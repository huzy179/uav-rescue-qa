"""Kiểm tra recall theo loại nhiễu bằng ví dụ tính tay."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from eval.recall_by_tag import match_flags, ratio_ci

ROOT = Path(__file__).resolve().parents[1]


def test_match_tham_lam_va_vung_bo_qua() -> None:
    gts = np.array([[0, 0, 10, 10], [100, 100, 110, 110]], float)
    preds = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60], [200, 200, 210, 210]], float)
    confs = np.array([0.9, 0.8, 0.7, 0.6])
    ignore = np.array([[195, 195, 215, 215]], float)
    found, fp = match_flags(preds, confs, gts, 0.5, ignore)
    # người 1 khớp; box thứ hai trùng người 1 là báo nhầm; (50,50) báo nhầm; (200,200) nằm trong vùng bỏ qua
    assert found.tolist() == [True, False] and fp == 2


def test_ratio_ci_khong_bootstrap() -> None:
    assert np.isnan(ratio_ci(np.array([1.0]), np.array([2.0]), np.array([0]), 0)[0])
    lo, hi = ratio_ci(np.array([1.0, 1.0]), np.array([1.0, 1.0]), np.array([0, 1]), 200)
    assert lo == hi == 1.0


def test_chay_tron_tren_du_lieu_nho(tmp_path: Path) -> None:
    ann, run = tmp_path / "flood", tmp_path / "run"
    (ann / "images" / "test").mkdir(parents=True)
    run.mkdir()
    for name in ("a.jpg", "b.jpg"):
        Image.new("RGB", (100, 100)).save(ann / "images" / "test" / name)
    pd.DataFrame({
        "image": ["a.jpg", "a.jpg", "b.jpg"], "x1": [0, 50, 0], "y1": [0, 50, 0], "x2": [10, 60, 10], "y2": [10, 60, 10],
        "partly_submerged": [1, 0, 0], "occluded": [0, 0, 1],
    }).to_csv(ann / "boxes_test.csv", index=False)
    pd.DataFrame({"image": ["a.jpg", "b.jpg"], "glare": [1, 0], "weather": [0, 0], "blur": [0, 0],
                  "floating_debris": [0, 1]}).to_csv(ann / "tags_test.csv", index=False)
    pd.DataFrame({  # a: thấy người 1, sót người 2; b: thấy người, thêm một báo nhầm; một box conf thấp bị bỏ
        "image": ["a.jpg", "b.jpg", "b.jpg", "b.jpg"], "x1": [0, 0, 80, 50], "y1": [0, 0, 80, 50],
        "x2": [10, 10, 90, 60], "y2": [10, 10, 90, 60], "conf": [0.9, 0.8, 0.5, 0.1],
    }).to_csv(run / "boxes.csv", index=False)
    out = tmp_path / "out"
    subprocess.run([sys.executable, str(ROOT / "eval/recall_by_tag.py"), "--runs", str(run), "--annotations", str(ann),
                    "--bootstrap", "0", "--output", str(out)], check=True, cwd=ROOT, capture_output=True)
    t = pd.read_csv(out / "recall_by_tag.csv").set_index("subset")
    assert t.loc["tất cả", "recall"] == 2 / 3 and t.loc["tất cả", "fp_per_image"] == 0.5
    assert t.loc["glare", "recall"] == 0.5 and t.loc["glare", "n_gt"] == 2
    assert t.loc["floating_debris", "fp_per_image"] == 1.0
    assert t.loc["partly_submerged", "recall"] == 1.0 and t.loc["occluded", "recall"] == 1.0
    assert t.loc["người không thuộc tính", "recall"] == 0.0
    assert np.isnan(t.loc["weather", "recall"])
