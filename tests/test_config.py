"""Kiểm tra đọc tham số kèm file YAML (shared/config.py)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

from shared.config import parse_args_with_config


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=640)
    return parser


def test_conf_khong_bi_hieu_nham_la_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["prog", "--conf", "0.001"])
    args = parse_args_with_config(make_parser())
    assert args.conf == 0.001
    assert args.config is None


def test_yaml_lam_mac_dinh_va_dong_lenh_duoc_uu_tien(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "c.yaml"
    config.write_text("conf: 0.1\nimgsz: 1280\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["prog", "--config", str(config), "--conf", "0.001"])
    args = parse_args_with_config(make_parser())
    assert (args.conf, args.imgsz) == (0.001, 1280)
