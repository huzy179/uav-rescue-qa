"""Ghép độ chính xác và thời gian của các biến thể RQ2 thành một bảng và hình recall theo FPS (TECHNICAL mục 14.3).

Đọc thư mục kết quả của scripts/run_rq2.py:
- <rq2>/timing.csv (eval/timing_summary.py): thời gian từng chặng, FPS theo p95;
- <rq2>/<tập>/eval_<biến thể>_iou0.5/eval_by_size.csv: AP50, recall ở conf 0,25 (mọi người);
- <rq2>/<tập>/eval_<biến thể>_iou0.3/eval_by_size.csv: recall người dưới 8 px ở IoU 0,3.

Ghi <rq2>/rq2.csv (mỗi dòng một biến thể × một tập) và rq2_<tập>.png: mỗi biến thể một điểm (FPS theo p95, recall),
đường dọc ở 2 FPS là mức tối thiểu của pipeline (TECHNICAL 2.4). Biến thể nằm bên phải đường và cao nhất là lựa chọn.
FPS lấy từ p95 chứ không từ trung bình: chọn theo trung bình thì 1 khung trong 20 không kịp xử lý.

Ví dụ:
    .venv/bin/python eval/rq2_tradeoff.py --rq2 runs/rq2 --rq2-config configs/experiments/rq2_t4.yaml
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import yaml

from shared.config import parse_args_with_config

MIN_FPS = 2.0


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rq2", type=Path, required=True, help="Thư mục kết quả của scripts/run_rq2.py")
    parser.add_argument("--rq2-config", type=Path, required=True, help="File YAML cấu hình RQ2 đã dùng")
    return parse_args_with_config(parser)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Đọc CSV thành list dict; file không có thì list rỗng."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def size_row(rows: list[dict[str, str]], size_bin: str) -> dict[str, str]:
    """Dòng của một nhóm kích thước trong eval_by_size.csv (một lần chạy mỗi file)."""
    return next((r for r in rows if r["size_bin"] == size_bin), {})


def number(value: str | None) -> float | None:
    """Ô CSV thành số; ô trống thành None."""
    return float(value) if value not in (None, "") else None


def tradeoff_rows(rq2: Path, variants: list[dict[str, Any]], datasets: list[str]) -> list[dict[str, Any]]:
    """Một dòng cho mỗi biến thể × tập có kết quả; thiếu thời gian hay độ chính xác thì để trống phần đó."""
    timing = {Path(r["run"]).name: r for r in read_csv(rq2 / "timing.csv")}
    rows = []
    for data in datasets:
        for v in variants:
            name = v["name"]
            at05 = read_csv(rq2 / data / f"eval_{name}_iou0.5" / "eval_by_size.csv")
            at03 = read_csv(rq2 / data / f"eval_{name}_iou0.3" / "eval_by_size.csv")
            if not at05:
                continue
            t = timing.get(name, {})
            rows.append({
                "dataset": data,
                "variant": name,
                "precision": v["precision"],
                "mode": v.get("mode", "tiled"),
                "target_person_px": v.get("target_person_px"),
                "AP50": number(size_row(at05, "all").get("AP")),
                "recall": number(size_row(at05, "all").get("recall")),
                "precision_at_025": number(size_row(at05, "all").get("precision")),
                "recall_lt8_iou03": number(size_row(at03, "<8").get("recall")),
                "infer_ms_p95": number(t.get("infer_ms_p95")),
                "total_ms_p50": number(t.get("total_ms_p50")),
                "total_ms_p95": number(t.get("total_ms_p95")),
                "fps_at_p95": number(t.get("fps_at_p95")),
                "n_tiles": number(t.get("n_tiles")),
                "gpu": t.get("gpu"),
            })
    return rows


def plot(rows: list[dict[str, Any]], data: str, path: Path) -> None:
    """Recall theo FPS (p95) của các biến thể trên một tập, đánh dấu 2 FPS."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    points = [r for r in rows if r["dataset"] == data and r["fps_at_p95"] is not None and r["recall"] is not None]
    if not points:
        return
    fig, ax = plt.subplots(figsize=(7, 4.5))
    markers = {"pt": "o", "fp32": "s", "fp16": "^", "int8": "D"}
    for r in points:
        ax.scatter(r["fps_at_p95"], r["recall"], marker=markers[r["precision"]], s=50)
        ax.annotate(r["variant"], (r["fps_at_p95"], r["recall"]), textcoords="offset points", xytext=(5, 4), fontsize=8)
    ax.axvline(MIN_FPS, color="grey", linestyle="--", linewidth=1)
    ax.text(MIN_FPS, ax.get_ylim()[0], " 2 FPS", color="grey", va="bottom", fontsize=8)
    gpu = points[0]["gpu"] or "?"
    ax.set_xlabel(f"FPS cả pipeline theo p95 ({gpu}; chỉ để so sánh tương đối)")
    ax.set_ylabel("Recall @ conf 0,25, IoU 0,5")
    ax.set_title(f"RQ2: recall theo tốc độ, {data}")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    """Đọc cấu hình và kết quả, ghi rq2.csv, vẽ hình mỗi tập, in bảng gọn."""
    args = parse_args()
    config = yaml.safe_load(args.rq2_config.read_text(encoding="utf-8"))
    datasets = [d["name"] for d in config["accuracy"]]
    rows = tradeoff_rows(args.rq2, config["variants"], datasets)
    if not rows:
        raise SystemExit(f"Chưa có kết quả độ chính xác nào trong {args.rq2}")
    out = args.rq2 / "rq2.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for data in datasets:
        plot(rows, data, args.rq2 / f"rq2_{data}.png")
    for r in rows:
        print(f"{r['dataset']:>18} {r['variant']:>20}: AP50 {r['AP50']}, recall {r['recall']}, "
              f"{r['fps_at_p95']} FPS (p95)")
    print(f"Lưu tại: {out}")


if __name__ == "__main__":
    main()
