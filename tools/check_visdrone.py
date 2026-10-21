"""Kiểm tra VisDrone sau khi chuyển nhãn: đối chiếu từng ảnh với nhãn gốc và kiểm tra định dạng YOLO.

Chạy sau `tools/convert_visdrone.py`. Kết quả in ra màn hình và ghi thành JSON; mã thoát khác 0 nếu có lỗi.
Rò rỉ giữa các tập kiểm tra bằng `tools/check_leakage.py`.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from PIL import Image

from shared.config import parse_args_with_config

PERSON_CLASSES = (1, 2)
IGNORED_REGION = 0


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw/visdrone"), help="Thư mục chứa VisDrone2019-DET-<tập>")
    parser.add_argument("--processed", type=Path, default=Path("data/processed/visdrone"), help="Thư mục đầu ra của convert_visdrone.py")
    parser.add_argument("--splits", nargs="+", default=["train", "val"], help="Các tập cần kiểm tra")
    parser.add_argument("--output", type=Path, default=Path("runs/data/visdrone_check.json"), help="File JSON kết quả")
    return parse_args_with_config(parser)


def check_split(raw: Path, processed: Path, split: str, problems: list[str]) -> dict[str, object]:
    """Kiểm tra một tập; ghi lỗi vào `problems`, trả về thống kê."""
    src = raw / f"VisDrone2019-DET-{split}"
    raw_images = sorted((src / "images").glob("*.jpg"))
    n_out_images = len(list((processed / "images" / split).glob("*.jpg")))
    n_labels = len(list((processed / "labels" / split).glob("*.txt")))
    if not (len(raw_images) == n_out_images == n_labels):
        problems.append(f"{split}: {len(raw_images)} ảnh gốc, {n_out_images} ảnh đã chuyển, {n_labels} file nhãn")

    raw_counts: Counter[str] = Counter()
    n_boxes = n_empty = n_dup = n_raw_outside = n_tiny = max_per_image = 0
    max_overflow = 0.0
    for image_path in raw_images:
        stem = image_path.stem
        with Image.open(image_path) as img:
            width, height = img.size
            img.verify()

        persons_raw = 0
        for line in (src / "annotations" / f"{stem}.txt").read_text().splitlines():
            parts = line.strip().rstrip(",").split(",")
            if len(parts) < 6:
                continue
            x, y, w, h, score, category = (int(v) for v in parts[:6])
            if category == 1:
                raw_counts["pedestrian" if score == 1 else "person_score0"] += 1
            elif category == 2:
                raw_counts["people" if score == 1 else "person_score0"] += 1
            elif category == IGNORED_REGION:
                raw_counts["ignored_region"] += 1
            if category in PERSON_CLASSES and score == 1 and w > 0 and h > 0:
                persons_raw += 1
                n_raw_outside += x < 0 or y < 0 or x + w > width or y + h > height

        label_path = processed / "labels" / split / f"{stem}.txt"
        if not label_path.is_file():
            problems.append(f"{split}/{stem}: thiếu file nhãn")
            continue
        rows = [r.split() for r in label_path.read_text().splitlines() if r.strip()]
        if len(rows) != persons_raw:
            problems.append(f"{split}/{stem}: {len(rows)} box YOLO, nhãn gốc có {persons_raw} người")
        seen: set[tuple[str, ...]] = set()
        for row in rows:
            if len(row) != 5 or row[0] != "0":
                problems.append(f"{split}/{stem}: dòng sai định dạng {' '.join(row)}")
                continue
            cx, cy, bw, bh = map(float, row[1:])
            max_overflow = max(max_overflow, bw / 2 - cx, bh / 2 - cy, cx + bw / 2 - 1, cy + bh / 2 - 1)
            n_tiny += bw * width < 2 or bh * height < 2
            n_dup += tuple(row) in seen
            seen.add(tuple(row))
        n_boxes += len(rows)
        n_empty += not rows
        max_per_image = max(max_per_image, len(rows))

    stats_path = processed / f"stats_{split}.json"
    by_size = json.loads(stats_path.read_text(encoding="utf-8"))["persons_by_short_side_px"] if stats_path.is_file() else None
    if max_overflow > 1e-5:
        problems.append(f"{split}: box YOLO tràn ra ngoài ảnh {max_overflow:.2e} (lớn hơn sai số làm tròn)")
    return {
        "n_images": len(raw_images),
        "raw_pedestrian": raw_counts["pedestrian"],
        "raw_people": raw_counts["people"],
        "raw_person_score0": raw_counts["person_score0"],
        "raw_ignored_regions": raw_counts["ignored_region"],
        "raw_person_boxes_outside_image": n_raw_outside,
        "yolo_person_boxes": n_boxes,
        "images_without_person": n_empty,
        "max_persons_per_image": max_per_image,
        "duplicate_boxes": n_dup,
        "boxes_side_under_2px": n_tiny,
        "max_overflow_normalized": max_overflow,
        "persons_by_short_side_px": by_size,
    }


def main() -> None:
    """Kiểm tra từng tập, ghi kết quả ra JSON."""
    args = parse_args()
    problems: list[str] = []
    splits = {split: check_split(args.raw, args.processed, split, problems) for split in args.splits}
    result = {"splits": splits, "problems": problems}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Kết quả lưu tại: {args.output}")
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
