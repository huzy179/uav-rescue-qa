"""Tính GSD và kích thước người (pixel) theo độ cao bay của UAV."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

PERSON_WIDTH_M = 0.5  # bề ngang người nhìn từ trên xuống
HEAD_WIDTH_M = 0.2  # đầu người khi thân đã ngập dưới nước


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fov-deg", type=float, default=82.0, help="Góc nhìn của camera (độ); mặc định: camera góc rộng Matrice 4T")
    parser.add_argument(
        "--fov-type",
        choices=["horizontal", "diagonal"],
        default="diagonal",
        help="--fov-deg là góc ngang hay góc chéo (DJI ghi thông số theo góc chéo)",
    )
    parser.add_argument("--width-px", type=int, default=3840, help="Bề rộng ảnh gốc (px)")
    parser.add_argument("--height-px", type=int, default=2160, help="Chiều cao ảnh gốc (px), dùng khi FOV là góc chéo")
    parser.add_argument(
        "--tilt-deg", type=float, default=0.0, help="Góc nghiêng camera so với phương thẳng đứng (0 = chụp thẳng xuống)"
    )
    parser.add_argument(
        "--altitudes", type=float, nargs="+", default=[30, 50, 80, 100], help="Các độ cao bay (m)"
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Bề rộng ảnh sau khi thu nhỏ để suy luận (px)")
    parser.add_argument("--output", type=Path, default=Path("runs/gsd/gsd_table.csv"), help="File CSV kết quả")
    return parser.parse_args()


def horizontal_fov_deg(fov_deg: float, fov_type: str, width_px: int, height_px: int) -> float:
    """Quy đổi góc nhìn về góc ngang; với góc chéo dùng tỉ lệ bề rộng trên đường chéo cảm biến."""
    if fov_type == "horizontal":
        return fov_deg
    diagonal_px = math.hypot(width_px, height_px)
    return math.degrees(2.0 * math.atan(math.tan(math.radians(fov_deg) / 2.0) * width_px / diagonal_px))


def gsd_table(hfov_deg: float, width_px: int, altitudes: list[float], imgsz: int, tilt_deg: float = 0.0) -> pd.DataFrame:
    """Lập bảng bề rộng vùng chụp, GSD và kích thước người/đầu người theo từng độ cao.

    Khi camera nghiêng, các giá trị được tính tại tâm ảnh với khoảng cách xiên h / cos(góc nghiêng).
    """
    scale = imgsz / width_px
    rows = []
    for altitude in altitudes:
        distance_m = altitude / math.cos(math.radians(tilt_deg))
        footprint_m = 2.0 * distance_m * math.tan(math.radians(hfov_deg) / 2.0)
        gsd_m = footprint_m / width_px
        person_px = PERSON_WIDTH_M / gsd_m
        head_px = HEAD_WIDTH_M / gsd_m
        rows.append(
            {
                "altitude_m": altitude,
                "footprint_w_m": round(footprint_m, 2),
                "gsd_cm_per_px": round(gsd_m * 100.0, 3),
                "person_px": round(person_px, 2),
                "head_px": round(head_px, 2),
                f"person_px_at_{imgsz}": round(person_px * scale, 2),
                f"head_px_at_{imgsz}": round(head_px * scale, 2),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    """In bảng GSD, lưu CSV và file JSON tham số bên cạnh."""
    args = parse_args()
    hfov_deg = horizontal_fov_deg(args.fov_deg, args.fov_type, args.width_px, args.height_px)
    table = gsd_table(hfov_deg, args.width_px, args.altitudes, args.imgsz, args.tilt_deg)
    print(
        f"FOV ngang = {hfov_deg:.2f}°, nghiêng {args.tilt_deg}°, ảnh gốc rộng {args.width_px} px, thu về imgsz = {args.imgsz} "
        f"(tỉ lệ {args.imgsz / args.width_px:.3f}); người = {PERSON_WIDTH_M} m, đầu = {HEAD_WIDTH_M} m"
    )
    print(table.to_string(index=False))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False)
    params = {
        "script": Path(__file__).name,
        "command": " ".join(sys.argv),
        "args": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        "horizontal_fov_deg": round(hfov_deg, 4),
        "person_width_m": PERSON_WIDTH_M,
        "head_width_m": HEAD_WIDTH_M,
    }
    args.output.with_suffix(".json").write_text(json.dumps(params, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nĐã lưu: {args.output}")


if __name__ == "__main__":
    main()
