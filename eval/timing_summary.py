"""Tổng hợp thời gian từng chặng của pipeline từ timings.jsonl (RQ2, TECHNICAL mục 14).

Với mỗi thư mục chạy của edge/main.py: trung bình, p50, p95 (ms) của từng chặng (cắt ô, suy luận, gộp, georef,
confirm) và của tổng, cùng FPS đạt được. FPS tính từ p95 là con số nên dùng để chọn tần số khung: chọn theo trung
bình thì 1 khung trong 20 sẽ không kịp xử lý.

Ghi máy chạy (`machine` trong run_config.json) vào bảng: số đo trên Mac (arm64, MPS) chỉ dùng để so sánh tương đối,
không phải số cho Jetson (CLAUDE.md).

Ví dụ:
    .venv/bin/python eval/timing_summary.py --runs runs/edge/demo runs/edge/demo_full --output runs/edge/timing.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

STAGES = ["tile_ms", "infer_ms", "merge_ms", "georef_ms", "confirm_ms"]


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=Path, nargs="+", required=True, help="Thư mục chạy của edge/main.py (có timings.jsonl)")
    parser.add_argument("--output", type=Path, required=True, help="File CSV kết quả")
    return parser.parse_args()


def summarize_timings(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Thống kê từng chặng và tổng mỗi khung; chặng không có trong log (ví dụ khi --replay) để trống."""
    if not records:
        raise ValueError("timings.jsonl rỗng")
    row: dict[str, Any] = {"n_frames": len(records)}
    total = np.zeros(len(records))
    for stage in STAGES:
        values = np.array([r.get(stage, np.nan) for r in records], dtype=float)
        if np.isnan(values).all():
            row.update({f"{stage}_mean": None, f"{stage}_p50": None, f"{stage}_p95": None})
            continue
        total += np.nan_to_num(values)
        row.update(
            {
                f"{stage}_mean": round(float(np.nanmean(values)), 2),
                f"{stage}_p50": round(float(np.nanpercentile(values, 50)), 2),
                f"{stage}_p95": round(float(np.nanpercentile(values, 95)), 2),
            }
        )
    row.update(
        {
            "total_ms_mean": round(float(total.mean()), 2),
            "total_ms_p50": round(float(np.percentile(total, 50)), 2),
            "total_ms_p95": round(float(np.percentile(total, 95)), 2),
            "n_tiles": records[0].get("n_tiles"),
            "n_dets_mean": round(float(np.mean([r.get("n_dets", 0) for r in records])), 1),
        }
    )
    row["fps_at_mean"] = round(1000.0 / row["total_ms_mean"], 2) if row["total_ms_mean"] > 0 else None
    row["fps_at_p95"] = round(1000.0 / row["total_ms_p95"], 2) if row["total_ms_p95"] > 0 else None
    return row


def main() -> None:
    """Đọc từng thư mục chạy, tổng hợp, ghi CSV và in bảng."""
    args = parse_args()
    rows = []
    for run in args.runs:
        with (run / "timings.jsonl").open(encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]
        config = json.loads((run / "run_config.json").read_text(encoding="utf-8"))
        run_args = config.get("args", {})
        rows.append(
            {
                "run": str(run),
                "machine": config.get("machine"),
                "device": config.get("device"),
                "model": config.get("model"),
                "mode": run_args.get("mode"),
                "imgsz": run_args.get("imgsz"),
                "tile": run_args.get("tile"),
                **summarize_timings(records),
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(
            f"{row['run']}: {row['machine']}/{row['device']}, {row['n_tiles']} ô, tổng p50 {row['total_ms_p50']} ms, "
            f"p95 {row['total_ms_p95']} ms → {row['fps_at_p95']} FPS (theo p95)"
        )
    if any(r["machine"] == "arm64" for r in rows):
        print("[lưu ý] Có lần chạy trên Mac (arm64): chỉ dùng để so sánh tương đối, không phải số cho Jetson.")
    print(f"Lưu tại: {args.output}")


if __name__ == "__main__":
    main()
