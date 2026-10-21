"""Kiểm tra chia theo video và phát hiện ảnh gần trùng."""

import numpy as np
import pytest

from eval.splits import assign_groups, dhash, group_of, hamming_matrix, near_duplicates


def test_group_of_flood_naming_and_fallback() -> None:
    assert group_of("lu_hue_2020_a_000120") == "lu_hue_2020_a"
    assert group_of("0000001_02999_d_0000005", r"^(\d+)_") == "0000001"
    assert group_of("anh_le") == "anh_le"  # không khớp: mỗi ảnh một nhóm


def test_assign_groups_keeps_videos_whole_and_near_ratio() -> None:
    sizes = {f"v{i}": 10 for i in range(10)}
    assignment = assign_groups(sizes, [0.8, 0.2], seed=1)
    assert set(assignment) == set(sizes)
    assert sum(sizes[g] for g, s in assignment.items() if s == 1) == 20
    assert assign_groups(sizes, [0.8, 0.2], seed=1) == assignment  # tái lập
    with pytest.raises(ValueError):
        assign_groups(sizes, [0.0, 0.0])


def test_dhash_survives_resize_and_brightness_but_not_new_scene() -> None:
    rng = np.random.default_rng(0)
    scene = (rng.random((90, 160)) * 255).astype(np.uint8)
    import cv2

    scene = cv2.GaussianBlur(scene, (0, 0), 6)
    resized = cv2.resize(scene, (320, 180))
    brighter = np.clip(scene.astype(int) + 20, 0, 255).astype(np.uint8)
    other = cv2.GaussianBlur((rng.random((90, 160)) * 255).astype(np.uint8), (0, 0), 6)
    h = {name: dhash(img) for name, img in {"a": scene, "b": resized, "c": brighter, "d": other}.items()}
    pairs = {(x, y) for x, y, _ in near_duplicates(h, max_distance=5)}
    assert ("a", "b") in pairs and ("a", "c") in pairs
    assert not any("d" in pair for pair in pairs)


def test_hamming_matrix_counts_bits() -> None:
    a = np.array([0, 0b1011], dtype=np.uint64)
    b = np.array([0, 2**63], dtype=np.uint64)
    assert hamming_matrix(a, b).tolist() == [[0, 1], [3, 4]]


def test_size_table_counts_lost_labels() -> None:
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("label_size_stats", Path("tools/label_size_stats.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    table = module.size_table(np.array([3.0, 5.0, 10.0, 40.0]), [1.0, 0.5])
    assert table.loc[0, "<2 (mất nhãn)"] == 0 and table.loc[0, "2-4"] == 0.25
    assert table.loc[1, "<2 (mất nhãn)"] == 0.25  # 3 px × 0,5 = 1,5 px
