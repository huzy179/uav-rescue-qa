"""Quy tắc chọn khung cố định của tools/demo_panels.py (không cần ảnh, mô hình hay data/)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

import tools.demo_panels as demo_panels
from console.errors import ImageErrors


def frame(name: str, sides: list[float], n_tp: int) -> "demo_panels.Frame":
    gts = np.array([[0.0, 0.0, s, s] for s in sides]).reshape(-1, 4)
    b = ImageErrors(tp=[(j, j) for j in range(n_tp)], fn=list(range(n_tp, len(sides))))
    return demo_panels.Frame(name, Path(name), gts, None, ImageErrors(), b, np.zeros((0, 4)), np.zeros((0, 4)))


def test_pick_theo_quy_tac() -> None:
    frames = [
        frame("c.jpg", [5, 6, 7, 30], 1),        # 3 người < 16 px, bỏ sót 3, recall 0,25
        frame("a.jpg", [20, 20, 20, 20], 2),     # recall 0,5
        frame("b.jpg", [10, 40, 40], 3),         # recall 1
    ]
    # recall chung của B: 6 / 11
    assert demo_panels.pick(frames, "nho_nhat").name == "c.jpg"
    assert demo_panels.pick(frames, "loi").name == "c.jpg"
    assert demo_panels.pick(frames, "tieu_bieu").name == "a.jpg"


def test_pick_hoa_lay_ten_nho_nhat() -> None:
    frames = [frame("z.jpg", [5, 5], 0), frame("m.jpg", [5, 5], 0)]
    assert demo_panels.pick(frames, "nho_nhat").name == "m.jpg"
    assert demo_panels.pick(frames, "loi").name == "m.jpg"
