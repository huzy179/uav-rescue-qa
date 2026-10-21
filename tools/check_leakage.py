"""Kiểm tra rò rỉ giữa tập huấn luyện và tập đánh giá: trùng video (theo tên) và ảnh gần trùng (dHash).

Chạy trước khi khoá tập test lũ và trước mỗi lần huấn luyện có thêm dữ liệu. Thoát với mã 1 nếu có rò rỉ.

Ví dụ:
    .venv/bin/python tools/check_leakage.py --train data/processed/visdrone/images/train \\
        --eval data/processed/flood/images/test --output runs/leakage/flood_test
    # chỉ một tập: tìm ảnh gần trùng bên trong (khung liền nhau làm khoảng tin cậy hẹp giả)
    .venv/bin/python tools/check_leakage.py --eval data/processed/visdrone/images/val --output runs/leakage/visdrone_val
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2

from eval.splits import DEFAULT_GROUP_PATTERN, dhash, group_of, image_paths, near_duplicates
from shared.config import parse_args_with_config
from shared.provenance import write_run_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--train", type=Path, nargs="*", default=[], help="Các thư mục ảnh huấn luyện")
    parser.add_argument("--eval", type=Path, required=True, help="Thư mục ảnh đánh giá (val hoặc test)")
    parser.add_argument("--group-pattern", default=DEFAULT_GROUP_PATTERN, help="Regex lấy mã video từ tên file không đuôi")
    parser.add_argument("--max-distance", type=int, default=5, help="Số bit dHash khác nhau tối đa để coi là gần trùng (trên 64)")
    parser.add_argument("--output", type=Path, required=True, help="Thư mục ghi near_duplicates.csv và shared_groups.csv")
    return parse_args_with_config(parser)


def hash_folder(folder: Path) -> dict[str, int]:
    """dHash của mọi ảnh trong thư mục, khoá là đường dẫn tương đối dạng <thư mục>/<tên>."""
    hashes = {}
    for path in image_paths(folder):
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            print(f"[cảnh báo] Không đọc được ảnh, bỏ qua: {path}")
            continue
        hashes[f"{folder.name}/{path.name}"] = dhash(image)
    return hashes


def main() -> None:
    """Đối chiếu nhóm và hash, ghi CSV, in tóm tắt."""
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    eval_hashes = hash_folder(args.eval)
    train_hashes: dict[str, int] = {}
    for folder in args.train:
        train_hashes.update(hash_folder(folder))

    eval_groups = {group_of(Path(n).stem, args.group_pattern) for n in eval_hashes}
    train_groups = {group_of(Path(n).stem, args.group_pattern) for n in train_hashes}
    shared = sorted(eval_groups & train_groups)
    pairs = near_duplicates(eval_hashes, train_hashes if args.train else None, args.max_distance)

    with (args.output / "shared_groups.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["group"], *[[g] for g in shared]])
    with (args.output / "near_duplicates.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["eval_image", "other_image", "hamming"], *pairs])
    write_run_config(args.output, Path(__file__).name, None, None, vars(args))

    scope = "giữa tập đánh giá và tập huấn luyện" if args.train else "bên trong tập đánh giá"
    print(f"Tập đánh giá: {len(eval_hashes)} ảnh, {len(eval_groups)} video; tập huấn luyện: {len(train_hashes)} ảnh.")
    print(f"Video có mặt ở cả hai phía: {len(shared)}")
    n_eval_involved = len({a for a, _, _ in pairs} | ({b for _, b, _ in pairs} if not args.train else set()))
    print(f"Cặp gần trùng {scope} (≤ {args.max_distance} bit): {len(pairs)}, liên quan {n_eval_involved} ảnh đánh giá")
    print(f"Chi tiết: {args.output}")
    if args.train and (shared or pairs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
