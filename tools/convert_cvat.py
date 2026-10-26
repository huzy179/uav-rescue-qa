"""Chuyển nhãn tập lũ từ CVAT ("CVAT for images 1.1", XML) sang YOLO một lớp, kèm vùng bỏ qua, thuộc tính và thẻ.

Theo docs/LABELING.md: nhãn `person` (thuộc tính partly_submerged, occluded), nhãn `ignore`; thẻ ảnh glare, weather,
blur, floating_debris. Định dạng YOLO làm mất thuộc tính và thẻ, nên chúng được ghi riêng ra CSV để phân tích recall
theo loại nhiễu (TECHNICAL mục 5.7).

Ghi vào --dst:
    images/<split>/      liên kết cứng tới ảnh gốc (không tốn dung lượng)
    labels/<split>/      YOLO, lớp 0 = person
    ignore/<split>/      vùng bỏ qua dạng YOLO, cùng định dạng với tools/convert_visdrone.py
    boxes_<split>.csv    mỗi người một dòng: ảnh, toạ độ pixel, partly_submerged, occluded
    tags_<split>.csv     mỗi ảnh một dòng: các thẻ (0/1)
    stats_<split>.json

Ví dụ:
    .venv/bin/python tools/convert_cvat.py --xml data/raw/flood/annotations.xml --images data/raw/flood/frames \\
        --dst data/processed/flood --split test
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from shared.config import parse_args_with_config

PERSON, IGNORE = "person", "ignore"
BOX_ATTRIBUTES = ["partly_submerged", "occluded"]
IMAGE_TAGS = ["glare", "weather", "blur", "floating_debris"]


@dataclass
class ImageLabels:
    name: str
    width: int
    height: int
    persons: list[tuple[float, float, float, float, dict[str, bool]]] = field(default_factory=list)
    ignores: list[tuple[float, float, float, float]] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--xml", type=Path, nargs="+", required=True,
                        help="Các file annotations.xml xuất từ CVAT (CVAT for images 1.1), hoặc file .zip xuất ra chứa nó; mỗi task một file")
    parser.add_argument("--images", type=Path, required=True, help="Thư mục chứa các khung đã gán nhãn")
    parser.add_argument("--dst", type=Path, default=Path("data/processed/flood"), help="Thư mục đích")
    parser.add_argument("--split", default="test", help="Tên tập (thư mục con)")
    return parse_args_with_config(parser)


def _clip_box(box: ET.Element, width: int, height: int) -> tuple[float, float, float, float]:
    x1, y1 = max(0.0, float(box.get("xtl", 0))), max(0.0, float(box.get("ytl", 0)))
    x2, y2 = min(float(width), float(box.get("xbr", 0))), min(float(height), float(box.get("ybr", 0)))
    return x1, y1, x2, y2


def parse_cvat(xml_text: str) -> list[ImageLabels]:
    """Đọc XML của CVAT; nhãn hoặc thẻ lạ thì báo lỗi thay vì bỏ qua lặng lẽ (tập test nhỏ, mỗi nhãn đều quan trọng)."""
    root = ET.fromstring(xml_text)
    images = []
    for node in root.iter("image"):
        width, height = int(node.get("width", 0)), int(node.get("height", 0))
        item = ImageLabels(node.get("name", ""), width, height)
        for box in node.findall("box"):
            label = box.get("label")
            x1, y1, x2, y2 = _clip_box(box, width, height)
            if x2 <= x1 or y2 <= y1:
                raise ValueError(f"{item.name}: box '{label}' rỗng sau khi cắt theo mép ảnh")
            if label == PERSON:
                attrs = {a.get("name", ""): (a.text or "").strip().lower() == "true" for a in box.findall("attribute")}
                unknown = set(attrs) - set(BOX_ATTRIBUTES)
                if unknown:
                    raise ValueError(f"{item.name}: thuộc tính lạ {sorted(unknown)}; sửa LABELING.md hoặc CVAT")
                item.persons.append((x1, y1, x2, y2, {name: attrs.get(name, False) for name in BOX_ATTRIBUTES}))
            elif label == IGNORE:
                item.ignores.append((x1, y1, x2, y2))
            else:
                raise ValueError(f"{item.name}: nhãn lạ '{label}' (chỉ có '{PERSON}' và '{IGNORE}')")
        for tag in node.findall("tag"):
            label = tag.get("label", "")
            if label not in IMAGE_TAGS:
                raise ValueError(f"{item.name}: thẻ lạ '{label}' (chỉ có {IMAGE_TAGS})")
            item.tags.add(label)
        images.append(item)
    if not images:
        raise ValueError("XML không có ảnh nào: kiểm tra đã xuất đúng định dạng 'CVAT for images 1.1'")
    return images


def read_xml(path: Path) -> str:
    """Nội dung annotations.xml, đọc thẳng hoặc từ file .zip CVAT xuất ra."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if n.endswith("annotations.xml")]
            if len(names) != 1:
                raise ValueError(f"{path}: cần đúng một annotations.xml trong file zip, thấy {names}")
            return archive.read(names[0]).decode("utf-8")
    return path.read_text(encoding="utf-8")


def parse_many(paths: list[Path]) -> list[ImageLabels]:
    """Gộp nhãn của nhiều task; một ảnh có mặt ở hai task thì báo lỗi (không biết lấy nhãn nào)."""
    images: list[ImageLabels] = []
    seen: dict[str, Path] = {}
    for path in paths:
        for item in parse_cvat(read_xml(path)):
            name = Path(item.name).name
            if name in seen:
                raise ValueError(f"Ảnh {name} có ở cả {seen[name]} và {path}")
            seen[name] = path
            images.append(item)
    return images


def yolo_line(x1: float, y1: float, x2: float, y2: float, width: int, height: int) -> str:
    return f"0 {(x1 + x2) / 2 / width:.6f} {(y1 + y2) / 2 / height:.6f} {(x2 - x1) / width:.6f} {(y2 - y1) / height:.6f}\n"


def main() -> None:
    """Đọc XML, kiểm tra khớp với thư mục ảnh, ghi nhãn YOLO, vùng bỏ qua và CSV thuộc tính."""
    args = parse_args()
    images = parse_many(args.xml)
    on_disk = {p.name for p in args.images.iterdir() if p.is_file()}
    missing = [item.name for item in images if Path(item.name).name not in on_disk]
    if missing:
        raise SystemExit(f"{len(missing)} ảnh trong XML không có trong {args.images}, ví dụ: {missing[:3]}")
    unlabeled = sorted(on_disk - {Path(item.name).name for item in images} - {".DS_Store"})
    if unlabeled:
        print(f"[cảnh báo] {len(unlabeled)} file trong {args.images} không có trong XML (chưa gán nhãn?), ví dụ: {unlabeled[:3]}")

    dirs = {kind: args.dst / kind / args.split for kind in ("images", "labels", "ignore")}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    with (
        (args.dst / f"boxes_{args.split}.csv").open("w", newline="", encoding="utf-8") as box_file,
        (args.dst / f"tags_{args.split}.csv").open("w", newline="", encoding="utf-8") as tag_file,
    ):
        box_writer, tag_writer = csv.writer(box_file), csv.writer(tag_file)
        box_writer.writerow(["image", "x1", "y1", "x2", "y2", *BOX_ATTRIBUTES])
        tag_writer.writerow(["image", *IMAGE_TAGS])
        for item in images:
            name = Path(item.name).name
            src, dst = args.images / name, dirs["images"] / name
            if not dst.exists():
                try:
                    os.link(src, dst)
                except OSError:
                    shutil.copy2(src, dst)
            stem = Path(name).stem
            (dirs["labels"] / f"{stem}.txt").write_text(
                "".join(yolo_line(*p[:4], item.width, item.height) for p in item.persons), encoding="utf-8"
            )
            (dirs["ignore"] / f"{stem}.txt").write_text(
                "".join(yolo_line(*b, item.width, item.height) for b in item.ignores), encoding="utf-8"
            )
            for x1, y1, x2, y2, attrs in item.persons:
                box_writer.writerow([name, round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2), *(int(attrs[a]) for a in BOX_ATTRIBUTES)])
            tag_writer.writerow([name, *(int(tag in item.tags) for tag in IMAGE_TAGS)])

    stats = {
        "n_images": len(images),
        "n_images_without_person": sum(not item.persons for item in images),
        "n_persons": sum(len(item.persons) for item in images),
        "n_ignore_regions": sum(len(item.ignores) for item in images),
        "persons_by_attribute": {a: sum(p[4][a] for item in images for p in item.persons) for a in BOX_ATTRIBUTES},
        "images_by_tag": {t: sum(t in item.tags for item in images) for t in IMAGE_TAGS},
    }
    (args.dst / f"stats_{args.split}.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
