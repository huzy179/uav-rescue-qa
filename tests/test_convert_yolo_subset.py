"""Kiểm tra chuyển bộ YOLO nhiều lớp về một lớp person theo tên lớp."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

SPEC = importlib.util.spec_from_file_location("convert_yolo_subset", Path("tools/convert_yolo_subset.py"))
convert = importlib.util.module_from_spec(SPEC)
sys.modules["convert_yolo_subset"] = convert
SPEC.loader.exec_module(convert)


def test_read_class_names_variants(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("names: {0: boat, 1: human}\n")
    (tmp_path / "b.yaml").write_text("names: [boat, human]\n")
    (tmp_path / "obj.names").write_text("boat\nhuman\n\n")
    for name in ("a.yaml", "b.yaml", "obj.names"):
        assert convert.read_class_names(tmp_path / name) == ["boat", "human"]


def test_convert_label_lines() -> None:
    lines = ["1 0.5 0.5 0.1 0.2", "0 0.1 0.1 0.05 0.05", "2 0.3 0.3 0.1 0.1", "bad"]
    persons, ignores, dropped = convert.convert_label_lines(lines, keep_ids={1}, ignore_ids={2})
    assert persons == ["0 0.5 0.5 0.1 0.2\n"] and ignores == ["0 0.3 0.3 0.1 0.1\n"] and dropped == 1


def test_end_to_end_both_layouts_and_unknown_class(tmp_path: Path) -> None:
    for layout in ("split_first", "kind_first"):
        src = tmp_path / layout
        images, labels = (src / "train" / "images", src / "train" / "labels") if layout == "split_first" else (src / "images" / "valid", src / "labels" / "valid")
        images.mkdir(parents=True)
        labels.mkdir(parents=True)
        cv2.imwrite(str(images / "a.jpg"), np.zeros((10, 10, 3), np.uint8))
        (labels / "a.txt").write_text("1 0.5 0.5 0.2 0.2\n0 0.1 0.1 0.1 0.1\n")
        (src / "data.yaml").write_text("names: [boat, human]\n")
        split = "train" if layout == "split_first" else "val:valid"
        cmd = [sys.executable, "tools/convert_yolo_subset.py", "--src", str(src), "--dst", str(tmp_path / f"out_{layout}"), "--keep", "human", "--splits", split]
        subprocess.run(cmd, check=True, capture_output=True)
        name = split.split(":")[0]
        assert (tmp_path / f"out_{layout}/labels/{name}/a.txt").read_text() == "0 0.5 0.5 0.2 0.2\n"
    bad = subprocess.run(cmd[:-4] + ["--keep", "person", "--splits", "val:valid"], capture_output=True, text=True)
    assert bad.returncode != 0 and "human" in bad.stderr
