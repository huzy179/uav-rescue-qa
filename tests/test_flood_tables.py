"""Bảng Markdown của tập test lũ (eval/flood_tables.py) từ dữ liệu giả, không cần mô hình hay data/."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

import eval.flood_tables as ft


def make_flood(root: Path) -> Path:
    flood = root / "flood"
    (flood / "images" / "test").mkdir(parents=True)
    for name in ("vida_000000.jpg", "vida_000060.jpg", "vidb_000000.jpg"):
        Image.new("RGB", (100, 50)).save(flood / "images" / "test" / name)
    pd.DataFrame({
        "image": ["vida_000000.jpg", "vida_000000.jpg", "vidb_000000.jpg"],
        "x1": [0, 10, 0], "y1": [0, 10, 0], "x2": [5, 30, 40], "y2": [5, 50, 40],
        "partly_submerged": [True, False, False], "occluded": [False, False, True],
    }).to_csv(flood / "boxes_test.csv", index=False)
    pd.DataFrame({"image": ["vida_000000.jpg", "vida_000060.jpg", "vidb_000000.jpg"], "glare": [1, 0, 0], "blur": [0, 0, 1]}
                 ).to_csv(flood / "tags_test.csv", index=False)
    return flood


def make_runs(root: Path) -> Path:
    runs = root / "runs"
    for name, iou in (("E1", "0.5"), ("E1", "0.3"), ("E2c", "0.5"), ("E2c", "0.3")):
        d = runs / f"eval_{name}_iou{iou}"
        d.mkdir(parents=True)
        pd.DataFrame([{"config": "x", "size_bin": b, "n_images": 3, "n_gt": n, "AP": 0.5, "recall": 0.25, "precision": 0.9,
                       "recall_max": 0.6, "AP_lo": 0.4, "AP_hi": 0.6, "recall_lo": 0.2, "recall_hi": 0.3}
                      for b, n in (("all", 3), ("<8", 1), ("8-16", 0), ("16-32", 1), (">32", 1))]).to_csv(d / "eval_by_size.csv", index=False)
    d = runs / "compare_E1_E2c_iou0.5"
    d.mkdir()
    pd.DataFrame([{"size_bin": "all", "metric": m, "A": 0.4, "B": 0.5, "diff": -0.021 if m == "AP" else 0.1,
                   "diff_lo": -0.038, "diff_hi": 0.017, "p_value": 0.206, "significant": m == "recall"} for m in ("AP", "recall")]
                 ).to_csv(d / "compare.csv", index=False)
    d = runs / "eval_tags"
    d.mkdir()
    pd.DataFrame([{"run": "runs/flood/E2c", "subset": "glare", "kind": "tag", "n_gt": 2, "recall": 0.5, "recall_lo": 0.0,
                   "recall_hi": 1.0, "n_images": 1, "fp_per_image": 1.0, "fp_per_image_lo": 1.0, "fp_per_image_hi": 1.0},
                  {"run": "runs/flood/E1", "subset": "glare", "kind": "tag", "n_gt": 2, "recall": 0.1, "recall_lo": 0.0,
                   "recall_hi": 1.0, "n_images": 1, "fp_per_image": 1.0, "fp_per_image_lo": 1.0, "fp_per_image_hi": 1.0}]
                 ).to_csv(d / "recall_by_tag.csv", index=False)
    return runs


def test_num_dau_phay_va_dau_tru() -> None:
    assert ft.num(0.4969) == "0,497"
    assert ft.signed(-0.021) == "−0,021" and ft.signed(0.1) == "+0,100"
    assert ft.num(float("nan")) == "–"


def test_bang_day_du(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    flood, runs = make_flood(tmp_path), make_runs(tmp_path)
    out = tmp_path / "bang.md"
    monkeypatch.setattr("sys.argv", ["x", "--flood", str(flood), "--runs-dir", str(runs), "--names", "E1", "E2c", "E3",
                                     "--cluster-pattern", r"^(.+)_\d+$", "--output", str(out)])
    ft.main()
    text = out.read_text(encoding="utf-8")
    # Bảng 4.4: vida có 2 khung, 2 người (một < 8 px, một 16–32 px), 1 khung trống; vidb một người > 32 px.
    assert "| vida | 2 | 100×50 | 2 | 1 | 0 | 1 | 0 | 1 |" in text
    assert "| vidb | 1 | 100×50 | 1 | 0 | 0 | 0 | 1 | 0 |" in text
    assert "| **Tổng** (2 nguồn, 2 video) | 3 | | 3 | 1 | 0 | 1 | 1 | 1 |" in text
    assert "Người ngập một phần: 1 người" in text and "Loá nước: 1 khung" in text
    # Bảng theo cỡ: số chép từ CSV, nhóm không có người để gạch; E3 chưa có thì ghi chú.
    assert "0,500 (0,400–0,600)" in text
    assert "eval_E3_iou0.5" in text
    # So cặp: hiệu chép nguyên, đánh dấu * khi có ý nghĩa.
    assert "−0,021 (−0,038 đến +0,017) | 0,206" in text
    assert "+0,100 (−0,038 đến +0,017) * | 0,206" in text
    # Theo loại nhiễu: chỉ mô hình chính.
    assert "| Loá nước | 2 | 0,500 (0,000–1,000) | 1 |" in text
    assert "0,100" not in text.split("Theo loại nhiễu")[1]
