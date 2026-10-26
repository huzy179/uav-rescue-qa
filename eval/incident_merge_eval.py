"""Chấm cách trạm mặt đất gộp cảnh báo thành sự cố (ground/incidents.py) trên video thật có nhãn theo track.

Phát lại confirmations.jsonl của edge/main.py qua đúng hàm gộp của trạm mặt đất, với nhiều bán kính; mỗi cảnh báo
được ghép với người thật như eval/track_confirm_eval.py. Chỉ số theo từng cấu hình:
- số sự cố so với số cảnh báo;
- sự cố lẫn nhiều người: chứa cảnh báo của từ hai người thật trở lên (gộp nhầm);
- người bị tách: người thật có cảnh báo nằm ở từ hai sự cố trở lên (lặp còn sót);
- người bị gộp chung: người thật nằm trong ít nhất một sự cố lẫn nhiều người.
Gộp ở trạm không bỏ cảnh báo nào (khác --suppress-s ở biên), nên gộp nhầm chỉ làm hiển thị kém rõ, không làm mất người.

Ví dụ:
    .venv/bin/python eval/incident_merge_eval.py --videos val-m100-DJI_0001-v21 val-mavic-DJI_0065-v5 \\
        --mot data/processed/sds_mot --runs runs/sds --confirm geo --output runs/sds/incident_merge.csv
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from eval.track_confirm_eval import match_track, read_jsonl
from ground.incidents import MergeRule, choose_incident, merged_position
from shared.config import parse_args_with_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--videos", nargs="+", required=True, help="Tên thư mục video trong --mot và --runs")
    parser.add_argument("--mot", type=Path, required=True, help="Thư mục của tools/convert_seadronessee_mot.py")
    parser.add_argument("--runs", type=Path, required=True, help="Thư mục kết quả, <runs>/<video>/<confirm>/confirmations.jsonl")
    parser.add_argument("--confirm", default="geo", help="Thư mục con của lần chạy cần chấm")
    parser.add_argument("--radius", type=float, nargs="+", default=[3.0, 5.0, 10.0], help="Các bán kính gộp cố định (m)")
    parser.add_argument("--position-error-m", type=float, default=5.0,
                        help="Sai số gửi kèm cảnh báo (hằng số của edge/main.py), để chấm thêm luật bán kính theo sai số")
    parser.add_argument("--window-s", type=float, default=300.0, help="Cửa sổ thời gian gộp (s)")
    parser.add_argument("--iou", type=float, default=0.3, help="IoU tối thiểu để ghép cảnh báo với người thật")
    parser.add_argument("--output", type=Path, required=True, help="File CSV kết quả")
    return parse_args_with_config(parser)


def assign_incidents(confirmations: list[dict[str, Any]], error_m: float, rule: MergeRule) -> list[int]:
    """Sự cố của từng cảnh báo (theo thứ tự thời gian), gộp như ground/app.py."""
    incidents: list[dict[str, Any]] = []
    member = []
    for c in confirmations:
        i = choose_incident(c["lat"], c["lon"], error_m, c["t"], incidents, rule)
        if i is None:
            i = len(incidents)
            incidents.append({"incident_id": i, "lat": c["lat"], "lon": c["lon"], "position_error_m": error_m,
                              "first_t": c["t"], "last_t": c["t"], "n_alerts": 1})
        else:
            inc = incidents[i]
            inc["lat"], inc["lon"], inc["position_error_m"] = merged_position(inc, c["lat"], c["lon"], error_m)
            inc["n_alerts"] += 1
            inc["last_t"] = max(inc["last_t"], c["t"])
        member.append(i)
    return member


def purity(member: list[int], people: list[int | None]) -> dict[str, int]:
    """Đếm sự cố lẫn nhiều người, người bị tách, người bị gộp chung; cảnh báo nhầm (None) không tính."""
    people_in: dict[int, set[int]] = defaultdict(set)
    incidents_of: dict[int, set[int]] = defaultdict(set)
    for inc, tid in zip(member, people):
        if tid is not None:
            people_in[inc].add(tid)
            incidents_of[tid].add(inc)
    mixed = {i for i, p in people_in.items() if len(p) > 1}
    return {
        "incidents": len(set(member)),
        "people": len(incidents_of),
        "mixed_incidents": len(mixed),
        "people_split": sum(len(s) > 1 for s in incidents_of.values()),
        "people_merged": sum(bool(s & mixed) for s in incidents_of.values()),
    }


def main() -> None:
    """Chấm từng video ở từng cấu hình bán kính, ghi CSV và in bảng."""
    args = parse_args()
    rows = []
    for video in args.videos:
        truth = {int(k): v for k, v in json.loads((args.mot / video / "truth.json").read_text(encoding="utf-8")).items()}
        confs = sorted(read_jsonl(args.runs / video / args.confirm / "confirmations.jsonl"), key=lambda c: c["t"])
        people = [match_track(tuple(c["box_px"]), truth.get(c["frame_id"], []), args.iou) for c in confs]
        rules = [(f"cố định {r:g} m", MergeRule(r, 0.0, args.window_s)) for r in args.radius]
        rules.append((f"tổng sai số ({2 * args.position_error_m:g} m)", MergeRule(0.0, 1.0, args.window_s)))
        for name, rule in rules:
            member = assign_incidents(confs, args.position_error_m, rule)
            rows.append({"video": video, "rule": name, "alerts": len(confs), **purity(member, people)})
    table = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
