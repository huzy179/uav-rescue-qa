"""Kiểm tra hiệu chỉnh hồ sơ thiết bị từ timings.jsonl, bằng ví dụ tính tay."""

from __future__ import annotations

import pytest

from tools.fit_device_profile import fit, fit_resize

TILED = [{"infer_ms": 120.0, "n_tiles": 32, "tile_ms": 0.05, "merge_ms": 0.4, "georef_ms": 0.05, "confirm_ms": 0.05}] * 3
RESIZED = [{"infer_ms": 30.0, "n_tiles": 6, "tile_ms": 46.05}] * 3


def test_fit_per_tile_and_overhead() -> None:
    overhead, tile, full = fit(TILED, None)
    assert tile == pytest.approx(3.75)
    assert overhead == pytest.approx(0.55)
    assert full == pytest.approx(15.0)  # không có lần chạy toàn ảnh: 4 × ô


def test_fit_resize_per_megapixel() -> None:
    # (46,05 − 0,05) / 8 MP = 5,75 ms/MP
    assert fit_resize(TILED, RESIZED, 8.0) == pytest.approx(5.75)
    assert fit_resize(RESIZED, TILED, 8.0) == 0.0  # không âm
