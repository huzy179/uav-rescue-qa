"""Kiểm tra ánh xạ tên tham số YOLO26 3 đầu → YOLO26-P2 (training/train.py), không cần mô hình."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("train", Path(__file__).resolve().parents[1] / "training" / "train.py")
train = importlib.util.module_from_spec(spec)
spec.loader.exec_module(train)  # type: ignore[union-attr]


@pytest.mark.parametrize("key, expected", [
    ("model.0.conv.weight", "model.0.conv.weight"),            # backbone giữ chỗ
    ("model.16.cv2.conv.weight", "model.16.cv2.conv.weight"),  # nhánh lên tới P3 giữ chỗ
    ("model.17.conv.weight", "model.23.conv.weight"),          # nhánh xuống P3→P4 dời 6
    ("model.22.m.0.cv1.conv.weight", "model.28.m.0.cv1.conv.weight"),
    ("model.23.cv2.0.0.conv.weight", "model.29.cv2.1.0.conv.weight"),  # đầu P3 thành đầu thứ 2 (P2 đứng đầu)
    ("model.23.one2one_cv3.2.1.0.conv.weight", "model.29.one2one_cv3.3.1.0.conv.weight"),
    ("model.23.dfl.conv.weight", "model.29.dfl.conv.weight"),
])
def test_remap_to_p2(key: str, expected: str) -> None:
    assert train.remap_to_p2(key) == expected


def test_remap_bo_qua_ten_la() -> None:
    assert train.remap_to_p2("names") is None
    assert train.remap_to_p2("model.24.conv.weight") is None


def test_split_run_callbacks(tmp_path: Path) -> None:
    """Chép last.pt thành last_resume.pt sau mỗi lần lưu; dừng sau đủ số epoch."""
    from types import SimpleNamespace

    last = tmp_path / "last.pt"
    last.write_bytes(b"ckpt")
    callbacks = train.split_run_callbacks(stop_after=3)
    trainer = SimpleNamespace(last=last, epoch=1, stop=False)
    callbacks["on_model_save"](trainer)
    assert (tmp_path / "last_resume.pt").read_bytes() == b"ckpt"
    callbacks["on_fit_epoch_end"](trainer)
    assert trainer.stop is False  # mới xong 2 epoch
    trainer.epoch = 2
    callbacks["on_fit_epoch_end"](trainer)
    assert trainer.stop is True
    untouched = SimpleNamespace(last=last, epoch=99, stop=False)
    train.split_run_callbacks(stop_after=None)["on_fit_epoch_end"](untouched)
    assert untouched.stop is False
