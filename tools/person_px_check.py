"""So cỡ người trong nhãn SeaDronesSee-MOT với cỡ dự kiến từ độ cao bay (docs/results/person_px_check.md).

Thu nhỏ theo độ cao (--target-person-px) và mô phỏng câu hỏi 3 ước lượng người rộng --person-m mét, camera --fov-deg
góc chéo: px_dự_kiến = person_m · f / h. Script này đo, ở các khung camera gần nhìn thẳng xuống (góc gimbal ≤ --max-pitch),
tích "cạnh ngắn box nhãn × độ cao" của từng người (hằng số nếu mô hình đúng) và chia cho person_m · f để ra tỉ số
nhãn / dự kiến. Tỉ số khác 1 có hai nguồn không tách được bằng dữ liệu này: cỡ người thật khác person_m (box người bơi
gồm cả thân, tay, bọt nước) và góc nhìn thật của camera khác fov_deg.

Ghi CSV mỗi đoạn một dòng: phần dữ liệu (train/val), loại drone, số box, độ cao trung vị, góc gimbal trung vị, tích
trung vị và tỉ số; và một dòng cho mọi khung (không lọc góc) để thấy ảnh hưởng của camera nghiêng.

Ví dụ:
    .venv/bin/python tools/person_px_check.py --mot data/processed/sds_mot --output runs/stats/person_px_check.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

from edge.georef import Camera
from shared.config import parse_args_with_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mot", type=Path, required=True, help="Thư mục các đoạn SDS-MOT đã chuyển")
    parser.add_argument("--fov-deg", type=float, default=82.0, help="Góc nhìn chéo giả định (độ)")
    parser.add_argument("--person-m", type=float, default=0.5, help="Cỡ người giả định nhìn từ trên xuống (m)")
    parser.add_argument("--max-pitch", type=float, default=-80.0, help="Chỉ lấy khung có góc gimbal ≤ giá trị này (−90 là nhìn thẳng)")
    parser.add_argument("--output", type=Path, required=True, help="File CSV kết quả")
    return parse_args_with_config(parser)


def sequence_rows(folder: Path, fov_deg: float, person_m: float, max_pitch: float) -> list[dict[str, object]]:
    """Hai dòng cho một đoạn: mọi khung, và chỉ khung gần nhìn thẳng xuống."""
    info = json.loads((folder / "info.json").read_text(encoding="utf-8"))
    truth = json.loads((folder / "truth.json").read_text(encoding="utf-8"))
    tel = pd.read_csv(folder / "telemetry.csv")
    cam = Camera.from_fov(fov_deg, "diagonal", info["width"], info["height"])
    times = tel["t"].to_numpy()
    records = []
    for key, items in truth.items():
        i = min(int(np.searchsorted(times, int(key) / 30.0)), len(tel) - 1)
        alt, pitch = float(tel["alt_agl_m"].iloc[i]), float(tel["pitch_deg"].iloc[i])
        for item in items:
            x1, y1, x2, y2 = item["box"]
            records.append((alt, pitch, min(x2 - x1, y2 - y1) * alt))
    split, drone = folder.name.split("-")[0], folder.name.split("-")[1]
    rows = []
    for subset, keep in (("mọi khung", lambda p: True), (f"góc ≤ {max_pitch:g}°", lambda p: p <= max_pitch)):
        sel = [r for r in records if keep(r[1])]
        if not sel:
            continue
        k = float(np.median([r[2] for r in sel]))
        rows.append({"sequence": folder.name, "split": split, "drone": drone, "frames": subset, "n_boxes": len(sel),
                     "alt_median_m": round(float(np.median([r[0] for r in sel])), 2),
                     "pitch_median_deg": round(float(np.median([r[1] for r in sel])), 1),
                     "short_px_x_alt_median": round(k, 1), "ratio_label_to_expected": round(k / (person_m * cam.f_px), 3)})
    return rows


def main() -> None:
    """Đo mọi đoạn, ghi CSV, in bảng."""
    args = parse_args()
    rows = []
    for folder in sorted(p for p in args.mot.iterdir() if (p / "truth.json").exists()):
        rows += sequence_rows(folder, args.fov_deg, args.person_m, args.max_pitch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"Lưu tại: {args.output}")


if __name__ == "__main__":
    main()
