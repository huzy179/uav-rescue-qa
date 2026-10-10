"""Đo tốc độ suy luận của một mô hình (.pt, .onnx, .engine) ở nhiều imgsz, dùng được trên Jetson."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


from edge.device import pick_device
from eval.report import PERSON_CLASS_ID, write_run_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="yolo26s.pt", help="Trọng số .pt hoặc mô hình đã xuất (.onnx, .engine)")
    parser.add_argument("--imgsz", type=int, nargs="+", default=[640, 1280], help="Danh sách kích thước suy luận")
    parser.add_argument("--image", type=Path, default=None, help="Ảnh dùng để đo (mặc định: ảnh nhiễu ngẫu nhiên)")
    parser.add_argument("--frame-size", type=int, nargs=2, default=[3840, 2160], metavar=("W", "H"), help="Kích thước ảnh ngẫu nhiên")
    parser.add_argument("--runs", type=int, default=50, help="Số lần đo cho mỗi imgsz")
    parser.add_argument("--warmup", type=int, default=10, help="Số lần chạy làm nóng, không tính vào kết quả")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng độ tin cậy")
    parser.add_argument("--half", action="store_true", help="Suy luận FP16 (chỉ với GPU CUDA)")
    parser.add_argument("--device", default=None, help="Ví dụ: cuda:0, mps, cpu (mặc định: tự chọn)")
    parser.add_argument("--output", type=Path, default=Path("runs/benchmark"), help="Thư mục kết quả")
    return parser.parse_args()


def main() -> None:
    """Đo thời gian mỗi lần gọi predict (gồm tiền và hậu xử lý) rồi in bảng và lưu CSV."""
    args = parse_args()
    from ultralytics import YOLO

    device = pick_device(args.device)
    args.output.mkdir(parents=True, exist_ok=True)
    if args.image is not None:
        frame = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
        if frame is None:
            raise FileNotFoundError(f"Không đọc được ảnh: {args.image}")
    else:
        width, height = args.frame_size
        frame = np.random.default_rng(0).integers(0, 256, (height, width, 3), dtype=np.uint8)

    model = YOLO(args.model, task="detect")
    write_run_config(args.output, Path(__file__).name, args.model, device, vars(args))
    rows = []
    for imgsz in args.imgsz:
        kwargs = dict(imgsz=imgsz, conf=args.conf, classes=[PERSON_CLASS_ID], device=device, half=args.half, verbose=False)
        for _ in range(args.warmup):
            model.predict(frame, **kwargs)
        times_ms = []
        for _ in range(args.runs):
            start = time.perf_counter()
            model.predict(frame, **kwargs)
            times_ms.append((time.perf_counter() - start) * 1000.0)
        times = np.asarray(times_ms)
        rows.append(
            {
                "model": Path(args.model).name,
                "device": device,
                "imgsz": imgsz,
                "frame": f"{frame.shape[1]}x{frame.shape[0]}",
                "mean_ms": round(float(times.mean()), 2),
                "median_ms": round(float(np.median(times)), 2),
                "p95_ms": round(float(np.percentile(times, 95)), 2),
                "fps": round(1000.0 / float(times.mean()), 1),
            }
        )

    table = pd.DataFrame(rows)
    table.to_csv(args.output / "benchmark.csv", index=False)
    print(table.to_string(index=False))
    print(f"\nKết quả lưu tại: {args.output}")


if __name__ == "__main__":
    main()
