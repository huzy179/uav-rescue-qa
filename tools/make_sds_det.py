"""Dựng tập đánh giá phát hiện người dưới nước từ SeaDronesSee-MOT: 1 khung mỗi --every khung, nhãn YOLO một lớp person.

Khung liền nhau trong video gần như giống hệt, nên chỉ lấy thưa; tên ảnh v<video>_<khung>.jpg để bootstrap theo video
(eval_by_size.py --cluster-pattern '^(v\\d+)_'). Lớp swimmer và swimmer with life jacket thành person; thuyền bỏ.

Ví dụ:
    .venv/bin/python tools/make_sds_det.py --src data/raw/seadronessee_mot --dst data/processed/sds_det --split val --every 15
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
from collections import defaultdict
from pathlib import Path

from shared.config import parse_args_with_config

PERSON_NAMES = {"swimmer", "swimmer with life jacket"}


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", type=Path, required=True, help="Thư mục có annotations/<split>.json và images/<split>/")
    parser.add_argument("--dst", type=Path, required=True, help="Thư mục đích (images/<split>, labels/<split>)")
    parser.add_argument("--split", default="val", help="Phần dữ liệu")
    parser.add_argument("--every", type=int, default=15, help="Lấy khung có frame_index chia hết cho số này")
    return parse_args_with_config(parser)


def main() -> None:
    """Chọn khung thưa, liên kết ảnh, ghi nhãn YOLO, in thống kê kích thước người."""
    args = parse_args()
    data = json.loads((args.src / "annotations" / f"{args.split}.json").read_text(encoding="utf-8"))
    persons = {c["id"] for c in data["categories"] if c["name"] in PERSON_NAMES}
    boxes = defaultdict(list)
    for ann in data["annotations"]:
        if ann["category_id"] in persons:
            boxes[ann["image_id"]].append(ann["bbox"])
    images_dir, labels_dir = args.dst / "images" / args.split, args.dst / "labels" / args.split
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    sizes, n_images, videos = [], 0, set()
    for image in data["images"]:
        if image["frame_index"] % args.every:
            continue
        name = f"v{image['video_id']:02d}_{image['frame_index']:06d}"
        target = images_dir / f"{name}.jpg"
        if not target.exists():
            try:
                os.link(args.src / "images" / args.split / image["file_name"], target)
            except OSError:
                shutil.copy2(args.src / "images" / args.split / image["file_name"], target)
        w_img, h_img = image["width"], image["height"]
        lines = [f"0 {(x + w / 2) / w_img:.6f} {(y + h / 2) / h_img:.6f} {w / w_img:.6f} {h / h_img:.6f}\n"
                 for x, y, w, h in boxes[image["id"]]]
        (labels_dir / f"{name}.txt").write_text("".join(lines), encoding="utf-8")
        sizes += [min(w, h) for _, _, w, h in boxes[image["id"]]]
        n_images += 1
        videos.add(image["video_id"])
    print(f"{n_images} ảnh, {len(sizes)} người, {len(videos)} video; cạnh ngắn người trung vị "
          f"{statistics.median(sizes) if sizes else 0:.0f} px")


if __name__ == "__main__":
    main()
