"""Chỉ số RQ3 từ log của edge/main.py và nhãn theo thời gian (TECHNICAL mục 15.4).

Ghép cảnh báo với người thật theo khoảng cách mặt đất tại thời điểm cảnh báo:
- cảnh báo không gần người nào (> r_eval) là báo động giả;
- cảnh báo gần từ hai người trở lên là gộp nhầm;
- người nhận từ hai cảnh báo trở lên (tính theo người gần nhất của mỗi cảnh báo) là tách nhầm;
- người không có cảnh báo nào trong [t_in, t_out + tail] là bỏ sót hoàn toàn;
- sai số vị trí lấy ở cảnh báo đầu tiên của mỗi người, so với bán kính sai số 1σ cảnh báo đó tự báo (within_reported_radius) và
  bán kính 95 % = R95_FACTOR × 1σ (within_reported_radius_95).

Ví dụ:
    .venv/bin/python eval/rq3_metrics.py --run runs/rq3/demo/geo --truth runs/rq3/demo/ground_truth.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from edge.georef import R95_FACTOR, ground_distance_m
from shared.provenance import write_run_config
from shared.schema import GROUP_RADIUS_M, Alert
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
    group_errors: list[int] = []  # số người ước tính − số người thật trong GROUP_RADIUS_M, mỗi cảnh báo đúng
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
        here = people[matched[0][1]].at(alert.t)
        true_group = sum(1 for p in people.values() if ground_distance_m(*here, *p.at(alert.t)) <= GROUP_RADIUS_M)
        group_errors.append(alert.group_size - true_group)

    per_person = []
    for pid, (t_in, t_out) in sorted(spans.items()):
        in_window = [a for a in alerts_of[pid] if a.t <= t_out + tail_s]
        first = min((a.t for a in in_window), default=None)
        # Cảnh báo đầu tiên (gần nhất nếu nhiều cảnh báo cùng lúc): sai số thật và bán kính sai số hệ thống tự báo.
        best = None if first is None else min(
            ((ground_distance_m(a.lat, a.lon, *people[pid].at(a.t)), a.position_error_m) for a in in_window if a.t == first)
        )
        per_person.append(
            {
                "person_id": pid, "t_in": t_in, "t_out": t_out, "n_alerts": len(alerts_of[pid]),
                "time_to_alert_s": None if first is None else first - t_in,
                "position_error_m": None if best is None else best[0],
                "reported_error_m": None if best is None else best[1],
            }
        )

    acked = {}
    for record in sends:
        if record["kind"] == "coords" and record["ok"]:
            acked.setdefault(record["msg_id"].rsplit(":", 1)[0], record["t"])
    delays = [acked[a.alert_id] - a.t for a in alerts if a.alert_id in acked]
    times = [p["time_to_alert_s"] for p in per_person if p["time_to_alert_s"] is not None]
    found = [p for p in per_person if p["position_error_m"] is not None]
    errors = [p["position_error_m"] for p in found]
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
        "position_error_m_max": max(errors, default=None),
        # Tỉ lệ người (đã được cảnh báo) nằm trong bán kính sai số mà cảnh báo đầu tiên tự báo (vòng tròn trên bản đồ).
        "within_reported_radius": sum(p["position_error_m"] <= p["reported_error_m"] for p in found) / len(found) if found else None,
        "within_reported_radius_95": (
            sum(p["position_error_m"] <= R95_FACTOR * p["reported_error_m"] for p in found) / len(found) if found else None
        ),
        # Bán kính vùng tìm 95% trên bản đồ (trung vị qua người đã được cảnh báo): cái giá của vùng chứa đủ người.
        "search_radius_95_m_median": _median([R95_FACTOR * p["reported_error_m"] for p in found]),
        # Ước tính số người quanh cảnh báo (group_size) so với số người thật trong GROUP_RADIUS_M quanh người được báo.
        "group_count_exact": sum(e == 0 for e in group_errors) / len(group_errors) if group_errors else None,
        "group_count_error_mean": sum(group_errors) / len(group_errors) if group_errors else None,
        "group_count_abs_error_mean": sum(abs(e) for e in group_errors) / len(group_errors) if group_errors else None,
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


def timing_metrics(records: list[dict[str, Any]]) -> dict[str, float | int | None]:
    """Chi phí tính toán từ timings.jsonl: số khung đã chạy detector, và trung vị độ trễ giả lập của thiết bị
    (--device-profile; None khi không giả lập thiết bị)."""
    latency = sorted(r["sim_latency_ms"] for r in records if "sim_latency_ms" in r)
    median = None
    if latency:
        mid = len(latency) // 2
        median = latency[mid] if len(latency) % 2 else (latency[mid - 1] + latency[mid]) / 2
    return {"frames_processed": len(records), "sim_latency_ms_median": median}


def main() -> None:
    """Đọc log và nhãn, tính chỉ số, ghi rq3_metrics.json và rq3_per_person.json."""
    args = parse_args()
    output = args.output or args.run / "rq3_eval"
    output.mkdir(parents=True, exist_ok=True)
    alerts = [Alert.model_validate(row) for row in read_jsonl(args.run / "alerts.jsonl")]
    sends = read_jsonl(args.run / "alerts_sent.jsonl")
    truth = json.loads(args.truth.read_text(encoding="utf-8"))
    summary, per_person = compute_metrics(alerts, sends, truth, args.r_eval_m, args.tail_s)
    # Chi phí tính toán: số khung đã chạy detector (khác nhau khi tần số xử lý đổi theo độ cao, --min-views).
    timings = args.run / "timings.jsonl"
    if timings.exists():
        summary.update(timing_metrics(read_jsonl(timings)))
    else:
        summary.update({"frames_processed": None, "sim_latency_ms_median": None})
    (output / "rq3_metrics.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (output / "rq3_per_person.json").write_text(json.dumps(per_person, indent=2, ensure_ascii=False), encoding="utf-8")
    write_run_config(output, Path(__file__).name, None, None, vars(args))
    for key, value in summary.items():
        print(f"{key:28s} {value if not isinstance(value, float) else round(value, 3)}")


if __name__ == "__main__":
    main()
