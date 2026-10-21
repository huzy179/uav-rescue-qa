"""Chỉ số RQ3 từ log của edge/main.py và nhãn theo thời gian (TECHNICAL mục 15.4).

Ghép cảnh báo với người thật theo khoảng cách mặt đất tại thời điểm cảnh báo:
- cảnh báo không gần người nào (> r_eval) là báo động giả;
- cảnh báo gần từ hai người trở lên là gộp nhầm;
- người nhận từ hai cảnh báo trở lên (tính theo người gần nhất của mỗi cảnh báo) là tách nhầm;
- người không có cảnh báo nào trong [t_in, t_out + tail] là bỏ sót hoàn toàn.

Ví dụ:
    .venv/bin/python eval/rq3_metrics.py --run runs/rq3/demo/geo --truth runs/rq3/demo/ground_truth.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from edge.georef import ground_distance_m
from shared.provenance import write_run_config
from shared.schema import Alert
from sim.scenario import Person


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True, help="Thư mục log của edge/main.py (alerts.jsonl, alerts_sent.jsonl)")
    parser.add_argument("--truth", type=Path, required=True, help="ground_truth.json (sim/make_rq3.py)")
    parser.add_argument("--r-eval-m", type=float, default=10.0, help="Cảnh báo cách người thật ≤ r_eval (m) thì coi là đúng người đó")
    parser.add_argument("--tail-s", type=float, default=10.0, help="Cảnh báo tới muộn tối đa sau khi người rời khung (giây)")
    parser.add_argument("--output", type=Path, default=None, help="Nơi ghi kết quả (mặc định: <run>/rq3_eval; không ghi thẳng vào --run để khỏi đè run_config.json của pipeline)")
    return parser.parse_args()


def presence(truth: dict[str, Any]) -> dict[int, tuple[float, float]]:
    """(t_in, t_out) của từng người: thời điểm khung đầu và cuối người đó có trong khung."""
    spans: dict[int, tuple[float, float]] = {}
    for frame in truth["frames"]:
        for item in frame["visible"]:
            pid = item["person_id"]
            t_in, _ = spans.get(pid, (frame["t"], frame["t"]))
            spans[pid] = (t_in, frame["t"])
    return spans


def compute_metrics(
    alerts: list[Alert], sends: list[dict[str, Any]], truth: dict[str, Any], r_eval_m: float, tail_s: float
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Trả về (chỉ số tổng, bảng theo người). Chỉ tính người có xuất hiện trong ít nhất một khung."""
    people = {p["person_id"]: Person(**p) for p in truth["people"]}
    spans = presence(truth)
    alerts_of: dict[int, list[Alert]] = {pid: [] for pid in spans}
    false_alarms = merges = 0
    for alert in alerts:
        near = sorted(
            (ground_distance_m(alert.lat, alert.lon, *people[pid].at(alert.t)), pid) for pid in spans
        )
        matched = [(d, pid) for d, pid in near if d <= r_eval_m]
        if not matched:
            false_alarms += 1
            continue
        merges += len(matched) >= 2
        alerts_of[matched[0][1]].append(alert)

    per_person = []
    for pid, (t_in, t_out) in sorted(spans.items()):
        in_window = [a for a in alerts_of[pid] if a.t <= t_out + tail_s]
        first = min((a.t for a in in_window), default=None)
        per_person.append(
            {
                "person_id": pid, "t_in": t_in, "t_out": t_out, "n_alerts": len(alerts_of[pid]),
                "time_to_alert_s": None if first is None else first - t_in,
                "position_error_m": None if first is None else min(
                    ground_distance_m(a.lat, a.lon, *people[pid].at(a.t)) for a in in_window if a.t == first
                ),
            }
        )

    acked = {}
    for record in sends:
        if record["kind"] == "coords" and record["ok"]:
            acked.setdefault(record["msg_id"].rsplit(":", 1)[0], record["t"])
    delays = [acked[a.alert_id] - a.t for a in alerts if a.alert_id in acked]
    times = [p["time_to_alert_s"] for p in per_person if p["time_to_alert_s"] is not None]
    errors = [p["position_error_m"] for p in per_person if p["position_error_m"] is not None]
    n_people = len(per_person)
    summary = {
        "n_people": n_people,
        "n_alerts": len(alerts),
        "false_alarms": false_alarms,
        "false_alarms_per_min": false_alarms / (truth["duration_s"] / 60.0),
        "missed_rate": sum(p["time_to_alert_s"] is None for p in per_person) / n_people if n_people else None,
        "merge_errors": merges,
        "split_errors": sum(p["n_alerts"] >= 2 for p in per_person),
        "time_to_alert_s_median": _median(times),
        "time_to_alert_s_max": max(times, default=None),
        "position_error_m_median": _median(errors),
        "delivery_delay_s_median": _median(delays),
        "delivery_delay_s_max": max(delays, default=None),
        "lost_rate": (len(alerts) - len(delays)) / len(alerts) if alerts else None,
        "kb_per_alert": sum(r["bytes"] for r in sends) / 1024 / len(alerts) if alerts else None,
    }
    return summary, per_person


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    """Đọc log và nhãn, tính chỉ số, ghi rq3_metrics.json và rq3_per_person.json."""
    args = parse_args()
    output = args.output or args.run / "rq3_eval"
    output.mkdir(parents=True, exist_ok=True)
    alerts = [Alert.model_validate(row) for row in read_jsonl(args.run / "alerts.jsonl")]
    sends = read_jsonl(args.run / "alerts_sent.jsonl")
    truth = json.loads(args.truth.read_text(encoding="utf-8"))
    summary, per_person = compute_metrics(alerts, sends, truth, args.r_eval_m, args.tail_s)
    (output / "rq3_metrics.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (output / "rq3_per_person.json").write_text(json.dumps(per_person, indent=2, ensure_ascii=False), encoding="utf-8")
    write_run_config(output, Path(__file__).name, None, None, vars(args))
    for key, value in summary.items():
        print(f"{key:28s} {value if not isinstance(value, float) else round(value, 3)}")


if __name__ == "__main__":
    main()
