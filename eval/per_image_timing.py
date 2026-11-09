"""Tóm tắt thời gian mỗi ảnh (per_image.csv) của nhiều lần chạy: trung vị, trung bình, p95 của từng cột thời gian.

Dùng cho docs/results/gpu_resize.md. Thời gian đo trên máy cá nhân chỉ để so sánh tương đối (CLAUDE.md).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from shared.config import parse_args_with_config

COLUMNS = ("tile_ms", "infer_ms")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, nargs="+", required=True, help="Thư mục kết quả có per_image.csv")
    parser.add_argument("--output", type=Path, required=True, help="File CSV tóm tắt")
    return parser


def summarize(per_image: pd.DataFrame) -> dict[str, float]:
    """Trung vị, trung bình, p95 của các cột thời gian có trong bảng (làm tròn 2 chữ số như per_image.csv)."""
    row: dict[str, float] = {"n_images": float(len(per_image))}
    for col in COLUMNS:
        if col in per_image:
            values = per_image[col].dropna()
            row[f"{col}_median"] = round(float(values.median()), 2)
            row[f"{col}_mean"] = round(float(values.mean()), 2)
            row[f"{col}_p95"] = round(float(values.quantile(0.95)), 2)
    return row


def main() -> None:
    args = parse_args_with_config(build_parser())
    rows = [{"run": run.name, **summarize(pd.read_csv(run / "per_image.csv"))} for run in args.runs]
    table = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
