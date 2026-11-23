"""Video kiểm tra cho tập test lũ: chạy mô hình trên trọn một video đã trích khung gán nhãn (docs/DEMO_BAO_VE.md).

Mỗi khung vẽ box của mô hình (xanh dương, conf ≥ --conf). Khung nằm trong tập test đã khoá (tên
`<video>_<số khung>.jpg`, tools/extract_frames.py) thì dừng --hold-s giây và so với nhãn như tools/demo_panels.py:
vòng xanh lá là người có nhãn được thấy, đỏ là bỏ sót, vàng là báo nhầm, kèm dòng đếm. Dự đoán trên các khung đó lấy
từ --run (boxes.csv của lần chấm, ví dụ runs/flood/E2c) để khớp số đã báo cáo, không phải từ lần chạy lại trên video
(ảnh JPEG trích ra và khung giải mã từ video lệch nhau chút ít).

Chạy cho cả 10 video, không chọn video: chọn tay video để chiếu là chọn ảnh đẹp (CLAUDE.md). Video lũ có bản quyền:
chỉ chiếu trong buổi bảo vệ (quyết định #12). Không có telemetry nên không có bản đồ.

Ví dụ:
    .venv/bin/python tools/flood_video.py --video nidarx-flood-1 --output runs/demo/flood_video
    .venv/bin/python tools/flood_video.py --video all --output runs/demo/flood_video
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from console.errors import ImageErrors, match_errors
from eval.draw import put_text
from eval.metrics import load_yolo_labels
from shared.config import parse_args_with_config

GREEN, RED, YELLOW, BLUE = (80, 220, 40), (40, 40, 255), (0, 210, 255), (255, 160, 0)  # BGR
FRAME_NAME = re.compile(r"^(?P<video>.+)_(?P<index>\d{6})$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", required=True, help="Mã video (tên file trong --videos, không đuôi) hoặc 'all'")
    parser.add_argument("--videos", type=Path, default=Path("data/raw/flood/videos"), help="Thư mục video gốc")
    parser.add_argument("--flood", type=Path, default=Path("data/processed/flood"), help="Tập lũ đã chuyển nhãn")
    parser.add_argument("--split", default="test")
    parser.add_argument("--run", type=Path, default=Path("runs/flood/E2c"), help="Lần chấm trên tập lũ (boxes.csv)")
    parser.add_argument("--model", default="runs/train/E2c_s0/weights/best.pt", help="Mô hình chạy trên các khung còn lại")
    parser.add_argument("--title", default="Đã tinh chỉnh (E2c)", help="Tên mô hình in trên video")
    parser.add_argument("--imgsz", type=int, default=1280, help="Như configs/experiments/E2c_flood.yaml")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng conf vận hành")
    parser.add_argument("--iou", type=float, default=0.5, help="Ngưỡng IoU khi so với nhãn")
    parser.add_argument("--hold-s", type=float, default=2.0, help="Dừng ở khung đã gán nhãn bao nhiêu giây")
    parser.add_argument("--stride", type=int, default=1, help="Lấy một khung mỗi N khung (video ra nhanh hơn, chạy nhanh hơn)")
    parser.add_argument("--max-width", type=int, default=1280, help="Thu nhỏ video ra về cạnh ngang này")
    parser.add_argument("--device", default=None)
    parser.add_argument("--output", type=Path, required=True, help="Thư mục ghi <video>.mp4")
    return parser


def labeled_frames(images: Path, video: str) -> dict[int, Path]:
    """Số khung → file ảnh của các khung đã gán nhãn thuộc video này."""
    out = {}
    for path in sorted(images.glob(f"{video}_*.jpg")):
        m = FRAME_NAME.match(path.stem)
        if m and m["video"] == video:
            out[int(m["index"])] = path
    return out


def videos_in(images: Path) -> list[str]:
    """Mọi mã video có khung trong tập (không chọn tay)."""
    return sorted({m["video"] for p in images.glob("*.jpg") if (m := FRAME_NAME.match(p.stem))})


def ring(image: np.ndarray, box: np.ndarray, color: tuple[int, int, int], thick: int) -> None:
    cx, cy = int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)
    r = int(max(10, image.shape[1] // 100, 0.6 * max(box[2] - box[0], box[3] - box[1])))
    cv2.circle(image, (cx, cy), r, color, thick, cv2.LINE_AA)


def banner(image: np.ndarray, text: str, row: int = 0) -> None:
    size = max(18, image.shape[1] // 50)
    y = 6 + row * (size + 14)
    cv2.rectangle(image, (0, y - 6), (image.shape[1], y + size + 8), (0, 0, 0), -1)
    put_text(image, text, (10, y), size, (255, 255, 255))


def draw_boxes(image: np.ndarray, boxes: np.ndarray) -> None:
    thick = max(2, image.shape[1] // 640)
    for b in boxes.astype(int):
        cv2.rectangle(image, (b[0], b[1]), (b[2], b[3]), BLUE, thick)


def draw_labeled(image: np.ndarray, gts: np.ndarray, preds: np.ndarray, err: ImageErrors) -> str:
    """Vòng so với nhãn như demo_panels; trả dòng đếm."""
    for _, j in err.tp:
        ring(image, gts[j], GREEN, 3)
    for j in err.fn:
        ring(image, gts[j], RED, 4)
    for i in err.fp:
        ring(image, preds[i], YELLOW, 3)
    return f"KHUNG ĐÃ GÁN NHÃN: thấy {len(err.tp)}/{len(gts)}, bỏ sót {len(err.fn)}, báo nhầm {len(err.fp)}"


def load_run(run: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    df = pd.read_csv(run / "boxes.csv")
    return {n: (g[["x1", "y1", "x2", "y2"]].to_numpy(float), g["conf"].to_numpy(float)) for n, g in df.groupby("image")}


def render_video(video: str, args: argparse.Namespace, detector: object, run: dict[str, tuple[np.ndarray, np.ndarray]]) -> Path:
    images = args.flood / "images" / args.split
    labeled = labeled_frames(images, video)
    cap = cv2.VideoCapture(str(args.videos / f"{video}.mp4"))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    out_fps = fps / args.stride
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / f"{video}.mp4"
    writer: cv2.VideoWriter | None = None
    index, n_tp, n_gt = -1, 0, 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            index += 1
            is_labeled = index in labeled
            if index % args.stride and not is_labeled:
                continue
            if is_labeled:
                name = labeled[index].name
                h, w = frame.shape[:2]
                gts = load_yolo_labels(args.flood / "labels" / args.split / f"{labeled[index].stem}.txt", w, h, [0])
                ign_path = args.flood / "ignore" / args.split / f"{labeled[index].stem}.txt"
                ign = load_yolo_labels(ign_path, w, h, [0]) if ign_path.exists() else None
                boxes, confs = run.get(name, (np.zeros((0, 4)), np.zeros(0)))
                keep = confs >= args.conf
                boxes, confs = boxes[keep], confs[keep]
                err = match_errors(boxes, confs, gts, args.iou, ign)
                n_tp, n_gt = n_tp + len(err.tp), n_gt + len(gts)
                draw_boxes(frame, boxes)
                line = draw_labeled(frame, gts, boxes, err)
            else:
                dets, _ = detector.detect(frame, index, index / fps)  # type: ignore[attr-defined]
                boxes = np.array([d.box_px for d in dets], dtype=float).reshape(-1, 4)
                draw_boxes(frame, boxes)
                line = ""
            scale = min(1.0, args.max_width / frame.shape[1])
            if scale < 1.0:
                frame = cv2.resize(frame, (round(frame.shape[1] * scale), round(frame.shape[0] * scale)), interpolation=cv2.INTER_AREA)
            banner(frame, f"{args.title} · {video} · khung {index} · không có telemetry")
            if line:
                banner(frame, line, row=1)
            if writer is None:
                writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"mp4v"), out_fps, (frame.shape[1], frame.shape[0]))
            for _ in range(max(1, round(args.hold_s * out_fps)) if line else 1):
                writer.write(frame)
    finally:
        cap.release()
        if writer is not None:
            writer.release()
    print(f"{path}: {index + 1} khung, {len(labeled)} khung đã gán nhãn, thấy {n_tp}/{n_gt} người có nhãn")
    return path


def main() -> None:
    args = parse_args_with_config(build_parser())
    images = args.flood / "images" / args.split
    names = videos_in(images) if args.video == "all" else [args.video]
    from edge.detector import YoloDetector  # ultralytics chỉ nạp ở đây, khi thật sự chạy

    detector = YoloDetector(args.model, mode="full", imgsz=args.imgsz, conf=args.conf, device=args.device)
    run = load_run(args.run)
    for video in names:
        if not (args.videos / f"{video}.mp4").exists():
            print(f"[bỏ qua] không có {args.videos / video}.mp4")
            continue
        render_video(video, args, detector, run)


if __name__ == "__main__":
    main()
