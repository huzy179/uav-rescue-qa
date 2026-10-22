"""Demo trực tiếp: phát video trong một cửa sổ, phát hiện và theo dõi người ngay trên từng khung.

Mỗi người được tô một màu riêng (bán trong suốt) kèm số ID và vệt đường đi; góc trên có bảng đếm người. Dùng để
trình bày, không phải để đo: số đếm là số track khác nhau, một người bị mất dấu rồi xuất hiện lại sẽ được đếm hai lần.

Phím: Space tạm dừng / chạy tiếp, Q hoặc Esc thoát.

Ví dụ:
    .venv/bin/python scripts/live_demo.py --source "/mnt/c/Users/Huy/Downloads/test uav.mp4" \\
        --model runs/train/E2_s0/weights/best.pt
    # không mở cửa sổ, chỉ ghi video (kiểm tra trên máy không có màn hình):
    .venv/bin/python scripts/live_demo.py --source video.mp4 --no-window --save runs/edge/live.mp4
"""

from __future__ import annotations

import argparse
import time
from collections import defaultdict, deque
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from edge.detector import ByteTracker, YoloDetector
from shared.config import parse_args_with_config

WINDOW = "FloodEye - demo truc tiep"


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, required=True, help="File video")
    parser.add_argument("--model", default="yolo26s.pt", help="Trọng số .pt, .onnx hoặc .engine")
    parser.add_argument("--mode", choices=["full", "tiled"], default="full", help="Toàn ảnh (nhanh) hay cắt ô")
    parser.add_argument("--imgsz", type=int, default=1280, help="Kích thước suy luận khi mode=full")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng conf để hiển thị")
    parser.add_argument("--min-frames", type=int, default=3, help="Track thấy đủ số khung này mới được đếm")
    parser.add_argument("--trail", type=int, default=25, help="Số vị trí gần nhất vẽ thành vệt đường đi")
    parser.add_argument("--window-width", type=int, default=1280, help="Bề rộng cửa sổ (px)")
    parser.add_argument("--save", type=Path, default=None, help="Ghi video đã tô ra file .mp4")
    parser.add_argument("--no-window", action="store_true", help="Không mở cửa sổ (chỉ dùng với --save)")
    parser.add_argument("--device", default=None, help="cuda:0, mps, cpu (mặc định: tự chọn)")
    return parse_args_with_config(parser)


def track_color(track_id: int) -> tuple[int, int, int]:
    """Màu cố định cho mỗi track (BGR), độ bão hoà cao để nổi trên nền nước đục."""
    hue = (track_id * 47) % 180
    return tuple(int(c) for c in cv2.cvtColor(np.uint8([[[hue, 230, 255]]]), cv2.COLOR_HSV2BGR)[0, 0])


def load_font(size: int) -> ImageFont.ImageFont:
    """Font có dấu tiếng Việt: DejaVu đi kèm matplotlib; không có thì dùng font mặc định của Pillow."""
    try:
        import matplotlib

        return ImageFont.truetype(str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans-Bold.ttf"), size)
    except (ImportError, OSError):
        return ImageFont.load_default()


def draw_people(frame: np.ndarray, tracks: list[tuple[np.ndarray, int]], trails: dict[int, deque], confirmed: set[int]) -> np.ndarray:
    """Tô người: nền màu bán trong suốt, viền, vệt đường đi và số ID; người đã đếm có viền đậm."""
    overlay = frame.copy()
    for box, track_id in tracks:
        x1, y1, x2, y2 = (int(round(v)) for v in box)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), track_color(track_id), -1)
    canvas = cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)
    for track_id, points in trails.items():
        if len(points) > 1:
            cv2.polylines(canvas, [np.int32(list(points))], False, track_color(track_id), 2, cv2.LINE_AA)
    for box, track_id in tracks:
        x1, y1, x2, y2 = (int(round(v)) for v in box)
        color = track_color(track_id)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2 if track_id in confirmed else 1, cv2.LINE_AA)
        cv2.putText(canvas, str(track_id), (x1, max(12, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
    return canvas


def draw_panel(canvas: np.ndarray, lines: list[str], font: ImageFont.ImageFont) -> np.ndarray:
    """Bảng thông tin nền tối ở góc trên trái, chữ có dấu vẽ bằng Pillow."""
    image = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image, "RGBA")
    line_h = font.size + 8 if hasattr(font, "size") else 20
    width = max(draw.textlength(line, font=font) for line in lines) + 28
    draw.rounded_rectangle((10, 10, 10 + width, 18 + line_h * len(lines)), radius=10, fill=(0, 0, 0, 170))
    for i, line in enumerate(lines):
        draw.text((24, 16 + i * line_h), line, font=font, fill=(255, 230, 80) if i == 0 else (255, 255, 255))
    return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


def main() -> None:
    """Đọc từng khung, phát hiện, ghép track, tô và hiển thị theo đúng nhịp video (hoặc nhanh nhất có thể)."""
    args = parse_args()
    if args.no_window and args.save is None:
        raise SystemExit("--no-window cần --save, nếu không sẽ không thấy gì")
    cap = cv2.VideoCapture(str(args.source))
    if not cap.isOpened():
        raise SystemExit(f"Không mở được video: {args.source}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    detector = YoloDetector(args.model, mode=args.mode, imgsz=args.imgsz, conf=args.conf, device=args.device)
    tracker = ByteTracker()
    trails: dict[int, deque] = defaultdict(lambda: deque(maxlen=args.trail))
    seen_frames: dict[int, int] = defaultdict(int)
    font = load_font(max(14, height // 30))
    writer = cv2.VideoWriter(str(args.save), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)) if args.save else None
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
    if not args.no_window:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW, args.window_width, int(args.window_width * height / width))

    frame_id, paused, proc_fps = 0, False, 0.0
    try:
        while True:
            if not paused:
                ok, frame = cap.read()
                if not ok:
                    break
                tick = time.perf_counter()
                dets, _ = detector.detect(frame, frame_id, frame_id / fps)
                boxes = np.array([d.box_px for d in dets], dtype=float).reshape(-1, 4)
                confs = np.array([d.conf for d in dets], dtype=float)
                tracks = [(boxes[i], track_id) for i, track_id in tracker.update(boxes, confs)]
                visible = {track_id for _, track_id in tracks}
                for box, track_id in tracks:
                    seen_frames[track_id] += 1
                    trails[track_id].append(((box[0] + box[2]) / 2, box[3]))
                for track_id in list(trails):
                    if track_id not in visible:
                        del trails[track_id]
                confirmed = {k for k, n in seen_frames.items() if n >= args.min_frames}
                canvas = draw_people(frame, tracks, trails, confirmed)
                elapsed = time.perf_counter() - tick
                proc_fps = 0.9 * proc_fps + 0.1 * (1.0 / max(elapsed, 1e-6)) if frame_id else 1.0 / max(elapsed, 1e-6)
                canvas = draw_panel(canvas, [
                    "FloodEye · phát hiện người từ UAV",
                    f"Đang thấy: {len(visible & confirmed)} người",
                    f"Tổng số người khác nhau: {len(confirmed)}",
                    f"Mô hình: {Path(args.model).name} · {proc_fps:.0f} khung/giây",
                ], font)
                if writer is not None:
                    writer.write(canvas)
                frame_id += 1
                wait_ms = max(1, int(1000 / fps - elapsed * 1000))  # giữ nhịp video khi xử lý nhanh hơn thời gian thực
            else:
                wait_ms = 50
            if not args.no_window:
                cv2.imshow(WINDOW, canvas)
                key = cv2.waitKey(wait_ms) & 0xFF
                if key in (ord("q"), 27) or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                    break
                if key == ord(" "):
                    paused = not paused
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        if not args.no_window:
            cv2.destroyAllWindows()
    print(f"Đã xử lý {frame_id} khung; tổng số người khác nhau (track ≥ {args.min_frames} khung): {len(confirmed) if frame_id else 0}")
    if args.save:
        print(f"Video đã tô: {args.save}")


if __name__ == "__main__":
    main()
