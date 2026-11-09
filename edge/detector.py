"""Phát hiện người bằng YOLO trên toàn ảnh hoặc cắt ô theo lô (TECHNICAL mục 4.5, 7.4).

Ultralytics chỉ được import trong file này.
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal, Protocol

import cv2
import numpy as np

from edge.device import pick_device
from edge.tile_cache import TileCache
from shared.schema import Detection

PERSON_CLASS_ID = 0  # COCO và mô hình fine-tune một lớp đều để người ở lớp 0


class Detector(Protocol):
    def detect(
        self, frame: np.ndarray, frame_id: int, t: float, scale: float = 1.0
    ) -> tuple[list[Detection], dict[str, float]]: ...


def person_scale(
    expected_px: float, target_px: float | None, min_px: float | None = None, max_upscale: float = 2.0
) -> float:
    """Hệ số đổi cỡ khung trước khi phát hiện: > 1 là thu nhỏ, < 1 là phóng to, 1 là giữ nguyên.

    Thu nhỏ (target_px): người dự kiến to hơn target_px thì thu nhỏ để còn khoảng target_px. Lý do
    (docs/results/e6_sds_pilot.md): E2c bắt tốt nhất người khoảng 10–30 px và tụt mạnh với người trên 45 px.

    Phóng to (min_px): người dự kiến nhỏ hơn min_px thì phóng to để lên khoảng min_px, tối đa max_upscale lần.
    Phóng to không thêm chi tiết của cảm biến, nhưng mạng có bước lưới nhỏ nhất 8 px nên người 4–6 px chiếm
    quá ít ô lưới; dưới khoảng 6 px recall của E2c gần bằng 0 (e6_sds_pilot.md). Đổi lại số ô tăng theo bình phương
    hệ số. Không bật (min_px=None) thì giữ hành vi cũ.
    """
    if min_px is not None and target_px is not None and min_px > target_px:
        raise ValueError(f"min_px ({min_px}) phải không lớn hơn target_px ({target_px})")
    if max_upscale < 1.0:
        raise ValueError(f"max_upscale phải ≥ 1, nhận được: {max_upscale}")
    if min_px is not None and 0 < expected_px < min_px:
        return max(expected_px / min_px, 1.0 / max_upscale)
    if target_px is None or expected_px <= target_px:
        return 1.0
    return expected_px / target_px


def torch_device(device: str) -> str:
    """Tên thiết bị kiểu Ultralytics ("0", "cuda:0", "cpu", "mps") sang tên torch hiểu ("0" thành "cuda:0")."""
    return f"cuda:{device}" if device.isdigit() else device


def resize_torch(frame: np.ndarray, size: tuple[int, int], device: str = "cpu") -> np.ndarray:
    """Đổi cỡ khung bằng torch trên `device`, thay cho cv2.resize trên CPU (CAI_TIEN mục 2, docs/results/gpu_resize.md).

    size là (rộng, cao) như cv2. Thu nhỏ dùng nội suy song tuyến có khử răng cưa (antialias), gần INTER_AREA của
    cv2; phóng to dùng song tuyến thường như INTER_LINEAR. Khung uint8 (cao, rộng, kênh) được chép lên thiết bị ở dạng
    uint8 rồi mới đổi sang số thực, để lượng dữ liệu chép qua PCIe nhỏ nhất. Trả về uint8 trên CPU.
    """
    import torch
    import torch.nn.functional as F

    width, height = size
    downscale = width < frame.shape[1] or height < frame.shape[0]
    x = torch.from_numpy(np.ascontiguousarray(frame)).to(device).permute(2, 0, 1)[None].float()
    y = F.interpolate(x, size=(height, width), mode="bilinear", align_corners=False, antialias=downscale)
    return y[0].permute(1, 2, 0).round_().clamp_(0, 255).to(torch.uint8).cpu().numpy()


class ReplayDetector:
    """Đọc lại detections.jsonl của một lần chạy trước, để thí nghiệm RQ3 không phải chạy lại mô hình."""

    def __init__(self, path: Path) -> None:
        self._by_frame: dict[int, list[Detection]] = defaultdict(list)
        with path.open(encoding="utf-8") as f:
            for line in f:
                det = Detection.model_validate_json(line)
                # Bỏ toạ độ cũ: georef tính lại theo telemetry của lần chạy này.
                self._by_frame[det.frame_id].append(det.model_copy(update={"lat": None, "lon": None}))

    def detect(
        self, frame: np.ndarray, frame_id: int, t: float, scale: float = 1.0
    ) -> tuple[list[Detection], dict[str, float]]:
        return list(self._by_frame.get(frame_id, [])), {}


class Tracker(Protocol):
    def update(self, boxes: np.ndarray, confs: np.ndarray, warp: np.ndarray | None = None) -> list[tuple[int, int]]: ...


class ByteTracker:
    """Bọc BYTETracker của ultralytics làm thư viện độc lập, vì vòng model.track() không đi được với bộ cắt ô riêng.

    Đặt ở đây để ultralytics chỉ được import trong detector.py (quyết định #8 của ROADMAP); confirm.py dùng qua
    giao diện Tracker nên kiểm thử được bằng tracker giả. Tham số mặc định như bytetrack.yaml của ultralytics.
    """

    def __init__(
        self,
        track_high_thresh: float = 0.25,
        track_low_thresh: float = 0.1,
        new_track_thresh: float = 0.25,
        track_buffer: int = 30,
        match_thresh: float = 0.8,
        fuse_score: bool = True,
    ) -> None:
        from types import SimpleNamespace

        from ultralytics.trackers.byte_tracker import BYTETracker

        self._tracker = BYTETracker(
            SimpleNamespace(
                track_high_thresh=track_high_thresh, track_low_thresh=track_low_thresh,
                new_track_thresh=new_track_thresh, track_buffer=track_buffer,
                match_thresh=match_thresh, fuse_score=fuse_score,
            )
        )

    def update(self, boxes: np.ndarray, confs: np.ndarray, warp: np.ndarray | None = None) -> list[tuple[int, int]]:
        """Cập nhật với phát hiện của một khung; trả về (chỉ số phát hiện, track_id) cho các track được ghép ở khung này.

        warp (affine 2×3, khung trước → khung này) dời mọi track trước khi ghép: bù chuyển động camera.
        """
        if warp is not None:
            _warp_tracks(self._tracker.tracked_stracks + self._tracker.lost_stracks, warp)
        boxes = np.asarray(boxes, dtype=np.float32).reshape(-1, 4)
        xywh = np.column_stack([(boxes[:, :2] + boxes[:, 2:]) / 2, boxes[:, 2:] - boxes[:, :2]])
        self._tracker.update(_TrackInput(xywh, np.asarray(confs, dtype=np.float32), np.zeros(len(boxes), np.float32)))
        # Lấy mọi track được thấy ở khung này, kể cả track mới chưa "kích hoạt": đầu ra mặc định của BYTETracker bỏ
        # lần thấy đầu tiên, làm bytetrack cần N + 1 khung trong khi geo cần N. Lọc nhiễu để cho bước N lần thấy chung.
        frame = self._tracker.frame_id
        return [(int(t.idx), int(t.track_id)) for t in self._tracker.tracked_stracks if t.end_frame == frame]


class _TrackInput:
    """Đối tượng tối thiểu BYTETracker cần: xywh, conf, cls và lọc bằng mặt nạ boolean."""

    def __init__(self, xywh: np.ndarray, conf: np.ndarray, cls: np.ndarray) -> None:
        self.xywh, self.conf, self.cls = xywh, conf, cls

    def __len__(self) -> int:
        return len(self.conf)

    def __getitem__(self, mask: np.ndarray) -> _TrackInput:
        return _TrackInput(self.xywh[mask], self.conf[mask], self.cls[mask])


def _warp_tracks(stracks: list[Any], warp: np.ndarray) -> None:
    """Áp affine lên trạng thái Kalman dạng (x, y, a, h, vx, vy, va, vh): dời và xoay vị trí, xoay vận tốc.

    Không dùng multi_gmc chung của ultralytics: nó xoay cả cặp (a, h), sai với trạng thái XYAH (tỉ lệ khung không
    phải toạ độ). Co giãn do đổi độ cao giữa hai khung chỉ vài phần trăm nên bỏ qua với (a, h).
    """
    rotation, shift = warp[:, :2], warp[:, 2]
    transform = np.eye(8)
    transform[:2, :2] = rotation
    transform[4:6, 4:6] = rotation
    for track in stracks:
        mean = transform @ track.mean
        mean[:2] += shift
        track.mean = mean
        track.covariance = transform @ track.covariance @ transform.T


def tile_origins(length: int, tile: int, overlap: float) -> list[int]:
    """Toạ độ bắt đầu các ô dọc một chiều; ô cuối kéo sát mép ảnh để không thừa ra ngoài."""
    if length <= tile:
        return [0]
    step = int(tile * (1.0 - overlap))
    n = math.ceil((length - tile) / step) + 1
    return [min(i * step, length - tile) for i in range(n)]


def merge_boxes(boxes: np.ndarray, confs: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """NMS tham lam theo IOS (giao chia box nhỏ hơn) giữa các ô; trả về chỉ số box giữ lại.

    IOS thay cho IoU để box nửa người ở mép ô bị box đầy đủ của ô bên cạnh nuốt (TECHNICAL mục 4.3).
    Không hợp nhất toạ độ kiểu NMM: ở conf thấp, box lớn điểm thấp phủ cả nhóm người kéo box của từng người
    thành box cả nhóm (đã thử trên VisDrone val, AP50 tụt từ 0,452 xuống 0,045).
    """
    order = np.argsort(-confs, kind="stable")
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    keep: list[int] = []
    while order.size:
        i, rest = order[0], order[1:]
        keep.append(int(i))
        w = np.clip(np.minimum(boxes[i, 2], boxes[rest, 2]) - np.maximum(boxes[i, 0], boxes[rest, 0]), 0, None)
        h = np.clip(np.minimum(boxes[i, 3], boxes[rest, 3]) - np.maximum(boxes[i, 1], boxes[rest, 1]), 0, None)
        ios = w * h / np.maximum(np.minimum(areas[i], areas[rest]), 1e-9)
        order = rest[ios <= threshold]
    return np.array(keep, dtype=int)


def export_model(
    weights: str,
    output: Path,
    fmt: Literal["engine", "onnx"] = "engine",
    quantize: int = 16,
    imgsz: int = 640,
    batch: int = 1,
    dynamic: bool = False,
    data: Path | None = None,
    fraction: float = 1.0,
    workspace: float | None = None,
    max_det: int = 1000,
    device: str = "0",
) -> Path:
    """Xuất trọng số .pt sang TensorRT hoặc ONNX (RQ2, TECHNICAL mục 14.1), ghi đúng vào `output`.

    quantize: 32 (FP32), 16 (FP16) hoặc 8 (INT8, cần `data`: data.yaml có phần val dùng hiệu chỉnh). Engine cắt ô
    xuất với dynamic=True và batch bằng số ô tối đa mỗi khung, vì số ô đổi theo kích thước khung (thu nhỏ theo độ cao).
    Xuất với nms mặc định của ultralytics (None): đầu một-nhiều, NMS chạy ngoài engine như lần chạy .pt; max_det 1000
    như quy ước đo. Đầu một-một không NMS (nms=False) chưa dùng (TECHNICAL mục 3.1, 14.1).
    Ultralytics ghi file cạnh trọng số với cùng tên gốc, nên trọng số được chép thành `output` đuôi .pt trước khi
    xuất: file ra nằm trong thư mục của `output` (trọng số gốc có thể ở chỗ chỉ đọc, như /kaggle/input), FP16 và INT8
    không đè nhau.
    """
    import shutil

    from ultralytics import YOLO

    if quantize == 8 and data is None:
        raise ValueError("Xuất INT8 cần data.yaml cho ảnh hiệu chỉnh (data)")
    output.parent.mkdir(parents=True, exist_ok=True)
    source = output.with_suffix(".pt")
    if Path(weights).exists():
        shutil.copyfile(weights, source)
    else:  # tên mô hình chuẩn (yolo26s.pt): ultralytics tự tải
        source = Path(weights)
    kwargs: dict[str, Any] = dict(
        format=fmt, imgsz=imgsz, batch=batch, dynamic=dynamic, device=device, fraction=fraction, max_det=max_det,
        quantize=None if quantize == 32 else quantize,
    )
    if data is not None:
        kwargs["data"] = str(data)
    if workspace is not None:
        kwargs["workspace"] = workspace
    exported = Path(YOLO(str(source)).export(**kwargs))
    if exported.resolve() != output.resolve():
        exported.replace(output)
    return output


class YoloDetector:
    """Chạy được .pt, .onnx, .engine; với .engine, imgsz/tile và batch phải khớp lúc xuất.

    full_pass (chỉ với mode="tiled"): thêm một lượt toàn ảnh ở imgsz để bắt người lớn bị cắt đôi giữa các ô,
    giống perform_standard_pred mặc định của SAHI.
    nms_free: dùng đầu một-một của YOLO26 (ultralytics nms=False), không chạy NMS; mặc định False là đầu một-nhiều
    kèm NMS như mọi kết quả trước 8/11 (TECHNICAL mục 3.1, docs/results/nms_free.md).
    gpu_resize: đổi cỡ khung (scale ≠ 1) bằng torch trên thiết bị của mô hình (resize_torch) thay cho cv2.resize trên
    CPU; mặc định False giữ cv2 như mọi kết quả trước 10/11 (docs/results/gpu_resize.md).
    """

    def __init__(
        self,
        model_path: str,
        mode: Literal["full", "tiled"] = "tiled",
        imgsz: int = 1280,
        tile: int = 640,
        overlap: float = 0.2,
        conf: float = 0.1,
        max_det: int = 1000,
        device: str | None = None,
        full_pass: bool = False,
        nms_free: bool = False,
        tile_cache: TileCache | None = None,
        gpu_resize: bool = False,
    ) -> None:
        from ultralytics import YOLO

        if mode not in ("full", "tiled"):
            raise ValueError(f"mode phải là 'full' hoặc 'tiled', nhận được: {mode}")
        self.model = YOLO(model_path)
        self.mode, self.imgsz, self.tile, self.overlap, self.full_pass = mode, imgsz, tile, overlap, full_pass
        self.device = pick_device(device)
        self._kwargs: dict[str, Any] = dict(
            conf=conf, classes=[PERSON_CLASS_ID], max_det=max_det, device=self.device, verbose=False
        )
        if nms_free:
            self._kwargs["nms"] = False
        # Dùng lại kết quả ô không đổi (edge/tile_cache.py); bên gọi bật allow_tile_reuse khi drone đứng yên.
        self.tile_cache = tile_cache
        self.resize_device = torch_device(self.device) if gpu_resize else None
        self.allow_tile_reuse = False
        self._warmed_up = False

    def _predict(self, images: list[np.ndarray], imgsz: int) -> list[tuple[np.ndarray, np.ndarray]]:
        results: Any = self.model.predict(images, imgsz=imgsz, **self._kwargs)
        return [(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()) for r in results]

    def detect(
        self, frame: np.ndarray, frame_id: int, t: float, scale: float = 1.0
    ) -> tuple[list[Detection], dict[str, float]]:
        """Trả về phát hiện trên toạ độ ảnh gốc và thời gian từng phần (ms): cắt ô, suy luận, gộp.

        scale ≠ 1: đổi cỡ khung theo hệ số này trước khi cắt ô hay suy luận (> 1 thu nhỏ, < 1 phóng to;
        xem person_scale), box quy về ảnh gốc.
        """
        start = time.perf_counter()
        if scale != 1.0:
            size = (max(1, round(frame.shape[1] / scale)), max(1, round(frame.shape[0] / scale)))
            if self.resize_device is not None:
                frame = resize_torch(frame, size, self.resize_device)
            else:
                interpolation = cv2.INTER_AREA if scale > 1.0 else cv2.INTER_LINEAR
                frame = cv2.resize(frame, size, interpolation=interpolation)
        if self.mode == "full":
            images, offsets, imgsz = [frame], [(0, 0)], self.imgsz
        else:
            height, width = frame.shape[:2]
            offsets = [
                (x, y)
                for y in tile_origins(height, self.tile, self.overlap)
                for x in tile_origins(width, self.tile, self.overlap)
            ]
            # Slicing numpy không sao chép dữ liệu ảnh.
            images, imgsz = [frame[y : y + self.tile, x : x + self.tile] for x, y in offsets], self.tile
        tile_ms = (time.perf_counter() - start) * 1000.0
        full_pass = self.mode == "tiled" and self.full_pass
        if not self._warmed_up:
            # Lần gọi đầu chậm bất thường, không tính vào thời gian đo.
            self._predict(images, imgsz)
            if full_pass:
                self._predict([frame], self.imgsz)
            self._warmed_up = True
        t_tile = time.perf_counter()
        n_run = len(images)
        if self.tile_cache is not None and self.mode == "tiled":
            keys = [(frame.shape[1], frame.shape[0], x, y) for x, y in offsets]
            run = self.tile_cache.begin(keys, images, self.allow_tile_reuse)
            to_run = [im for im, r in zip(images, run) if r]
            n_run = len(to_run)
            outputs = self.tile_cache.finish(self._predict(to_run, imgsz) if to_run else [])
        else:
            outputs = self._predict(images, imgsz)
        if full_pass:
            # Lượt toàn ảnh có imgsz khác ô nên gọi riêng; ultralytics đã quy box về ảnh gốc.
            outputs += self._predict([frame], self.imgsz)
            offsets = offsets + [(0, 0)]
        t_infer = time.perf_counter()

        boxes = np.concatenate([b + np.array([x, y, x, y], dtype=b.dtype) for (b, _), (x, y) in zip(outputs, offsets)])
        confs = np.concatenate([c for _, c in outputs])
        if len(offsets) > 1:
            keep = merge_boxes(boxes, confs)
            boxes, confs = boxes[keep], confs[keep]
        if scale != 1.0:
            boxes = boxes * scale
        detections = [
            Detection(frame_id=frame_id, t=t, box_px=(x1, y1, x2, y2), conf=conf)
            for (x1, y1, x2, y2), conf in zip(boxes.tolist(), confs.tolist())
        ]
        t_merge = time.perf_counter()
        timings = {
            "tile_ms": tile_ms,
            "infer_ms": (t_infer - t_tile) * 1000.0,
            "merge_ms": (t_merge - t_infer) * 1000.0,
            "n_tiles": float(len(offsets)),
            "n_tiles_run": float(n_run + (1 if full_pass else 0)),
            "scale": scale,
        }
        return detections, timings
