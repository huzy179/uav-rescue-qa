from __future__ import annotations

import numpy as np
import pytest

from edge.tile_cache import TileCache, is_hovering


def _out(v: float) -> tuple[np.ndarray, np.ndarray]:
    return np.array([[v, v, v + 1, v + 1]]), np.array([0.5])


def test_is_hovering() -> None:
    assert is_hovering(0.2, 1.0)
    assert not is_hovering(0.6, 1.0)
    assert not is_hovering(0.2, -3.0)
    assert not is_hovering(None, 0.0)


def test_first_frame_runs_everything_and_static_tiles_are_reused() -> None:
    cache = TileCache(diff_threshold=4.0, max_age=4)
    tiles = [np.full((64, 64, 3), 100, np.uint8), np.full((64, 64, 3), 200, np.uint8)]
    keys = [(128, 64, 0, 0), (128, 64, 64, 0)]
    assert cache.begin(keys, tiles, allow_reuse=True) == [True, True]  # chưa có gì để dùng lại
    cache.finish([_out(1), _out(2)])
    changed = [tiles[0], np.full((64, 64, 3), 230, np.uint8)]  # ô thứ hai đổi nhiều
    assert cache.begin(keys, changed, allow_reuse=True) == [False, True]
    out = cache.finish([_out(9)])
    assert out[0][0][0, 0] == 1 and out[1][0][0, 0] == 9  # ô 1 lấy kết quả cũ, ô 2 kết quả mới


def test_reuse_needs_permission_and_expires() -> None:
    cache = TileCache(diff_threshold=4.0, max_age=2)
    tile, key = [np.zeros((32, 32, 3), np.uint8)], [(32, 32, 0, 0)]
    cache.begin(key, tile, True)
    cache.finish([_out(1)])
    assert cache.begin(key, tile, allow_reuse=False) == [True]  # drone di chuyển: luôn chạy
    cache.finish([_out(1)])
    runs = []
    for _ in range(5):
        r = cache.begin(key, tile, True)
        runs.append(r[0])
        cache.finish([_out(1)] if r[0] else [])
    assert runs == [False, False, True, False, False]  # dùng lại tối đa 2 lần rồi chạy lại


def test_drift_is_measured_against_last_run_not_last_seen() -> None:
    """Ô sáng dần 3 mức mỗi khung: so với lần chạy gần nhất thì sau hai khung đã vượt ngưỡng 4, phải chạy lại."""
    cache = TileCache(diff_threshold=4.0, max_age=10)
    key = [(32, 32, 0, 0)]
    cache.begin(key, [np.full((32, 32), 100, np.uint8)], True)
    cache.finish([_out(1)])
    runs = []
    for k in (1, 2):
        r = cache.begin(key, [np.full((32, 32), 100 + 3 * k, np.uint8)], True)
        runs.append(r[0])
        cache.finish([_out(1)] if r[0] else [])
    assert runs == [False, True]


def test_finish_checks_count() -> None:
    cache = TileCache()
    cache.begin([(8, 8, 0, 0)], [np.zeros((8, 8), np.uint8)], True)
    with pytest.raises(ValueError):
        cache.finish([])
