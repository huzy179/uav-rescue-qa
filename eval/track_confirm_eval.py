"""Chấm khối xác nhận trên video thật có nhãn theo track (SeaDronesSee-MOT), trong không gian ảnh.

Khác eval/rq3_metrics.py (mô phỏng, chấm theo toạ độ mặt đất của người giả lập): ở đây người thật chỉ có box và
track_id trên từng khung. Mỗi cảnh báo (dòng của confirmations.jsonl) được ghép với người thật ở chính khung của nó:
IoU ≥ --iou, hoặc tâm box cảnh báo nằm trong box người thật (box người nhỏ, lệch vài pixel là IoU tụt mạnh).

Chỉ số:
- người đủ điều kiện: thấy trong ít nhất --min-frames khung đã xử lý (ít hơn thì không chiến lược nào xác nhận nổi);
- tỉ lệ người được cảnh báo: người đủ điều kiện có ít nhất một cảnh báo ghép được;
- cảnh báo nhầm: không ghép được người thật nào;
- cảnh báo lặp: cảnh báo thứ hai trở đi cho cùng một người (tách nhầm);
- thời gian tới cảnh báo: từ khung đầu tiên người xuất hiện (trong các khung đã xử lý) tới cảnh báo đầu tiên.

Ví dụ:
    .venv/bin/python eval/track_confirm_eval.py --run runs/sds/<video>/geo --truth data/processed/sds_mot/<video>/truth.json
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from shared.config import parse_args_with_config

Box = tuple[float, float, float, float]


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, required=True, help="Thư mục log của edge/main.py (confirmations.jsonl, timings.jsonl)")
    parser.add_argument("--truth", type=Path, required=True, help="truth.json của tools/convert_seadronessee_mot.py")
    parser.add_argument("--iou", type=float, default=0.3, help="IoU tối thiểu để ghép cảnh báo với người thật")
    parser.add_argument("--min-frames", type=int, default=3, help="Người phải thấy trong ít nhất số khung đã xử lý này mới được tính")
    parser.add_argument("--output", type=Path, default=None, help="File JSON kết quả (mặc định <run>/track_eval.json)")
    return parse_args_with_config(parser)


def iou(a: Box, b: Box) -> float:
    w = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = w * h
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def match_track(box: Box, people: list[dict[str, Any]], min_iou: float) -> int | None:
    """track_id của người thật khớp nhất với box cảnh báo trong cùng khung; None nếu không ai khớp."""
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    best, best_score = None, 0.0
    for person in people:
        b = person["box"]
        score = iou(box, b)
        inside = b[0] <= cx <= b[2] and b[1] <= cy <= b[3]
        if (score >= min_iou or inside) and (score > best_score or best is None):
            best, best_score = person["track_id"], score
    return best


def score(
    confirmations: list[dict[str, Any]], truth: dict[int, list[dict[str, Any]]], processed: list[int],
    times: dict[int, float], min_iou: float, min_frames: int,
) -> dict[str, Any]:
    """Tính các chỉ số từ cảnh báo, nhãn theo khung, các khung đã xử lý và thời điểm của chúng."""
    seen: dict[int, list[int]] = {}
    for frame in processed:
        for person in truth.get(frame, []):
            seen.setdefault(person["track_id"], []).append(frame)
    eligible = {tid for tid, frames in seen.items() if len(frames) >= min_frames}

    alerted: dict[int, float] = {}
    false_alerts = duplicates = 0
    for conf in sorted(confirmations, key=lambda c: c["t"]):
        tid = match_track(tuple(conf["box_px"]), truth.get(conf["frame_id"], []), min_iou)
        if tid is None:
            false_alerts += 1
        elif tid in alerted:
            duplicates += 1
        else:
            alerted[tid] = conf["t"]
    delays = [alerted[tid] - times[min(seen[tid])] for tid in eligible if tid in alerted]
    return {
        "processed_frames": len(processed),
        "people_seen": len(seen),
        "people_eligible": len(eligible),
        "people_alerted": len(eligible & set(alerted)),
        "alert_rate": len(eligible & set(alerted)) / len(eligible) if eligible else None,
        "alerts": len(confirmations),
        "false_alerts": false_alerts,
        "duplicate_alerts": duplicates,
        "time_to_alert_median_s": statistics.median(delays) if delays else None,
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    """Đọc log và nhãn, tính chỉ số, in và ghi JSON."""
    args = parse_args()
    truth = {int(k): v for k, v in json.loads(args.truth.read_text(encoding="utf-8")).items()}
    timings = read_jsonl(args.run / "timings.jsonl")
    result = score(
        read_jsonl(args.run / "confirmations.jsonl"), truth,
        [r["frame_id"] for r in timings], {r["frame_id"]: r["t"] for r in timings}, args.iou, args.min_frames,
    )
    result.update(run=str(args.run), truth=str(args.truth), iou=args.iou, min_frames=args.min_frames)
    out = args.output or args.run / "track_eval.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
