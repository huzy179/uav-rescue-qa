"""Kiểm tra thu nhỏ tập ảnh cho E6: kích thước ảnh chia đúng hệ số, nhãn chuẩn hoá giữ nguyên."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import cv2
import numpy as np

spec = importlib.util.spec_from_file_location("rescale_dataset", Path(__file__).resolve().parents[1] / "tools" / "rescale_dataset.py")
rescale_dataset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rescale_dataset)  # type: ignore[union-attr]
factor_name, rescale = rescale_dataset.factor_name, rescale_dataset.rescale


def test_ten_thu_muc_theo_he_so() -> None:
    assert factor_name(2) == "x2" and factor_name(2.1) == "x2.1" and factor_name(1.0) == "x1"


def test_thu_nho_anh_va_giu_nhan(tmp_path: Path) -> None:
    images, labels = tmp_path / "images", tmp_path / "labels"
    images.mkdir()
    labels.mkdir()
    cv2.imwrite(str(images / "a.jpg"), np.full((200, 400, 3), 128, np.uint8))
    (labels / "a.txt").write_text("0 0.5 0.5 0.1 0.2\n", encoding="utf-8")
    cv2.imwrite(str(images / "b.jpg"), np.zeros((100, 100, 3), np.uint8))  # ảnh không có nhãn

    assert rescale(images, labels, tmp_path / "out", 4, "val", 95) == 2
    out = tmp_path / "out" / "x4"
    assert cv2.imread(str(out / "images" / "val" / "a.jpg")).shape[:2] == (50, 100)
    assert (out / "labels" / "val" / "a.txt").read_text(encoding="utf-8") == "0 0.5 0.5 0.1 0.2\n"
    assert not (out / "labels" / "val" / "b.txt").exists()
