"""Kiểm tra detector giả của mô phỏng RQ3 khi recall theo cỡ người."""

from __future__ import annotations

import random
from pathlib import Path

from edge.georef import Camera
from sim.scenario import RecallCurve, simulate_detections


def test_recall_curve_bac_thang_va_ngoai_mien(tmp_path: Path) -> None:
    path = tmp_path / "r.csv"
    path.write_text("model,lo,hi,recall\nA,4,8,0.2\nA,8,inf,0.9\nB,4,inf,0.0\n", encoding="utf-8")
    curve = RecallCurve.from_csv(path, "A")
    assert curve(5) == 0.2 and curve(8) == 0.9 and curve(1000) == 0.9 and curve(1) == 0.2
    cam = Camera(1000, 1000, 90.0)
    boxes = [(0, (0.0, 0.0, 5.0, 20.0)), (1, (100.0, 100.0, 130.0, 130.0))]
    dets = simulate_detections(0, 0.0, boxes, cam, RecallCurve.from_csv(path, "B"), 0.0, random.Random(0))
    assert dets == []  # recall 0 ở mọi cỡ
    dets = simulate_detections(0, 0.0, boxes, cam, lambda px: 1.0 if px >= 30 else 0.0, 0.0, random.Random(0))
    assert [d.box_px for d in dets] == [(100.0, 100.0, 130.0, 130.0)]


def test_duong_recall_khi_thu_nho() -> None:
    curve = RecallCurve((0.0, 10.0), (10.0, float("inf")), (0.2, 0.8))
    half = curve.scaled(2.0)  # thu nhỏ 2 lần: người 15 px còn 7,5 px
    assert curve(15.0) == 0.8 and half(15.0) == 0.2 and half(25.0) == 0.8


def test_bay_zigzag_di_ve_va_chuyen_duong() -> None:
    from sim.flight import ZigzagFlight

    f = ZigzagFlight(21.0, 105.8, 50.0, 10.0, 0.0, leg_m=100.0, spacing_m=40.0)
    assert f.local(5.0) == (50.0, 0.0, 0.0)  # đường 1, đi về phía trước
    assert f.local(12.0) == (100.0, 20.0, 90.0)  # đang chuyển sang đường 2
    assert f.local(19.0) == (50.0, 40.0, 180.0)  # đường 2, đi ngược lại
    assert f.at(19.0).yaw_deg == 180.0
    assert f.n_legs(60.0) == 4  # 600 m: 100 + 40 + 100 + 40 + 100 + 40 + 100 = 520 m


def test_ho_so_do_cao() -> None:
    from sim.flight import AltitudeProfile

    p = AltitudeProfile.parse("0:120,20:120,30:40")
    assert (p(-1), p(10), p(25), p(30), p(99)) == (120, 120, 80, 40, 40)
