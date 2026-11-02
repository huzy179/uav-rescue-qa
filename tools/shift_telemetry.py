"""Dời telemetry CSV một khoảng cố định về phía Bắc, Đông (mét), giả lập drone thứ hai có GPS lệch độc lập.

Dùng cho demo nhiều drone (scripts/demo_multi.sh): hai drone phát lại cùng một đoạn video nhưng GPS mỗi chiếc lệch
một kiểu, trạm mặt đất phải gộp cảnh báo của cả hai thành một sự cố cho mỗi người (ground/incidents.py). Chỉ để minh
hoạ: hai drone thật nhìn cùng người từ hai góc, không phải cùng một khung hình.

Ví dụ:
    .venv/bin/python tools/shift_telemetry.py --src telemetry.csv --dst telemetry_uav2.csv --north-m 2 --east-m 3
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from edge.georef import offset_gps
from shared.config import parse_args_with_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", type=Path, required=True, help="Telemetry CSV gốc (cột t, lat, lon, ...)")
    parser.add_argument("--dst", type=Path, required=True, help="File CSV ghi ra")
    parser.add_argument("--north-m", type=float, default=0.0, help="Dời về phía Bắc (m)")
    parser.add_argument("--east-m", type=float, default=0.0, help="Dời về phía Đông (m)")
    return parse_args_with_config(parser)


def shift_rows(rows: list[dict[str, str]], north_m: float, east_m: float) -> list[dict[str, str]]:
    """Dời lat, lon của mọi dòng; các cột khác giữ nguyên."""
    out = []
    for row in rows:
        lat, lon = offset_gps(float(row["lat"]), float(row["lon"]), north_m, east_m)
        out.append({**row, "lat": f"{lat:.9f}", "lon": f"{lon:.9f}"})
    return out


def main() -> None:
    """Đọc, dời, ghi."""
    args = parse_args()
    with args.src.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames or [], list(reader)
    args.dst.parent.mkdir(parents=True, exist_ok=True)
    with args.dst.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(shift_rows(rows, args.north_m, args.east_m))
    print(f"Đã dời {len(rows)} dòng {args.north_m:g} m Bắc, {args.east_m:g} m Đông -> {args.dst}")


if __name__ == "__main__":
    main()
