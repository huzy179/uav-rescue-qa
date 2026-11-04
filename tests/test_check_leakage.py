"""Kiểm tra công cụ rò rỉ: ảnh trùng tên ở hai bộ huấn luyện không ghi đè nhau."""

import importlib.util
import sys
from pathlib import Path

import cv2
import numpy as np

SPEC = importlib.util.spec_from_file_location("check_leakage", Path("tools/check_leakage.py"))
leakage = importlib.util.module_from_spec(SPEC)
sys.modules["check_leakage"] = leakage
SPEC.loader.exec_module(leakage)


def test_hash_folder_keys_differ_across_datasets(tmp_path: Path) -> None:
    rng = np.random.default_rng(0)
    keys = {}
    for name in ("afo", "c2a"):
        folder = tmp_path / name / "images" / "train"
        folder.mkdir(parents=True)
        cv2.imwrite(str(folder / "0001.png"), rng.integers(0, 255, (32, 32), dtype=np.uint8))
        keys.update(leakage.hash_folder(folder))
    assert sorted(keys) == ["afo/train/0001.png", "c2a/train/0001.png"]
