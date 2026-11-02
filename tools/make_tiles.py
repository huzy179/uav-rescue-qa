"""Cắt một tập ảnh có nhãn YOLO thành ô (mặc định 640, chồng 0,2) ở độ phân giải gốc, giữ nhãn (TECHNICAL mục 13.2).

Dùng cho hai việc:
- dữ liệu hiệu chỉnh INT8 khi xuất TensorRT (RQ2): mô hình triển khai chạy trên ô 640 cắt từ ảnh gốc, nên hiệu chỉnh
  trên ô cùng kiểu thay vì ảnh thu nhỏ cả khung (người nhỏ hơn nhiều, phân bố kích hoạt khác);
- huấn luyện trên ô cắt (13.2), nếu cần.

Ô lấy theo cùng lưới với edge/detector.py (`tile_origins`). Một người được giữ trong ô khi phần nằm trong ô chiếm ít
nhất --min-visible diện tích box; box bị cắt theo mép ô. `--max-per-image` lấy ngẫu nhiên (có seed) tối đa từng ấy ô
mỗi ảnh, ưu tiên ô có người, để tập hiệu chỉnh không bị ô nước trống chiếm hết.

Ví dụ:
    .venv/bin/python tools/make_tiles.py --images data/processed/visdrone/images/val \\
        --labels data/processed/visdrone/labels/val --dst data/processed/calib_tiles --split val --max-per-image 2
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np

from edge.detector import tile_origins
from eval.splits import image_paths
from shared.config import parse_args_with_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images", type=Path, nargs="+", required=True, help="Một hay nhiều thư mục ảnh")
    parser.add_argument("--labels", type=Path, nargs="+", required=True, help="Thư mục nhãn YOLO, cùng thứ tự với --images")
    parser.add_argument("--dst", type=Path, required=True, help="Thư mục đích (ghi images/<split>, labels/<split>)")
    parser.add_argument("--split", default="val", help="Tên phần dữ liệu trong thư mục đích")
    parser.add_argument("--tile", type=int, default=640, help="Cạnh ô (px)")
    parser.add_argument("--overlap", type=float, default=0.2, help="Tỉ lệ chồng giữa các ô")
    parser.add_argument("--min-visible", type=float, default=0.5, help="Giữ người khi phần trong ô chiếm ít nhất tỉ lệ diện tích này")
    parser.add_argument("--max-per-image", type=int, default=None, help="Tối đa số ô mỗi ảnh (ưu tiên ô có người); không đặt thì lấy hết")
    parser.add_argument("--seed", type=int, default=0, help="Seed chọn ô")
    parser.add_argument("--jpeg-quality", type=int, default=95, help="Chất lượng JPEG khi ghi ô")
    return parse_args_with_config(parser)


def read_yolo_boxes(path: Path, width: int, height: int) -> np.ndarray:
    """Nhãn YOLO (cx, cy, w, h chuẩn hoá) thành box xyxy pixel, cột 0 là lớp; file không có thì mảng rỗng."""
    if not path.exists():
        return np.zeros((0, 5))
    rows = [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        return np.zeros((0, 5))
    a = np.array(rows, dtype=float)
    cx, cy, w, h = a[:, 1] * width, a[:, 2] * height, a[:, 3] * width, a[:, 4] * height
    return np.column_stack([a[:, 0], cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2])


def tile_labels(boxes: np.ndarray, x0: int, y0: int, tile_w: int, tile_h: int, min_visible: float) -> list[str]:
    """Dòng nhãn YOLO của một ô: box cắt theo mép ô, bỏ người có phần trong ô dưới min_visible diện tích."""
    lines = []
    for cls, x1, y1, x2, y2 in boxes:
        area = max((x2 - x1) * (y2 - y1), 1e-9)
        cx1, cy1 = max(x1, x0), max(y1, y0)
        cx2, cy2 = min(x2, x0 + tile_w), min(y2, y0 + tile_h)
        if cx2 <= cx1 or cy2 <= cy1 or (cx2 - cx1) * (cy2 - cy1) / area < min_visible:
            continue
        lines.append(
            f"{int(cls)} {((cx1 + cx2) / 2 - x0) / tile_w:.6f} {((cy1 + cy2) / 2 - y0) / tile_h:.6f} "
            f"{(cx2 - cx1) / tile_w:.6f} {(cy2 - cy1) / tile_h:.6f}\n"
        )
    return lines


def make_tiles(
    images: Path, labels: Path, dst: Path, split: str, tile: int, overlap: float, min_visible: float,
    max_per_image: int | None, rng: random.Random, quality: int,
) -> tuple[int, int]:
    """Ghi ô của một thư mục ảnh; trả (số ô, số người trong các ô đã ghi)."""
    image_dir, label_dir = dst / "images" / split, dst / "labels" / split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    n_tiles = n_persons = 0
    for path in image_paths(images):
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Không đọc được ảnh {path}")
        height, width = image.shape[:2]
        boxes = read_yolo_boxes(labels / f"{path.stem}.txt", width, height)
        candidates = []
        for y in tile_origins(height, tile, overlap):
            for x in tile_origins(width, tile, overlap):
                tw, th = min(tile, width - x), min(tile, height - y)
                candidates.append((x, y, tw, th, tile_labels(boxes, x, y, tw, th, min_visible)))
        if max_per_image is not None and len(candidates) > max_per_image:
            rng.shuffle(candidates)
            candidates.sort(key=lambda c: not c[4])  # sort ổn định: ô có người lên trước, giữ thứ tự ngẫu nhiên
            candidates = candidates[:max_per_image]
        for x, y, tw, th, lines in candidates:
            name = f"{path.stem}_x{x}_y{y}"
            cv2.imwrite(str(image_dir / f"{name}.jpg"), image[y : y + th, x : x + tw], [cv2.IMWRITE_JPEG_QUALITY, quality])
            (label_dir / f"{name}.txt").write_text("".join(lines), encoding="utf-8")
            n_tiles += 1
            n_persons += len(lines)
    return n_tiles, n_persons


def main() -> None:
    """Cắt từng thư mục ảnh, in số ô và số người."""
    args = parse_args()
    if len(args.images) != len(args.labels):
        raise SystemExit("--images và --labels phải cùng số thư mục")
    rng = random.Random(args.seed)
    for images, labels in zip(args.images, args.labels):
        n_tiles, n_persons = make_tiles(
            images, labels, args.dst, args.split, args.tile, args.overlap, args.min_visible,
            args.max_per_image, rng, args.jpeg_quality,
        )
        print(f"{images}: {n_tiles} ô, {n_persons} người -> {args.dst}")


if __name__ == "__main__":
    main()
