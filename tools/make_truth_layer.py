"""Lớp đáp án cho màn hình điều phối: người thật ở đâu, lúc nào drone thấy họ (TECHNICAL mục 12.6).

Hai nguồn:
- --rq3: ground_truth.json của chuyến bay mô phỏng (sim/make_rq3.py): vị trí thật của từng người.
- --sds: một đoạn SeaDronesSee-MOT đã chuyển (truth.json: box và track_id theo khung, telemetry.csv); vị trí người là
  tâm đáy box chiếu xuống mặt đất bằng chính telemetry đó (edge.georef), nên có cùng sai số GPS với pipeline: lớp
  đáp án cho biết người nào được cảnh báo, không đo sai số định vị.

Ghi một JSON: {source, note, people: [{id, t_in, t_out, track: [[t, lat, lon], ...]}]}, track lấy mẫu mỗi --step-s
giây và luôn có điểm đầu, cuối. Chỉ giữ người có mặt trong khung ít nhất --min-span-s giây: người lướt qua mép khung
hoặc track đứt vài khung thì không hệ thống nào xác nhận được (cần thấy N = 3 lần), như điều kiện "đủ điều kiện" của
eval/track_confirm_eval.py. Trạm mặt đất nhận qua POST /api/truth (scripts/demo_bao_ve.sh tự gửi).

Ví dụ:
    .venv/bin/python tools/make_truth_layer.py --rq3 runs/edge/demo_cache/hotay_quet/ground_truth.json \
        --output runs/edge/demo_cache/hotay_quet/truth_layer.json
    .venv/bin/python tools/make_truth_layer.py --sds data/processed/sds_mot/val-m100-DJI_0001-v21 \
        --config configs/demo/sds_v21_goc.yaml --output runs/edge/demo_cache/sds_v21_goc/truth_layer.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from edge.georef import Camera, pixel_to_gps
from edge.telemetry import SampledTelemetry
from sim.scenario import Person


def sample_times(times: list[float], step_s: float) -> list[float]:
    """Các thời điểm trong `times` (tăng dần) cách nhau ít nhất step_s, luôn giữ điểm đầu và cuối."""
    kept = [times[0]]
    for t in times[1:]:
        if t - kept[-1] >= step_s - 1e-9:
            kept.append(t)
    if kept[-1] != times[-1]:
        kept.append(times[-1])
    return kept


def from_rq3(truth: dict[str, Any], step_s: float) -> list[dict[str, Any]]:
    """Người có xuất hiện trong ít nhất một khung; vị trí theo Person.at (đứng yên hoặc trôi)."""
    people = {p["person_id"]: Person(**p) for p in truth["people"]}
    seen: dict[int, list[float]] = {}
    for frame in truth["frames"]:
        for item in frame["visible"]:
            seen.setdefault(item["person_id"], []).append(frame["t"])
    out = []
    for pid, times in sorted(seen.items()):
        track = [[round(t, 3), *people[pid].at(t)] for t in sample_times(times, step_s)]
        out.append({"id": pid, "t_in": times[0], "t_out": times[-1], "track": track})
    return out


def from_sds(folder: Path, cam_cfg: dict[str, Any], step_s: float) -> list[dict[str, Any]]:
    """Mỗi track_id là một người; vị trí là tâm đáy box chiếu xuống mặt đất theo telemetry của khung."""
    info = json.loads((folder / "info.json").read_text(encoding="utf-8"))
    truth = json.loads((folder / "truth.json").read_text(encoding="utf-8"))
    telemetry = SampledTelemetry.from_csv(folder / "telemetry.csv")
    cam = Camera.from_fov(cam_cfg.get("fov_deg", 82.0), cam_cfg.get("fov_type", "diagonal"), info["width"], info["height"])
    fps = float(cam_cfg.get("source_fps", 30.0))
    points: dict[int, list[tuple[float, float, float]]] = {}
    for key in sorted(truth, key=int):
        t = int(key) / fps
        tel = telemetry.at(t)
        for item in truth[key]:
            x1, _, x2, y2 = item["box"]
            points.setdefault(item["track_id"], []).append((t, *pixel_to_gps((x1 + x2) / 2.0, y2, tel, cam)))
    out = []
    for track_id, rows in sorted(points.items()):
        keep = set(sample_times([r[0] for r in rows], step_s))
        out.append({"id": track_id, "t_in": rows[0][0], "t_out": rows[-1][0],
                    "track": [[round(t, 3), lat, lon] for t, lat, lon in rows if t in keep]})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--rq3", type=Path, help="ground_truth.json của sim/make_rq3.py")
    source.add_argument("--sds", type=Path, help="Thư mục một đoạn SeaDronesSee-MOT đã chuyển (truth.json, telemetry.csv, info.json)")
    parser.add_argument("--config", type=Path, default=None, help="Với --sds: cấu hình demo để lấy fov_deg, fov_type, source_fps")
    parser.add_argument("--step-s", type=float, default=1.0, help="Lấy mẫu đường đi của mỗi người (giây)")
    parser.add_argument("--min-span-s", type=float, default=1.0, help="Bỏ người có mặt trong khung ít hơn số giây này")
    parser.add_argument("--output", type=Path, required=True, help="File JSON ghi ra")
    args = parser.parse_args()
    if args.rq3:
        people = from_rq3(json.loads(args.rq3.read_text(encoding="utf-8")), args.step_s)
        layer = {"source": str(args.rq3), "note": "Mô phỏng: vị trí thật của người trong kịch bản", "people": people}
    else:
        cfg = yaml.safe_load(args.config.read_text(encoding="utf-8")) if args.config else {}
        people = from_sds(args.sds, cfg, args.step_s)
        layer = {"source": str(args.sds), "note": "Nhãn SeaDronesSee chiếu xuống mặt đất bằng telemetry của drone", "people": people}
    n_all = len(layer["people"])
    layer["people"] = [p for p in layer["people"] if p["t_out"] - p["t_in"] >= args.min_span_s]
    layer["note"] += f"; chỉ người có mặt ít nhất {args.min_span_s:g} s ({len(layer['people'])}/{n_all})"
    people = layer["people"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(layer, ensure_ascii=False), encoding="utf-8")
    print(f"{len(people)} người. Ghi tại: {args.output}")


if __name__ == "__main__":
    main()
