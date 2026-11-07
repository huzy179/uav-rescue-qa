"""Recall, precision từng khung của các lần chạy edge/main.py trên một đoạn SDS-MOT, và số ô thật sự chạy mô hình.

Dùng để so hai cách chạy cùng một đoạn video (ví dụ có và không dùng lại ô không đổi, docs/results/tile_skip.md):
mỗi khung đã xử lý (timings.jsonl) so phát hiện (detections.jsonl, conf ≥ --conf) với nhãn truth.json của đúng khung đó,
ghép tham lam ở IoU --iou như eval.metrics.match_image (nhóm "all"). Hiệu B − A của recall và precision có khoảng tin cậy
bằng bootstrap cặp theo **khối thời gian** (--block-s giây), vì các khung liền nhau không độc lập.

Ghi một CSV: mỗi lần chạy một dòng (số khung, số ô chạy, tổng số ô, recall, precision) và với lần chạy thứ hai trở đi,
hiệu so với lần đầu kèm khoảng tin cậy.

Ví dụ:
    .venv/bin/python eval/frame_recall_mot.py --sds data/processed/sds_mot/val-m100-DJI_0001-v21 \\
        --runs runs/sds/v21_skip/off runs/sds/v21_skip/on --output runs/sds/v21_skip/frame_recall.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from eval.metrics import ALL_SIZES, SIZE_RANGES, _draw_counts, match_image
from shared.config import parse_args_with_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sds", type=Path, required=True, help="Thư mục một đoạn SDS-MOT đã chuyển (truth.json)")
    parser.add_argument("--runs", type=Path, nargs="+", required=True, help="Thư mục chạy edge/main.py; lần đầu là mốc A")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng conf của điểm vận hành")
    parser.add_argument("--iou", type=float, default=0.5, help="Ngưỡng IoU")
    parser.add_argument("--block-s", type=float, default=10.0, help="Độ dài khối thời gian cho bootstrap (giây)")
    parser.add_argument("--bootstrap", type=int, default=1000, help="Số lần bootstrap")
    parser.add_argument("--output", type=Path, required=True, help="File CSV kết quả")
    return parse_args_with_config(parser)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Các dòng JSON của một file; không có file thì rỗng."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def per_frame_counts(run: Path, truth: dict[str, list[dict[str, Any]]], conf: float, iou: float) -> dict[int, tuple[int, int, int]]:
    """frame_id → (số đúng, số dự đoán được tính, số nhãn) cho mọi khung đã xử lý của một lần chạy."""
    frames = {r["frame_id"]: r for r in read_jsonl(run / "timings.jsonl") if "frame_id" in r}
    dets: dict[int, list[dict[str, Any]]] = {}
    for d in read_jsonl(run / "detections.jsonl"):
        if d["conf"] >= conf:
            dets.setdefault(d["frame_id"], []).append(d)
    out = {}
    for fid in frames:
        gt = np.array([it["box"] for it in truth.get(str(fid), [])], dtype=float).reshape(-1, 4)
        pb = np.array([d["box_px"] for d in dets.get(fid, [])], dtype=float).reshape(-1, 4)
        pc = np.array([d["conf"] for d in dets.get(fid, [])], dtype=float)
        confs, is_tp, n_gt = match_image(pb, pc, gt, SIZE_RANGES[ALL_SIZES], iou)
        out[fid] = (int(is_tp.sum()), len(confs), n_gt)
    return out


def rates(counts: np.ndarray) -> tuple[float, float]:
    """(recall, precision) từ tổng [đúng, dự đoán, nhãn]."""
    tp, n_pred, n_gt = counts
    return (tp / n_gt if n_gt else float("nan"), tp / n_pred if n_pred else float("nan"))


def tile_totals(run: Path) -> tuple[float, float]:
    """(tổng số ô thật sự chạy, tổng số ô) qua các khung; lần chạy không dùng lại ô thì hai số bằng nhau."""
    rows = [r for r in read_jsonl(run / "timings.jsonl") if "n_tiles" in r]
    return sum(r.get("n_tiles_run", r["n_tiles"]) for r in rows), sum(r["n_tiles"] for r in rows)


def main() -> None:
    """So từng lần chạy với lần đầu; ghi CSV và in bảng."""
    args = parse_args()
    truth = json.loads((args.sds / "truth.json").read_text(encoding="utf-8"))
    fps = 30.0
    base = per_frame_counts(args.runs[0], truth, args.conf, args.iou)
    rows = []
    for run in args.runs:
        counts = per_frame_counts(run, truth, args.conf, args.iou)
        common = sorted(set(base) & set(counts))
        a = np.array([base[f] for f in common], dtype=float)
        b = np.array([counts[f] for f in common], dtype=float)
        ra, pa = rates(a.sum(axis=0))
        rb, pb = rates(b.sum(axis=0))
        ran, total = tile_totals(run)
        row: dict[str, Any] = {"run": str(run), "n_frames": len(common), "tiles_run": ran, "tiles_total": total,
                               "tiles_run_fraction": round(ran / total, 4) if total else None,
                               "recall": round(rb, 4), "precision": round(pb, 4)}
        if run != args.runs[0]:
            clusters = np.array([int(f / fps // args.block_s) for f in common])
            rng = np.random.default_rng(0)
            diffs = []
            for _ in range(args.bootstrap):
                w = _draw_counts(rng, len(common), clusters)
                diffs.append(np.subtract(rates(w @ b), rates(w @ a)))
            lo, hi = np.nanpercentile(np.array(diffs), [2.5, 97.5], axis=0)
            row.update({"recall_diff": round(rb - ra, 4), "recall_diff_lo": round(lo[0], 4), "recall_diff_hi": round(hi[0], 4),
                        "precision_diff": round(pb - pa, 4), "precision_diff_lo": round(lo[1], 4),
                        "precision_diff_hi": round(hi[1], 4)})
        rows.append(row)
        print(row)
    fields = sorted({k for r in rows for k in r}, key=lambda k: list(rows[-1]).index(k) if k in rows[-1] else 0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Lưu tại: {args.output}")


if __name__ == "__main__":
    main()
