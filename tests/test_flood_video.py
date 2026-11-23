"""Video kiểm tra tập lũ (tools/flood_video.py): phần không cần mô hình."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from console.errors import match_errors
from tools.flood_video import draw_labeled, labeled_frames, videos_in


def test_khung_da_gan_theo_video(tmp_path: Path) -> None:
    for name in ["hue-abc_000150.jpg", "hue-abc_000200.jpg", "hue-short-xyz_000010.jpg", "khac.jpg"]:
        (tmp_path / name).touch()
    frames = labeled_frames(tmp_path, "hue-abc")
    assert sorted(frames) == [150, 200]  # không lẫn hue-short-xyz dù cùng tiền tố
    assert videos_in(tmp_path) == ["hue-abc", "hue-short-xyz"]


def test_dong_dem_khop_so_khop() -> None:
    gts = np.array([[10, 10, 20, 20], [50, 50, 60, 60]], float)
    preds = np.array([[10, 10, 20, 20], [100, 100, 110, 110]], float)
    err = match_errors(preds, np.array([0.9, 0.8]), gts, 0.5)
    image = np.zeros((200, 200, 3), np.uint8)
    line = draw_labeled(image, gts, preds, err)
    assert line == "KHUNG ĐÃ GÁN NHÃN: thấy 1/2, bỏ sót 1, báo nhầm 1"
    assert image.any()  # đã vẽ vòng
