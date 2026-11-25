"""Kiểm tra phần không cần Chrome của tools/thesis_figures.py: đọc cỡ SVG, nhóm cấu hình, tâm nhóm trên trục log."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from tools.thesis_figures import group_centres, plot_pareto, plot_recall_by_pixels, setting_of, svg_size


def test_doc_co_svg(tmp_path: Path) -> None:
    svg = tmp_path / "a.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="640" viewBox="0 0 1400 640"/>',
                   encoding="utf-8")
    assert svg_size(svg) == (1400, 640)
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>', encoding="utf-8")
    with pytest.raises(ValueError):
        svg_size(svg)


def test_nhom_cau_hinh_theo_ten_bien_the() -> None:
    assert setting_of("fp16_full1280") == "full"
    assert setting_of("int8_tiled") == "tiled"
    assert setting_of("pt_tiled_px10") == "tiled_px10"


def test_tam_nhom_tren_truc_log_nhu_eval() -> None:
    group = pd.DataFrame({"lo": [0.0, 8.0, 96.0], "hi": [4.0, 16.0, math.inf]})
    centres = group_centres(group)
    assert centres[0] == pytest.approx(math.sqrt(2 * 4))       # cận dưới kẹp ở 2
    assert centres[1] == pytest.approx(math.sqrt(8 * 16))
    assert centres[2] == pytest.approx(math.sqrt(96 * 96 * 1.41))  # nhóm cuối: thêm một bậc √2


def test_ve_ra_file(tmp_path: Path) -> None:
    pixels = pd.DataFrame({"model": ["E1", "E1", "E2c", "E2c"], "lo": [4.0, 8.0, 4.0, 8.0], "hi": [8.0, 16.0, 8.0, 16.0],
                           "recall": [0.1, 0.2, 0.4, 0.5], "recall_lo": [0.0, 0.1, 0.3, 0.4],
                           "recall_hi": [0.2, 0.3, 0.5, 0.6]})
    plot_recall_by_pixels(pixels, tmp_path / "a.png")
    pareto = pd.DataFrame({"variant": ["fp16_full1280", "pt_tiled", "fp16_tiled_px10"], "fps_at_p95": [40.0, 2.5, 11.6],
                           "recall": [0.47, 0.37, 0.58], "on_front": [True, False, True]})
    plot_pareto(pareto, tmp_path / "b.png")
    assert (tmp_path / "a.png").stat().st_size > 0 and (tmp_path / "b.png").stat().st_size > 0
