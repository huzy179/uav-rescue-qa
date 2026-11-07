"""Kiểm chứng định vị khi camera nghiêng bằng nhãn track của SeaDronesSee-MOT (TECHNICAL 8.3, docs/CAI_TIEN.md).

Người trong SeaDronesSee là người bơi, gần như đứng yên trong vài giây. Nếu phép chiếu đúng, mọi khung của cùng một
track phải chiếu về gần cùng một điểm trên mặt nước, dù drone bay hay xoay. Với mỗi track: lấy các khung trong
--window-s giây đầu (mỗi --every khung một lần), chiếu tâm đáy box xuống mặt nước bằng telemetry của khung, tính độ
tản = trung vị khoảng cách tới vị trí trung vị (mét). So hai cách chiếu: giả định nhìn thẳng xuống (như mọi kết quả
trước 7/11) và theo góc gimbal trong telemetry (--use-pitch của edge/main.py). Độ tản còn gồm chuyển động thật của
người và sai số GPS, như nhau ở hai cách, nên hiệu giữa hai cách là phần do góc nghiêng.

Ghi per_track.csv, summary.csv (mỗi đoạn một dòng và một dòng "tất cả"), run_config.json.

Đồng bộ thời gian và làm mượt góc (docs/CAI_TIEN.md 3.6): --lags-s và --smooth-s cho một lưới cách chiếu theo gimbal,
đọc telemetry ở t + lag (ShiftedTelemetry) và lấy trung bình pitch, yaw trong cửa sổ (SmoothedAngles). Ghi thêm
grid.csv: mỗi ô lưới, tách phần train-* và val-* của SeaDronesSee, trung vị độ tản và tỉ lệ track tốt hơn nhìn thẳng.
Chọn ô lưới trên phần train rồi đọc kết quả trên phần val, để không chọn và chấm trên cùng dữ liệu.

    .venv/bin/python tools/eval_georef_pitch.py --root data/processed/sds_mot --output runs/georef_pitch
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

from edge.georef import Camera, ground_distance_m, pixel_to_gps
from edge.telemetry import NadirTelemetry, SampledTelemetry, ShiftedTelemetry, SmoothedAngles, TelemetrySource
from shared.provenance import write_run_config


def spread_m(points: list[tuple[float, float]]) -> float:
    """Trung vị khoảng cách tới điểm (trung vị vĩ độ, trung vị kinh độ)."""
    lat0 = statistics.median(p[0] for p in points)
    lon0 = statistics.median(p[1] for p in points)
    return statistics.median(ground_distance_m(lat0, lon0, lat, lon) for lat, lon in points)


def grid_name(lag_s: float, smooth_s: float) -> str:
    return f"lag{lag_s:+.2f}_sm{smooth_s:.2f}"


def evaluate(
    folder: Path, fov_deg: float, fov_type: str, fps: float, window_s: float, every: int, min_points: int,
    grid: list[tuple[float, float]] | None = None,
) -> list[dict]:
    info = json.loads((folder / "info.json").read_text(encoding="utf-8"))
    truth = json.loads((folder / "truth.json").read_text(encoding="utf-8"))
    tilted = SampledTelemetry.from_csv(folder / "telemetry.csv")
    sources: dict[str, TelemetrySource] = {"nadir": NadirTelemetry(tilted), "pitch": tilted}
    for lag_s, smooth_s in grid or []:
        source: TelemetrySource = ShiftedTelemetry(tilted, lag_s) if lag_s else tilted
        sources[grid_name(lag_s, smooth_s)] = SmoothedAngles(source, smooth_s) if smooth_s else source
    cam = Camera.from_fov(fov_deg, fov_type, info["width"], info["height"])
    boxes: dict[int, list[tuple[float, list[float]]]] = {}
    for key in sorted(truth, key=int):
        if int(key) % every:
            continue
        for item in truth[key]:
            boxes.setdefault(item["track_id"], []).append((int(key) / fps, item["box"]))
    rows = []
    for track_id, seen in sorted(boxes.items()):
        seen = [s for s in seen if s[0] - seen[0][0] <= window_s]
        row = {"video": folder.name, "track_id": track_id, "n_points": len(seen),
               "pitch_deg_median": statistics.median(tilted.at(t).pitch_deg for t, _ in seen)}
        ok = True
        for name, telemetry in sources.items():
            points = []
            for t, (x1, _, x2, y2) in seen:
                try:
                    points.append(pixel_to_gps((x1 + x2) / 2.0, y2, telemetry.at(t), cam))
                except ValueError:  # trên chân trời: không chiếu được
                    continue
            if len(points) < min_points:
                ok = False
                break
            row[f"spread_{name}_m"] = spread_m(points)
        if ok:
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path("data/processed/sds_mot"), help="Thư mục các đoạn đã chuyển")
    parser.add_argument("--fov-deg", type=float, default=82.0, help="Góc nhìn camera (độ), như configs/demo")
    parser.add_argument("--fov-type", choices=["horizontal", "diagonal"], default="diagonal")
    parser.add_argument("--fps", type=float, default=30.0, help="Số khung mỗi giây của đoạn")
    parser.add_argument("--window-s", type=float, default=10.0, help="Chỉ lấy các khung trong số giây đầu của mỗi track")
    parser.add_argument("--every", type=int, default=5, help="Lấy mỗi số khung này một lần")
    parser.add_argument("--min-points", type=int, default=5, help="Bỏ track có ít điểm hơn")
    parser.add_argument("--lags-s", type=float, nargs="+", default=[0.0], help="Độ trễ metadata so với ảnh cần thử (s)")
    parser.add_argument("--smooth-s", type=float, nargs="+", default=[0.0], help="Cửa sổ làm mượt góc gimbal cần thử (s), 0 = không")
    parser.add_argument("--output", type=Path, default=Path("runs/georef_pitch"))
    args = parser.parse_args()
    grid = [(lag, sm) for lag in args.lags_s for sm in args.smooth_s]
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for folder in sorted(p for p in args.root.iterdir() if (p / "truth.json").is_file()):
        rows += evaluate(folder, args.fov_deg, args.fov_type, args.fps, args.window_s, args.every, args.min_points, grid)
    with (args.output / "per_track.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = []
    for video in sorted({r["video"] for r in rows}) + ["tất cả"]:
        group = [r for r in rows if video in ("tất cả", r["video"])]
        summary.append({
            "video": video, "n_tracks": len(group),
            "pitch_deg_median": round(statistics.median(r["pitch_deg_median"] for r in group), 1),
            "spread_nadir_m_median": round(statistics.median(r["spread_nadir_m"] for r in group), 3),
            "spread_pitch_m_median": round(statistics.median(r["spread_pitch_m"] for r in group), 3),
            "share_tracks_pitch_better": round(sum(r["spread_pitch_m"] < r["spread_nadir_m"] for r in group) / len(group), 3),
        })
    with (args.output / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    grid_rows = []
    for lag_s, smooth_s in grid:
        key = f"spread_{grid_name(lag_s, smooth_s)}_m"
        for split in ("train", "val", "tất cả"):
            group = [r for r in rows if split == "tất cả" or r["video"].startswith(split + "-")]
            grid_rows.append({
                "lag_s": lag_s, "smooth_s": smooth_s, "split": split, "n_tracks": len(group),
                "spread_m_median": round(statistics.median(r[key] for r in group), 3),
                "spread_nadir_m_median": round(statistics.median(r["spread_nadir_m"] for r in group), 3),
                "share_tracks_better_than_nadir": round(sum(r[key] < r["spread_nadir_m"] for r in group) / len(group), 3),
            })
    with (args.output / "grid.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(grid_rows[0]))
        writer.writeheader()
        writer.writerows(grid_rows)
    write_run_config(args.output, "tools/eval_georef_pitch.py", None, None, vars(args))
    for s in summary:
        print(s)


if __name__ == "__main__":
    main()
