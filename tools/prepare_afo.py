"""Dựng lại bộ AFO (Aerial dataset of Floating Objects) theo bố cục chuẩn để tools/convert_yolo_subset.py đọc được.

Bản trên Kaggle (jangsienicajzkowy/afo-aerial-dataset-of-floating-objects) chia ảnh ra PART_1/2/3/images, còn mọi nhãn
nằm ở PART_1/6categories và chia tập bằng ba file danh sách train.txt, validation.txt, test.txt. Script này tạo
<out>/images/<tập> (liên kết cứng, không tốn dung lượng) và <out>/labels/<tập>, kèm file tên lớp <out>/classes.txt.
Tập test của AFO lấy từ 9 video không có trong train và validation.

Ví dụ:
    .venv/bin/python tools/prepare_afo.py --src data/raw/afo --out data/raw/afo_yolo
    .venv/bin/python tools/convert_yolo_subset.py --src data/raw/afo_yolo --dst data/processed/afo \\
        --names-file data/raw/afo_yolo/classes.txt --keep human --splits train val test
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from shared.config import parse_args_with_config

SPLIT_FILES = {"train": "train.txt", "val": "validation.txt", "test": "test.txt"}


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", type=Path, required=True, help="Thư mục chứa PART_1, PART_2, PART_3 (giải nén từ Kaggle)")
    parser.add_argument("--out", type=Path, required=True, help="Thư mục đích theo bố cục images/<tập>, labels/<tập>")
    parser.add_argument("--labels", default="6categories", help="Bộ nhãn trong PART_1: 6categories (có lớp human), 2categories, 1category")
    return parse_args_with_config(parser)


def find_part1(src: Path) -> Path:
    """Thư mục PART_1 chứa nhãn và file chia tập (Kaggle giải nén thành PART_1/PART_1)."""
    hits = sorted({p.parent for p in src.rglob("train.txt") if (p.parent / "validation.txt").is_file()})
    if len(hits) != 1:
        raise SystemExit(f"Cần đúng một thư mục có train.txt và validation.txt trong {src}, tìm thấy {len(hits)}")
    return hits[0]


def index_images(src: Path) -> dict[str, Path]:
    """Tên file → đường dẫn, gom từ mọi thư mục images; tên trùng giữa các phần là lỗi."""
    index: dict[str, Path] = {}
    for path in sorted(src.rglob("images/*.jpg")):
        if path.name in index:
            raise SystemExit(f"Ảnh trùng tên giữa các phần: {index[path.name]} và {path}")
        index[path.name] = path
    return index


def link(src: Path, dst: Path) -> None:
    """Liên kết cứng; khác ổ đĩa (Kaggle: /kaggle/input chỉ đọc) thì liên kết mềm, để không chép 4 GB ảnh."""
    if dst.exists() or dst.is_symlink():
        return
    try:
        os.link(src, dst)
    except OSError:
        dst.symlink_to(src.resolve())


def main() -> None:
    """Đọc danh sách từng tập, liên kết ảnh và nhãn sang bố cục chuẩn, báo ảnh thiếu hoặc không thuộc tập nào."""
    args = parse_args()
    part1 = find_part1(args.src)
    labels_dir = part1 / args.labels
    names_file = part1 / f"{args.labels}.names"
    if not labels_dir.is_dir():
        raise SystemExit(f"Không thấy thư mục nhãn {labels_dir}")
    images = index_images(args.src)

    listed: set[str] = set()
    for split, list_name in SPLIT_FILES.items():
        names = [Path(line.strip()).name for line in (part1 / list_name).read_text(encoding="utf-8").splitlines() if line.strip()]
        missing = [n for n in names if n not in images]
        if missing:
            raise SystemExit(f"{split}: {len(missing)} ảnh trong {list_name} không có trong các thư mục images, ví dụ {missing[:3]}")
        overlap = listed & set(names)
        if overlap:
            raise SystemExit(f"{split}: {len(overlap)} ảnh đã có ở tập khác, ví dụ {sorted(overlap)[:3]}")
        listed |= set(names)
        out_images, out_labels = args.out / "images" / split, args.out / "labels" / split
        out_images.mkdir(parents=True, exist_ok=True)
        out_labels.mkdir(parents=True, exist_ok=True)
        n_no_label = 0
        for name in names:
            link(images[name], out_images / name)
            label = labels_dir / f"{Path(name).stem}.txt"
            if label.is_file():
                link(label, out_labels / label.name)
            else:
                n_no_label += 1
                (out_labels / f"{Path(name).stem}.txt").write_text("", encoding="utf-8")
        print(f"{split}: {len(names)} ảnh, {n_no_label} ảnh không có file nhãn (coi là không có vật thể)")

    if names_file.is_file():
        shutil.copyfile(names_file, args.out / "classes.txt")
    unlisted = sorted(set(images) - listed)
    print(f"Ảnh không thuộc tập nào (bỏ qua): {len(unlisted)}{', ví dụ ' + str(unlisted[:3]) if unlisted else ''}")
    print(f"Kết quả tại: {args.out}")


if __name__ == "__main__":
    main()
