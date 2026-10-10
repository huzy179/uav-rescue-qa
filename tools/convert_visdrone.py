"""Chuyển VisDrone2019-DET sang định dạng YOLO một lớp person, giữ riêng các vùng bỏ qua."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image

# Mã lớp gốc của VisDrone: 0 = vùng bỏ qua, 1 = pedestrian, 2 = people, 3–10 = phương tiện, 11 = khác.
IGNORED_REGION = 0
DEFAULT_PERSON_CLASSES = [1, 2]
SIZE_BIN_EDGES = [0, 8, 16, 32, float("inf")]
SIZE_BIN_LABELS = ["<8", "8-16", "16-32", ">32"]


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, required=True, help="Thư mục gốc, ví dụ data/raw/visdrone/VisDrone2019-DET-val")
    parser.add_argument("--dst", type=Path, default=Path("data/processed/visdrone"), help="Thư mục đích")
    parser.add_argument("--split", required=True, help="Tên tập: train, val hoặc test")
    parser.add_argument("--person-classes", type=int, nargs="+", default=DEFAULT_PERSON_CLASSES, help="Mã lớp gốc gộp thành person")
    return parser.parse_args()


def to_yolo(x: float, y: float, w: float, h: float, width: int, height: int) -> str:
    """Box pixel (trái, trên, rộng, cao) sang dòng YOLO lớp 0 đã chuẩn hoá."""
    return f"0 {(x + w / 2) / width:.6f} {(y + h / 2) / height:.6f} {w / width:.6f} {h / height:.6f}\n"


def link_or_copy(src: Path, dst: Path) -> None:
    """Tạo hard link để không tốn thêm dung lượng; nếu không được thì sao chép."""
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def size_bin(short_side: float) -> str:
    """Nhóm kích thước theo cạnh ngắn của box."""
    for label, lo, hi in zip(SIZE_BIN_LABELS, SIZE_BIN_EDGES, SIZE_BIN_EDGES[1:]):
        if lo <= short_side < hi:
            return label
    return SIZE_BIN_LABELS[-1]


def main() -> None:
    """Chuyển một tập của VisDrone, in và lưu thống kê kích thước box."""
    args = parse_args()
    out_images = args.dst / "images" / args.split
    out_labels = args.dst / "labels" / args.split
    out_ignore = args.dst / "ignore" / args.split
    for d in (out_images, out_labels, out_ignore):
        d.mkdir(parents=True, exist_ok=True)

    bins: Counter[str] = Counter()
    n_images = n_persons = n_ignore = 0
    for image_path in sorted((args.src / "images").glob("*.jpg")):
        with Image.open(image_path) as img:
            width, height = img.size
        persons, ignores = [], []
        for line in (args.src / "annotations" / f"{image_path.stem}.txt").read_text().splitlines():
            parts = line.strip().rstrip(",").split(",")
            if len(parts) < 6:
                continue
            x, y, w, h, score, category = (int(v) for v in parts[:6])
            if w <= 0 or h <= 0:
                continue
            if category == IGNORED_REGION or score == 0:
                # score = 0 nghĩa là box bị bỏ qua khi đánh giá; gom chung với vùng bỏ qua.
                ignores.append(to_yolo(x, y, w, h, width, height))
            elif category in args.person_classes:
                persons.append(to_yolo(x, y, w, h, width, height))
                bins[size_bin(min(w, h))] += 1
        link_or_copy(image_path, out_images / image_path.name)
        (out_labels / f"{image_path.stem}.txt").write_text("".join(persons))
        (out_ignore / f"{image_path.stem}.txt").write_text("".join(ignores))
        n_images += 1
        n_persons += len(persons)
        n_ignore += len(ignores)

    stats = {
        "split": args.split,
        "source": str(args.src),
        "person_classes": args.person_classes,
        "n_images": n_images,
        "n_persons": n_persons,
        "n_ignore_regions": n_ignore,
        "persons_by_short_side_px": {label: bins[label] for label in SIZE_BIN_LABELS},
    }
    (args.dst / f"stats_{args.split}.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
