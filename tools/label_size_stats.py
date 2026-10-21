"""Phân bố kích thước người khi vào mô hình lúc huấn luyện, dưới augmentation `scale` của ultralytics (TECHNICAL mục 13).

Ultralytics đưa cạnh dài ảnh về imgsz, rồi nhân thêm hệ số ngẫu nhiên s trong [1 − scale, 1 + scale]. Box có cạnh
dưới 2 px sau biến đổi bị XOÁ NHÃN (box_candidates, wh_thr=2) nhưng người vẫn còn trong ảnh: mô hình học rằng chỗ
đó là nền. Script cho biết bao nhiêu người rơi vào vùng đó ở từng hệ số s, để chọn `scale` cho E2.

Ví dụ:
    .venv/bin/python tools/label_size_stats.py --images data/processed/visdrone/images/val \\
        --labels data/processed/visdrone/labels/val --imgsz 1280 --output runs/stats/visdrone_val_1280
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from eval.metrics import load_yolo_labels
from eval.splits import image_paths
from shared.config import parse_args_with_config
from shared.provenance import write_run_config

# Cận dưới các nhóm theo cạnh ngắn (px) khi vào mô hình; <2 là ngưỡng ultralytics xoá nhãn.
EDGES = [0.0, 2.0, 4.0, 8.0, 16.0, 32.0, float("inf")]
LABELS = ["<2 (mất nhãn)", "2-4", "4-8", "8-16", "16-32", ">32"]


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images", type=Path, required=True, help="Thư mục ảnh")
    parser.add_argument("--labels", type=Path, required=True, help="Thư mục nhãn YOLO")
    parser.add_argument("--classes", type=int, nargs="+", default=[0], help="Mã lớp người")
    parser.add_argument("--imgsz", type=int, default=1280, help="imgsz lúc huấn luyện")
    parser.add_argument("--scales", type=float, nargs="+", default=[0.5, 0.75, 1.0, 1.25, 1.5], help="Các hệ số s cần xem")
    parser.add_argument("--output", type=Path, required=True, help="Thư mục ghi size_stats.csv")
    return parse_args_with_config(parser)


def short_sides_at_imgsz(images: Path, labels: Path, classes: list[int], imgsz: int) -> np.ndarray:
    """Cạnh ngắn (px) của mọi box sau khi ảnh được đưa cạnh dài về imgsz, như load_image của ultralytics."""
    sides = []
    for path in image_paths(images):
        with Image.open(path) as image:
            width, height = image.size
        boxes = load_yolo_labels(labels / f"{path.stem}.txt", width, height, classes)
        if len(boxes):
            r = imgsz / max(width, height)
            sides.append(np.minimum(boxes[:, 2] - boxes[:, 0], boxes[:, 3] - boxes[:, 1]) * r)
    return np.concatenate(sides) if sides else np.zeros(0)


def size_table(sides: np.ndarray, scales: list[float]) -> pd.DataFrame:
    """Tỉ lệ box mỗi nhóm kích thước ở từng hệ số s."""
    rows = []
    for s in scales:
        counts, _ = np.histogram(sides * s, bins=EDGES)
        rows.append({"scale_factor": s, "n_boxes": len(sides), **{k: round(c / max(len(sides), 1), 4) for k, c in zip(LABELS, counts)}})
    return pd.DataFrame(rows)


def main() -> None:
    """Tính và in bảng."""
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    table = size_table(short_sides_at_imgsz(args.images, args.labels, args.classes, args.imgsz), args.scales)
    table.to_csv(args.output / "size_stats.csv", index=False)
    write_run_config(args.output, Path(__file__).name, None, None, vars(args))
    print(f"imgsz {args.imgsz}; tỉ lệ box theo cạnh ngắn khi vào mô hình, ở từng hệ số scale s:")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
