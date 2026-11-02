"""Kiểm tra tần số xử lý theo độ cao (edge/sampler.views_fps)."""

from __future__ import annotations

import pytest

from edge.sampler import views_fps


def test_tan_so_theo_vung_chup_va_van_toc() -> None:
    # Vùng chụp dài 25 m, bay 10 m/s: người ở trong khung 2,5 s; muốn thấy 6 lần thì 2,4 khung/giây.
    assert views_fps(25.0, 10.0, 6, 0.5, 8.0) == pytest.approx(2.4)
    # Bay cao gấp đôi: vùng chụp 50 m, chỉ cần 1,2 khung/giây.
    assert views_fps(50.0, 10.0, 6, 0.5, 8.0) == pytest.approx(1.2)
    # Kẹp trần, sàn; đứng yên thì sàn.
    assert views_fps(5.0, 10.0, 6, 0.5, 8.0) == 8.0
    assert views_fps(400.0, 10.0, 6, 0.5, 8.0) == 0.5
    assert views_fps(25.0, 0.0, 6, 0.5, 8.0) == 0.5
