"""Kiểm tra trích khung: khoảng cách tối thiểu, bỏ khung gần trùng, giới hạn số khung, tên file theo video."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from eval.splits import group_of
from eval.frames import Candidate, make_video_id, save_frames, scan_video, select_frames


def write_video(path: Path, scenes: list[np.ndarray], frames_per_scene: int, fps: float = 10.0) -> None:
    """Video MJPG: mỗi cảnh lặp lại `frames_per_scene` khung."""
    h, w = scenes[0].shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    assert writer.isOpened()
    for scene in scenes:
        for _ in range(frames_per_scene):
            writer.write(scene)
    writer.release()


def random_scene(seed: int) -> np.ndarray:
    """Cảnh ngẫu nhiên có cấu trúc thô (khối 8×8 phóng to) để dHash phân biệt được sau nén."""
    rng = np.random.default_rng(seed)
    coarse = rng.integers(0, 256, size=(8, 9, 3), dtype=np.uint8)
    return cv2.resize(coarse, (144, 128), interpolation=cv2.INTER_NEAREST)


def cand(frame: int, hash_: int) -> Candidate:
    return Candidate(frame=frame, t_s=frame / 10, hash=hash_)


def test_select_bo_khung_gan_trung_moi_khung_da_giu() -> None:
    a, b = 0, (1 << 20) - 1  # khác nhau 20 bit
    chosen = select_frames([cand(0, a), cand(10, a | 1), cand(20, b), cand(30, a)], max_frames=30, min_hamming=10)
    assert [c.frame for c in chosen] == [0, 20]


def test_select_rai_deu_khi_qua_nhieu() -> None:
    candidates = [cand(i * 10, (1 << (i + 1) * 12) - 1 if i else 0) for i in range(5)]
    chosen = select_frames(candidates, max_frames=3, min_hamming=1)
    assert [c.frame for c in chosen] == [0, 20, 40]


def test_select_tu_choi_max_frames_0() -> None:
    with pytest.raises(ValueError):
        select_frames([], max_frames=0, min_hamming=10)


@pytest.mark.parametrize("name, expected", [
    ("Lũ Yagi 2024 (flycam)", "Lu-Yagi-2024-flycam"),
    ("Đà Nẵng ngập", "Da-Nang-ngap"),
    ("clip_01", "clip-01"),
    ("a.b-c", "a.b-c"),
])
def test_make_video_id(name: str, expected: str) -> None:
    assert make_video_id(name) == expected


def test_trich_khung_tu_video(tmp_path: Path) -> None:
    # 10 FPS, 5 cảnh khác nhau mỗi cảnh 2 giây, cảnh thứ 6 lặp lại cảnh đầu, cuối là 1 giây màn đen.
    scenes = [random_scene(s) for s in range(5)]
    path = tmp_path / "clip.avi"
    write_video(path, scenes + [scenes[0], np.zeros_like(scenes[0])], frames_per_scene=20)

    candidates, fps = scan_video(path, min_gap_s=1.0, min_std=5.0)
    assert fps == pytest.approx(10.0)
    frames = [c.frame for c in candidates]
    assert all(b - a >= 10 for a, b in zip(frames, frames[1:]))  # cách nhau ít nhất 1 giây
    assert max(frames) < 120  # màn đen bị bỏ

    chosen = select_frames(candidates, max_frames=30, min_hamming=10)
    assert [c.frame // 20 for c in chosen] == [0, 1, 2, 3, 4]  # mỗi cảnh một khung; cảnh lặp lại bị bỏ

    out = tmp_path / "frames"
    out.mkdir()
    files = save_frames(path, chosen, out, "clip", jpeg_quality=95)
    assert [f.name for f in files] == [f"clip_{c.frame:06d}.jpg" for c in chosen]
    assert all(group_of(f.stem) == "clip" for f in files)
    assert cv2.imread(str(files[0])).shape == scenes[0].shape
