"""E6: recall theo số pixel trên người, gộp mọi mức thu nhỏ của tools/rescale_dataset.py (ROADMAP mục 5.3).

Mỗi người ở mỗi mức thu nhỏ là một điểm; nhóm theo cạnh ngắn (px) trong ảnh đã thu nhỏ, với các nhóm mịn hơn
eval_by_size.py để vẽ được đường cong. Recall tính ở --conf (điểm vận hành), AP50 trong từng nhóm theo quy ước
COCO như eval/metrics.py. Khoảng tin cậy 95% lấy mẫu lại theo video (--cluster-pattern): mọi mức thu nhỏ của
cùng một video cùng vào hoặc cùng ra, vì chúng là cùng những người.

Bố cục đầu vào: ảnh và nhãn ở <data>/x<f>/images|labels/<split>, kết quả run_tiled.py ở <runs>/x<f>/<mô hình>.

Ví dụ:
    .venv/bin/python eval/recall_by_pixels.py --data data/processed/sds_rescale --runs runs/e6_sds \\
        --models E1 E2c --factors 1 2 3 4 6 --cluster-pattern '^(v\\d+)_' --output runs/e6_sds/eval
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from eval.eval_by_size import image_clusters, load_ground_truth
from eval.metrics import average_precision, bootstrap_ci, match_image, merge_matches, operating_point
from shared.config import parse_args_with_config
from shared.provenance import write_run_config

# Cận các nhóm cạnh ngắn (px), tăng gần gấp √2 mỗi nhóm.
EDGES = [0.0, 4.0, 6.0, 8.0, 11.0, 16.0, 23.0, 32.0, 45.0, 64.0, 91.0, float("inf")]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, required=True, help="Thư mục gốc của tools/rescale_dataset.py")
    parser.add_argument("--runs", type=Path, required=True, help="Thư mục gốc kết quả, <runs>/x<f>/<mô hình>")
    parser.add_argument("--models", nargs="+", required=True, help="Tên thư mục mô hình trong <runs>/x<f>/")
    parser.add_argument("--factors", type=float, nargs="+", required=True, help="Các mức thu nhỏ")
    parser.add_argument("--split", default="val", help="Phần dữ liệu")
    parser.add_argument("--gt-classes", type=int, nargs="+", default=[0], help="Mã lớp người trong nhãn")
    parser.add_argument("--iou", type=float, default=0.5, help="Ngưỡng IoU")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng conf của điểm vận hành")
    parser.add_argument("--bootstrap", type=int, default=1000, help="Số lần lấy mẫu lại (0 để tắt)")
    parser.add_argument("--cluster-pattern", default=None, help="Regex lấy mã video từ tên ảnh để bootstrap theo video")
    parser.add_argument("--output", type=Path, required=True, help="Thư mục ghi recall_by_pixels.csv, recall_by_factor.csv và hình")
    return parse_args_with_config(parser)


def factor_name(factor: float) -> str:
    """Tên thư mục mức thu nhỏ, như tools/rescale_dataset.py: 2 → x2, 2.1 → x2.1."""
    return f"x{factor:g}"


def bin_label(lo: float, hi: float) -> str:
    return f">={lo:g}" if hi == float("inf") else f"{lo:g}-{hi:g}"


def match_parts(boxes: pd.DataFrame, ground_truth: dict[str, Any], size_range: tuple[float, float], iou: float) -> list:
    """Kết quả so khớp từng ảnh trong một nhóm kích thước, theo thứ tự của ground_truth."""
    preds_by_image = {name: group for name, group in boxes.groupby("image")}
    empty = boxes.iloc[0:0]
    parts = []
    for name, (gt_boxes, ignore) in ground_truth.items():
        preds = preds_by_image.get(name, empty)
        parts.append(match_image(
            preds[["x1", "y1", "x2", "y2"]].to_numpy(dtype=float), preds["conf"].to_numpy(dtype=float),
            gt_boxes, size_range, iou, ignore,
        ))
    return parts


def main() -> None:
    """Ghép mọi mức, tính recall và AP theo nhóm pixel cho từng mô hình, ghi CSV và hình."""
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    write_run_config(args.output, Path(__file__).name, None, None, vars(args))
    recall_at = lambda m: operating_point(m, args.conf)[0]  # noqa: E731
    rows, by_factor = [], []
    for model in args.models:
        parts_by_bin: dict[str, list] = {bin_label(lo, hi): [] for lo, hi in zip(EDGES, EDGES[1:])}
        names: list[str] = []
        for factor in args.factors:
            root, run = args.data / factor_name(factor), args.runs / factor_name(factor) / model
            boxes = pd.read_csv(run / "boxes.csv")
            image_names = pd.read_csv(run / "per_image.csv")["image"].tolist()
            ground_truth = load_ground_truth(
                image_names, root / "images" / args.split, root / "labels" / args.split, args.gt_classes
            )
            names += list(ground_truth)
            whole = match_parts(boxes, ground_truth, (0.0, float("inf")), args.iou)
            ci = bootstrap_ci(whole, [recall_at, average_precision], args.bootstrap, 0,
                              image_clusters(list(ground_truth), args.cluster_pattern))
            m = merge_matches(whole)
            by_factor.append({"model": model, "factor": factor, "n_gt": m.n_gt, "recall": recall_at(m),
                              "recall_lo": ci[0, 0], "recall_hi": ci[0, 1], "ap50": average_precision(m),
                              "ap50_lo": ci[1, 0], "ap50_hi": ci[1, 1]})
            for lo, hi in zip(EDGES, EDGES[1:]):
                parts_by_bin[bin_label(lo, hi)] += match_parts(boxes, ground_truth, (lo, hi), args.iou)
        clusters = image_clusters(names, args.cluster_pattern)
        for (lo, hi), (label, parts) in zip(zip(EDGES, EDGES[1:]), parts_by_bin.items()):
            match = merge_matches(parts)
            if match.n_gt == 0:
                continue
            (r_lo, r_hi), (ap_lo, ap_hi) = bootstrap_ci(parts, [recall_at, average_precision], args.bootstrap, 0, clusters)
            rows.append({
                "model": model, "size_px": label, "lo": lo, "hi": hi, "n_gt": match.n_gt,
                "recall": recall_at(match), "recall_lo": r_lo, "recall_hi": r_hi,
                "ap50": average_precision(match), "ap50_lo": ap_lo, "ap50_hi": ap_hi,
            })
    table = pd.DataFrame(rows)
    table.to_csv(args.output / "recall_by_pixels.csv", index=False)
    print(table.round(3).to_string(index=False))
    factors = pd.DataFrame(by_factor)
    factors.to_csv(args.output / "recall_by_factor.csv", index=False)
    print("\nMọi kích thước, theo mức thu nhỏ:")
    print(factors.round(3).to_string(index=False))
    plot(table, args.conf, args.output / "recall_by_pixels.png")


def plot(table: pd.DataFrame, conf: float, out_path: Path) -> None:
    """Recall theo cạnh ngắn người (trục log), mỗi mô hình một đường, dải là khoảng tin cậy 95%."""
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for color, (model, group) in zip(COLORS, table.groupby("model", sort=False)):
        lo = group["lo"].clip(lower=2).to_numpy()
        hi = np.where(np.isinf(group["hi"]), lo * 1.41, group["hi"])
        x = np.sqrt(lo * hi)  # tâm nhóm trên trục log; nhóm cuối không có cận trên nên lấy thêm một bậc √2
        ax.fill_between(x, group["recall_lo"], group["recall_hi"], color=color, alpha=0.15, linewidth=0)
        ax.plot(x, group["recall"], color=color, linewidth=2, marker="o", markersize=5, label=model)
    ax.set_xscale("log")
    ax.set_xticks([4, 8, 16, 32, 64, 128], labels=["4", "8", "16", "32", "64", "128"])
    ax.set_ylim(0, 1)
    ax.set_xlabel("Cạnh ngắn người (px, sau thu nhỏ)")
    ax.set_ylabel(f"Recall @ conf {conf:g}")
    ax.grid(alpha=0.25, linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
