"""Đọc tham số dòng lệnh, cho phép lấy giá trị mặc định từ file YAML."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def parse_args_with_config(parser: argparse.ArgumentParser) -> argparse.Namespace:
    """Thêm --config; giá trị trong file YAML thay cho mặc định, tham số gõ trên dòng lệnh vẫn được ưu tiên."""
    parser.add_argument("--config", type=Path, default=None, help="File YAML chứa tham số (khoá trùng tên tham số)")
    # Tắt viết tắt: nếu không, `--conf 0.1` của script bị lượt này hiểu nhầm là `--config 0.1`.
    pre_parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    pre_parser.add_argument("--config", type=Path, default=None)
    config_path = pre_parser.parse_known_args()[0].config
    if config_path is not None:
        values = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        values = {key.replace("-", "_"): value for key, value in values.items()}
        known = {action.dest for action in parser._actions}
        unknown = sorted(set(values) - known)
        if unknown:
            parser.error(f"Khoá không hợp lệ trong {config_path}: {', '.join(unknown)}")
        parser.set_defaults(**values)
        for action in parser._actions:
            if action.dest in values:
                action.required = False
    return parser.parse_args()
