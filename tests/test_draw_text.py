"""Vẽ chữ có dấu lên ảnh BGR (eval/draw.put_text), có đường lùi khi thiếu font."""

from __future__ import annotations

import numpy as np
import pytest

import eval.draw as draw


def test_strip_accents() -> None:
    assert draw.strip_accents("MẤT SÓNG - cảnh báo chờ gửi bù, độ trễ") == "MAT SONG - canh bao cho gui bu, do tre"


@pytest.mark.parametrize("has_font", [True, False])
def test_put_text_draws_inside_box(monkeypatch: pytest.MonkeyPatch, has_font: bool) -> None:
    if not has_font:
        monkeypatch.setattr(draw, "_font", lambda size_px: None)
    elif draw._font(20) is None:
        pytest.skip("máy không có font Unicode")
    image = np.zeros((100, 400, 3), dtype=np.uint8)
    out = draw.put_text(image, "Thiết bị giả lập", (10, 20), 20, (255, 255, 255), 2)
    assert out is image
    ys, xs = np.nonzero(image.any(axis=2))
    assert len(xs) > 0
    w, h = draw.text_size("Thiết bị giả lập", 20, 2)
    assert xs.min() >= 8 and xs.max() <= 10 + w + 4
    assert ys.min() >= 18 and ys.max() <= 20 + h + 4


def test_put_text_clipped_at_edge_does_not_fail() -> None:
    image = np.zeros((30, 50, 3), dtype=np.uint8)
    draw.put_text(image, "chữ dài vượt khỏi mép ảnh", (40, 20), 24, (0, 255, 255), 2)
    draw.put_text(image, "ngoài ảnh", (100, 100), 24, (0, 255, 255))
    assert image.shape == (30, 50, 3)
