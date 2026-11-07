"""Chấm ước tính số người quanh mỗi cảnh báo (group_size) trên video SeaDronesSee có nhãn (docs/results/rq3_group.md).

Với mỗi cảnh báo trong alerts.jsonl của một lần chạy edge/main.py trên đoạn SDS-MOT: lấy khung nhãn ở thời điểm cảnh
báo (t × source_fps), tìm nhãn người khớp box của cảnh báo (IoU lớn nhất, ít nhất --min-iou; không khớp thì là cảnh báo
nhầm, bỏ qua), chiếu tâm đáy mọi box nhãn của khung đó xuống mặt đất bằng chính telemetry (như
tools/make_truth_layer.py), rồi đếm số người trong --radius-m quanh người được báo. Chỉ đếm người có trong khung; người
ngoài khung không ai biết, kể cả hệ thống.

Ghi một CSV mỗi lần chạy một dòng: số cảnh báo khớp nhãn, tỉ lệ đúng số người, sai số trung bình (âm là đếm thiếu), sai
số tuyệt đối trung bình, số cảnh báo đếm thừa và đếm thiếu, phân bố số người thật.

Ví dụ:
    .venv/bin/python eval/group_count_eval.py --sds data/processed/sds_mot/val-m100-DJI_0001-v21 \\
        --runs runs/sds/val-m100-DJI_0001-v21/group_frame runs/sds/val-m100-DJI_0001-v21/group_clusters \\
        --output runs/sds/group_count_v21.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from edge.georef import Camera, ground_distance_m, pixel_to_gps
from edge.telemetry import NadirTelemetry, SampledTelemetry
from eval.metrics import iou_matrix
from shared.schema import GROUP_RADIUS_M, Alert


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sds", type=Path, required=True, help="Thư mục một đoạn SDS-MOT đã chuyển (truth.json, telemetry.csv, info.json)")
    parser.add_argument("--runs", type=Path, nargs="+", required=True, help="Thư mục chạy của edge/main.py (alerts.jsonl)")
    parser.add_argument("--source-fps", type=float, default=30.0, help="Số khung mỗi giây của chuỗi khung nguồn")
    parser.add_argument("--fov-deg", type=float, default=82.0, help="Góc nhìn chéo của camera (độ), như configs/edge.yaml")
    parser.add_argument("--radius-m", type=float, default=GROUP_RADIUS_M, help="Bán kính đếm (m), như group_size")
    parser.add_argument("--min-iou", type=float, default=0.3, help="IoU tối thiểu để box cảnh báo khớp một nhãn")
    parser.add_argument("--output", type=Path, required=True, help="File CSV kết quả")
    return parser.parse_args()


def true_group_sizes(
    alerts: list[Alert], truth: dict[str, list[dict[str, Any]]], telemetry: Any, cam: Camera, source_fps: float,
    radius_m: float, min_iou: float,
) -> list[tuple[int, int]]:
    """(group_size ước tính, số người thật) cho mỗi cảnh báo khớp nhãn."""
    out = []
    for alert in alerts:
        items = truth.get(str(round(alert.t * source_fps)), [])
        if not items or alert.box_px is None:
            continue
        boxes = np.array([it["box"] for it in items], dtype=float)
        ious = iou_matrix(np.array([alert.box_px], dtype=float), boxes)[0]
        best = int(np.argmax(ious))
        if ious[best] < min_iou:
            continue
        tel = telemetry.at(alert.t)
        ground = [pixel_to_gps((b[0] + b[2]) / 2.0, b[3], tel, cam) for b in boxes]
        n_true = sum(1 for g in ground if ground_distance_m(*ground[best], *g) <= radius_m)
        out.append((alert.group_size, n_true))
    return out


def summarize(pairs: list[tuple[int, int]]) -> dict[str, Any]:
    """Chỉ số tổng của một lần chạy."""
    errors = [est - true for est, true in pairs]
    n = len(errors)
    return {
        "n_alerts_matched": n,
        "exact": round(sum(e == 0 for e in errors) / n, 4) if n else None,
        "error_mean": round(sum(errors) / n, 4) if n else None,
        "abs_error_mean": round(sum(abs(e) for e in errors) / n, 4) if n else None,
        "n_over": sum(e > 0 for e in errors),
        "n_under": sum(e < 0 for e in errors),
        "true_sizes": json.dumps(dict(sorted(Counter(true for _, true in pairs).items()))),
    }


def main() -> None:
    """Chấm từng lần chạy, ghi CSV, in bảng."""
    args = parse_args()
    info = json.loads((args.sds / "info.json").read_text(encoding="utf-8"))
    truth = json.loads((args.sds / "truth.json").read_text(encoding="utf-8"))
    telemetry = NadirTelemetry(SampledTelemetry.from_csv(args.sds / "telemetry.csv"))  # cùng giả định với pipeline
    cam = Camera.from_fov(args.fov_deg, "diagonal", info["width"], info["height"])
    rows = []
    for run in args.runs:
        alerts = [Alert.model_validate_json(line) for line in (run / "alerts.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        row = {"run": str(run), "n_alerts": len(alerts),
               **summarize(true_group_sizes(alerts, truth, telemetry, cam, args.source_fps, args.radius_m, args.min_iou))}
        rows.append(row)
        print(f"{run}: {row['n_alerts_matched']}/{row['n_alerts']} cảnh báo khớp nhãn, đúng số người {row['exact']}, "
              f"sai số TB {row['error_mean']}, thừa {row['n_over']}, thiếu {row['n_under']}, người thật {row['true_sizes']}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Lưu tại: {args.output}")


if __name__ == "__main__":
    main()
