"""Đo thời gian đổi cỡ một khung bằng cv2 (CPU, số luồng cho trước) và bằng torch (resize_torch) trên ảnh thật.

Dùng cho docs/results/gpu_resize.md: thời gian trên máy cá nhân chỉ để so sánh tương đối (CLAUDE.md). Giới hạn số
luồng của cv2 (--threads) để thấy chặng này nặng thế nào khi CPU yếu như Kaggle hay Jetson.
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import cv2
import numpy as np

from edge.detector import resize_torch, torch_device
from shared.config import parse_args_with_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, nargs="+", required=True, help="Ảnh khung gốc để đo")
    parser.add_argument("--scales", type=float, nargs="+", default=[1.5, 2.37, 3.0, 6.0], help="Hệ số thu nhỏ (> 1)")
    parser.add_argument("--threads", type=int, nargs="+", default=[1, 2, 4, 0], help="Số luồng của cv2; 0 là mặc định")
    parser.add_argument("--device", default="0", help="Thiết bị của torch (như Ultralytics: 0, cpu)")
    parser.add_argument("--repeat", type=int, default=20, help="Số lần đo mỗi ô")
    parser.add_argument("--output", type=Path, required=True, help="File CSV kết quả")
    return parser


def median_ms(fn, repeat: int, sync=None) -> float:
    fn()
    times = []
    for _ in range(repeat):
        if sync:
            sync()
        start = time.perf_counter()
        fn()
        if sync:
            sync()
        times.append((time.perf_counter() - start) * 1000.0)
    return float(np.median(times))


def main() -> None:
    args = parse_args_with_config(build_parser())
    import torch

    device = torch_device(args.device)
    sync = torch.cuda.synchronize if device.startswith("cuda") else None
    default_threads = cv2.getNumThreads()
    rows = []
    for path in args.images:
        frame = cv2.imread(str(path))
        if frame is None:
            raise SystemExit(f"Không đọc được ảnh: {path}")
        h, w = frame.shape[:2]
        for scale in args.scales:
            size = (max(1, round(w / scale)), max(1, round(h / scale)))
            for threads in args.threads:
                cv2.setNumThreads(threads if threads > 0 else default_threads)
                ms = median_ms(lambda: cv2.resize(frame, size, interpolation=cv2.INTER_AREA), args.repeat)
                rows.append({"image": path.name, "width": w, "height": h, "scale": scale, "method": "cv2_area", "threads": threads, "ms_median": round(ms, 3), "mean_abs_diff": 0.0})
            cv2.setNumThreads(default_threads)
            ref = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
            out = resize_torch(frame, size, device)
            diff = float(np.abs(out.astype(int) - ref.astype(int)).mean())
            ms = median_ms(lambda: resize_torch(frame, size, device), args.repeat, sync)
            rows.append({"image": path.name, "width": w, "height": h, "scale": scale, "method": f"torch_{device}", "threads": 0, "ms_median": round(ms, 3), "mean_abs_diff": round(diff, 3)})
            print(rows[-1])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Đã ghi {args.output}")


if __name__ == "__main__":
    main()
