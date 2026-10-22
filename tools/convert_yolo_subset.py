"""Chuyển một bộ dữ liệu YOLO nhiều lớp (C2A, AFO, ...) về một lớp person, kèm vùng bỏ qua, theo TÊN lớp.

Chọn lớp theo tên đọc từ chính bộ dữ liệu (data.yaml, obj.names hoặc classes.txt), không đoán mã số lớp: mỗi bộ đánh
số khác nhau, đoán sai là huấn luyện nhầm lớp mà không có lỗi nào báo.

Nhận hai cấu trúc thư mục hay gặp:  <src>/<split>/images + labels  hoặc  <src>/images/<split> + labels/<split>.
Ghi ra --dst theo cùng bố cục với tools/convert_visdrone.py: images/<split> (liên kết cứng), labels/<split> (lớp 0),
ignore/<split> (các lớp trong --ignore-classes), stats.json.

Ví dụ:
    .venv/bin/python tools/convert_yolo_subset.py --src data/raw/c2a/C2A_Dataset --dst data/processed/c2a \\
        --keep human --splits train val test
    .venv/bin/python tools/convert_yolo_subset.py --src data/raw/afo --dst data/processed/afo \\
        --keep human --splits train:train val:validation test:test
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

import yaml

from eval.splits import image_paths
from shared.config import parse_args_with_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", type=Path, required=True, help="Thư mục gốc của bộ dữ liệu YOLO")
    parser.add_argument("--dst", type=Path, required=True, help="Thư mục đích, ví dụ data/processed/c2a")
    parser.add_argument("--keep", nargs="+", required=True, help="Tên các lớp được coi là người (gộp về lớp 0)")
    parser.add_argument("--ignore-classes", nargs="*", default=[], help="Tên các lớp ghi thành vùng bỏ qua")
    parser.add_argument("--names-file", type=Path, default=None, help="File tên lớp; mặc định tự tìm trong --src")
    parser.add_argument(
        "--splits", nargs="+", default=["train", "val", "test"],
        help="Tên tập đích, hoặc <đích>:<tên thư mục nguồn> khi khác nhau (ví dụ val:valid)",
    )
    return parse_args_with_config(parser)


def read_class_names(path: Path) -> list[str]:
    """Danh sách tên lớp theo thứ tự mã số, từ data.yaml (names: list hoặc dict) hoặc file mỗi dòng một tên."""
    if path.suffix in (".yaml", ".yml"):
        names = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("names")
        if isinstance(names, dict):
            return [str(names[k]) for k in sorted(names, key=int)]
        if isinstance(names, list):
            return [str(n) for n in names]
        raise ValueError(f"{path} không có khoá names dạng list hoặc dict")
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def find_names_file(src: Path) -> Path:
    """Tìm file tên lớp trong bộ dữ liệu; nhiều hơn một ứng viên thì báo lỗi để người dùng chỉ rõ."""
    candidates = [p for pattern in ("data.yaml", "*.yaml", "obj.names", "*.names", "classes.txt") for p in src.rglob(pattern)]
    unique = sorted(set(candidates))
    if len(unique) != 1:
        raise SystemExit(f"Tìm thấy {len(unique)} file tên lớp trong {src}: {[str(p) for p in unique[:5]]}; chỉ rõ bằng --names-file")
    return unique[0]


def split_dirs(src: Path, name: str) -> tuple[Path, Path]:
    """(thư mục ảnh, thư mục nhãn) của một tập, theo một trong hai cấu trúc hay gặp."""
    for images, labels in ((src / name / "images", src / name / "labels"), (src / "images" / name, src / "labels" / name)):
        if images.is_dir() and labels.is_dir():
            return images, labels
    raise SystemExit(f"Không thấy tập '{name}' trong {src} (đã thử <src>/{name}/images và <src>/images/{name})")


def convert_label_lines(lines: list[str], keep_ids: set[int], ignore_ids: set[int]) -> tuple[list[str], list[str], int]:
    """Tách các dòng YOLO thành (dòng người lớp 0, dòng vùng bỏ qua lớp 0, số dòng bị bỏ)."""
    persons, ignores, dropped = [], [], 0
    for line in lines:
        parts = line.split()
        if len(parts) < 5:
            continue
        class_id, box = int(float(parts[0])), " ".join(parts[1:5])
        if class_id in keep_ids:
            persons.append(f"0 {box}\n")
        elif class_id in ignore_ids:
            ignores.append(f"0 {box}\n")
        else:
            dropped += 1
    return persons, ignores, dropped


def main() -> None:
    """Đọc tên lớp, kiểm tra tên yêu cầu có thật, chuyển từng tập."""
    args = parse_args()
    names = read_class_names(args.names_file or find_names_file(args.src))
    missing = [n for n in args.keep + args.ignore_classes if n not in names]
    if missing:
        raise SystemExit(f"Lớp {missing} không có trong bộ dữ liệu; các lớp hiện có: {names}")
    keep_ids = {names.index(n) for n in args.keep}
    ignore_ids = {names.index(n) for n in args.ignore_classes}

    stats: dict[str, object] = {"src": str(args.src), "class_names": names, "keep": args.keep, "ignore_classes": args.ignore_classes}
    for spec in args.splits:
        dst_name, _, src_name = spec.partition(":")
        images_dir, labels_dir = split_dirs(args.src, src_name or dst_name)
        out = {kind: args.dst / kind / dst_name for kind in ("images", "labels", "ignore")}
        for d in out.values():
            d.mkdir(parents=True, exist_ok=True)
        n_images = n_persons = n_ignore = n_dropped = n_missing_labels = 0
        for image in image_paths(images_dir):
            label = labels_dir / f"{image.stem}.txt"
            n_missing_labels += not label.is_file()
            lines = label.read_text(encoding="utf-8").splitlines() if label.is_file() else []
            persons, ignores, dropped = convert_label_lines(lines, keep_ids, ignore_ids)
            target = out["images"] / image.name
            if not target.exists():
                try:
                    os.link(image, target)
                except OSError:
                    shutil.copy2(image, target)
            (out["labels"] / f"{image.stem}.txt").write_text("".join(persons), encoding="utf-8")
            (out["ignore"] / f"{image.stem}.txt").write_text("".join(ignores), encoding="utf-8")
            n_images += 1
            n_persons += len(persons)
            n_ignore += len(ignores)
            n_dropped += dropped
        stats[dst_name] = {
            "n_images": n_images, "n_persons": n_persons, "n_ignore_regions": n_ignore,
            "n_other_objects_dropped": n_dropped, "n_images_without_label_file": n_missing_labels,
        }
        print(f"{dst_name}: {n_images} ảnh, {n_persons} người, {n_ignore} vùng bỏ qua, bỏ {n_dropped} vật thể lớp khác")
    (args.dst / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
