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
