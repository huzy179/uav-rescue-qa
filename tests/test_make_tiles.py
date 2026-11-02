"""Kiểm tra cắt ô có nhãn: lưới ô như detector, box cắt theo mép ô, bỏ người còn quá ít trong ô."""

from __future__ import annotations

import importlib.util
import random
from pathlib import Path

import cv2
import numpy as np

spec = importlib.util.spec_from_file_location("make_tiles", Path(__file__).resolve().parents[1] / "tools" / "make_tiles.py")
make_tiles_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_tiles_module)  # type: ignore[union-attr]
tile_labels, make_tiles = make_tiles_module.tile_labels, make_tiles_module.make_tiles


def test_box_cat_theo_mep_o() -> None:
    # Người 20×40 px tại (90..110, 0..40); ô bắt đầu x=100 rộng 100: còn nửa phải (100..110), đúng 50% diện tích.
    boxes = np.array([[0, 90, 0, 110, 40]], dtype=float)
    assert tile_labels(boxes, 100, 0, 100, 100, 0.5) == ["0 0.050000 0.200000 0.100000 0.400000\n"]
    assert tile_labels(boxes, 100, 0, 100, 100, 0.6) == []
    assert tile_labels(boxes, 0, 0, 100, 100, 0.5) == ["0 0.950000 0.200000 0.100000 0.400000\n"]


def test_cat_anh_va_uu_tien_o_co_nguoi(tmp_path: Path) -> None:
    images, labels = tmp_path / "images", tmp_path / "labels"
    images.mkdir()
    labels.mkdir()
    cv2.imwrite(str(images / "a.jpg"), np.full((200, 300, 3), 128, np.uint8))
    # Một người 10×10 px ở góc dưới phải (280..290, 180..190).
    (labels / "a.txt").write_text(f"0 {285 / 300} {185 / 200} {10 / 300} {10 / 200}\n", encoding="utf-8")

    # Ô 100, chồng 0: lưới 3 × 2 = 6 ô; chỉ lấy 1 ô thì phải là ô chứa người.
    n_tiles, n_persons = make_tiles(images, labels, tmp_path / "out", "val", 100, 0.0, 0.5, 1, random.Random(0), 95)
    assert (n_tiles, n_persons) == (1, 1)
    out = sorted((tmp_path / "out" / "images" / "val").iterdir())
    assert [p.name for p in out] == ["a_x200_y100.jpg"]
    assert cv2.imread(str(out[0])).shape[:2] == (100, 100)

    n_tiles, n_persons = make_tiles(images, labels, tmp_path / "all", "val", 100, 0.0, 0.5, None, random.Random(0), 95)
    assert (n_tiles, n_persons) == (6, 1)
    assert (tmp_path / "all" / "labels" / "val" / "a_x0_y0.txt").read_text(encoding="utf-8") == ""
