"""Chia một thư mục ảnh thành các tập theo video (mọi khung của một video vào cùng một tập), ghi danh sách .txt.

File .txt dùng thẳng được làm --train/--val của training/train.py (ultralytics nhận danh sách đường dẫn ảnh).

Ví dụ:
    .venv/bin/python tools/split_by_video.py --images data/processed/finland/images/all \\
        --names train val --ratios 0.8 0.2 --output data/processed/finland/splits
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from eval.splits import DEFAULT_GROUP_PATTERN, assign_groups, group_of, image_paths
from shared.config import parse_args_with_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images", type=Path, required=True, help="Thư mục ảnh cần chia")
    parser.add_argument("--names", nargs="+", default=["train", "val"], help="Tên các tập")
    parser.add_argument("--ratios", type=float, nargs="+", default=[0.8, 0.2], help="Tỉ lệ số ảnh mỗi tập")
    parser.add_argument("--group-pattern", default=DEFAULT_GROUP_PATTERN, help="Regex trên tên file không đuôi; nhóm bắt đầu tiên là mã video")
    parser.add_argument("--seed", type=int, default=0, help="Seed xáo nhóm")
    parser.add_argument("--output", type=Path, required=True, help="Thư mục ghi <tên tập>.txt và groups.csv")
    return parse_args_with_config(parser)


def main() -> None:
    """Gom ảnh theo video, gán video vào tập, ghi danh sách và bảng nhóm."""
    args = parse_args()
    if len(args.names) != len(args.ratios):
        raise SystemExit("--names và --ratios phải cùng số phần tử")
    paths = image_paths(args.images)
    if not paths:
        raise SystemExit(f"Không có ảnh trong {args.images}")
    groups = {p: group_of(p.stem, args.group_pattern) for p in paths}
    sizes = Counter(groups.values())
    if len(sizes) == len(paths):
        print("[cảnh báo] Mỗi ảnh là một nhóm riêng: --group-pattern không khớp tên file, chia này KHÔNG chống được rò rỉ.")
    assignment = assign_groups(dict(sizes), args.ratios, args.seed)

    args.output.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(args.names):
        chosen = [str(p.resolve()) for p in paths if assignment[groups[p]] == index]
        (args.output / f"{name}.txt").write_text("\n".join(chosen) + "\n", encoding="utf-8")
        n_groups = sum(1 for g in sizes if assignment[g] == index)
        print(f"{name}: {len(chosen)} ảnh từ {n_groups} video ({len(chosen) / len(paths):.1%})")
    with (args.output / "groups.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["group", "n_images", "split"])
        for group in sorted(sizes):
            writer.writerow([group, sizes[group], args.names[assignment[group]]])


if __name__ == "__main__":
    main()
