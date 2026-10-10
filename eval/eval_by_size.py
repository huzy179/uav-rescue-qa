"""Đánh giá kết quả của run_baseline.py / run_sahi.py so với nhãn YOLO: AP, recall, precision theo nhóm kích thước."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image


from eval.metrics import (
    ALL_SIZES,
    SIZE_RANGES,
    MatchResult,
    average_precision,
    load_yolo_labels,
    match_image,
    merge_matches,
    operating_point,
    pr_curve,
)
from eval.report import (
    GRID_COLOR,
    MUTED_COLOR,
    SERIES_COLORS,
    SIZE_BIN_LABELS,
    SURFACE_COLOR,
    TEXT_COLOR,
    write_run_config,
)
from edge.sampler import IMAGE_EXTS


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs", type=Path, nargs="+", required=True, help="Các thư mục kết quả có boxes.csv và per_image.csv"
    )
    parser.add_argument("--images", type=Path, required=True, help="Thư mục ảnh gốc (để lấy kích thước ảnh)")
    parser.add_argument("--labels", type=Path, required=True, help="Thư mục nhãn YOLO (.txt cùng tên với ảnh)")
    parser.add_argument(
        "--ignore", type=Path, default=None, help="Thư mục vùng bỏ qua dạng YOLO (.txt cùng tên ảnh), ví dụ của VisDrone"
    )
    parser.add_argument("--gt-classes", type=int, nargs="+", default=[0], help="Các mã lớp trong nhãn được coi là người")
    parser.add_argument("--iou", type=float, default=0.5, help="Ngưỡng IoU để coi là phát hiện đúng")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng conf của điểm vận hành (recall, precision)")
    parser.add_argument("--output", type=Path, default=Path("runs/eval"), help="Thư mục kết quả")
    return parser.parse_args()


def load_ground_truth(
    image_names: list[str], images_dir: Path, labels_dir: Path, classes: list[int], ignore_dir: Path | None = None
) -> dict[str, Any]:
    """Đọc nhãn (và vùng bỏ qua nếu có) của từng ảnh, quy đổi về pixel; ảnh không có file nhãn coi như không có người."""
    by_stem = {p.stem: p for p in images_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS}
    ground_truth = {}
    missing_images = []
    n_missing_labels = 0
    for name in image_names:
        stem = Path(name).stem
        if stem not in by_stem:
            missing_images.append(name)
            continue
        with Image.open(by_stem[stem]) as img:
            width, height = img.size
        label_path = labels_dir / f"{stem}.txt"
        n_missing_labels += not label_path.is_file()
        ignore = (
            load_yolo_labels(ignore_dir / f"{stem}.txt", width, height, [0]) if ignore_dir is not None else None
        )
        ground_truth[name] = (load_yolo_labels(label_path, width, height, classes), ignore)
    if missing_images:
        raise FileNotFoundError(
            f"{len(missing_images)} ảnh trong per_image.csv không có trong {images_dir}, ví dụ: {missing_images[:3]}"
        )
    if n_missing_labels:
        print(f"[cảnh báo] {n_missing_labels}/{len(image_names)} ảnh không có file nhãn, coi như không có người.")
    return ground_truth


def evaluate_config(
    boxes: pd.DataFrame, ground_truth: dict[str, Any], iou_thr: float
) -> dict[str, MatchResult]:
    """So khớp dự đoán của một cấu hình với nhãn, cho từng nhóm kích thước."""
    preds_by_image = {name: group for name, group in boxes.groupby("image")}
    empty = boxes.iloc[0:0]
    results = {}
    for size_label, size_range in SIZE_RANGES.items():
        parts = []
        for name, (gt_boxes, ignore_regions) in ground_truth.items():
            preds = preds_by_image.get(name, empty)
            parts.append(
                match_image(
                    preds[["x1", "y1", "x2", "y2"]].to_numpy(dtype=float),
                    preds["conf"].to_numpy(dtype=float),
                    gt_boxes,
                    size_range,
                    iou_thr,
                    ignore_regions,
                )
            )
        results[size_label] = merge_matches(parts)
    return results


def plot_results(curves: dict[str, MatchResult], table: pd.DataFrame, iou_thr: float, conf_thr: float, out_path: Path) -> None:
    """Vẽ đường precision-recall (mọi kích thước) và recall theo nhóm kích thước cho từng cấu hình."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, (ax_pr, ax_rec) = plt.subplots(1, 2, figsize=(12, 4.5), facecolor=SURFACE_COLOR)
    for ax in (ax_pr, ax_rec):
        ax.set_facecolor(SURFACE_COLOR)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color(GRID_COLOR)
        ax.tick_params(colors=MUTED_COLOR)
        ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8)
        ax.set_axisbelow(True)

    for (label, match), color in zip(curves.items(), SERIES_COLORS):
        recall, precision = pr_curve(match)
        ax_pr.plot(recall, precision, color=color, linewidth=2, label=label)
    ax_pr.set_xlim(0, 1)
    ax_pr.set_ylim(0, 1.02)
    ax_pr.set_xlabel("Recall", color=TEXT_COLOR)
    ax_pr.set_ylabel("Precision", color=TEXT_COLOR)
    ax_pr.set_title(f"Đường precision-recall, mọi kích thước (IoU ≥ {iou_thr:g})", color=TEXT_COLOR, loc="left")

    x = np.arange(len(SIZE_BIN_LABELS))
    bar_width = 0.8 / max(len(curves), 1)
    for i, (label, color) in enumerate(zip(curves, SERIES_COLORS)):
        rows = table[table["config"] == label].set_index("size_bin")
        recalls = [rows.loc[b, "recall"] if b in rows.index else float("nan") for b in SIZE_BIN_LABELS]
        ax_rec.bar(
            x - 0.4 + (i + 0.5) * bar_width,
            np.nan_to_num(recalls),
            width=bar_width,
            color=color,
            edgecolor=SURFACE_COLOR,
            linewidth=2,
            label=label,
        )
    n_gt = table[table["config"] == next(iter(curves))].set_index("size_bin")["n_gt"] if curves else {}
    ax_rec.set_xticks(x, [f"{b} px\n(n={int(n_gt.get(b, 0))})" for b in SIZE_BIN_LABELS])
    ax_rec.set_ylim(0, 1.02)
    ax_rec.set_xlabel("Cạnh ngắn của nhãn (số nhãn trong nhóm)", color=TEXT_COLOR)
    ax_rec.set_ylabel("Recall", color=TEXT_COLOR)
    ax_rec.set_title(f"Recall theo nhóm kích thước (conf ≥ {conf_thr:g})", color=TEXT_COLOR, loc="left")
    ax_rec.legend(frameon=False, labelcolor=TEXT_COLOR)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=SURFACE_COLOR)
    plt.close(fig)


def main() -> None:
    """Đánh giá mọi cấu hình (method, imgsz) trong các thư mục kết quả rồi xuất bảng, biểu đồ và run_config.json."""
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    boxes = pd.concat([pd.read_csv(run / "boxes.csv") for run in args.runs], ignore_index=True)
    images = pd.concat([pd.read_csv(run / "per_image.csv") for run in args.runs], ignore_index=True)

    rows = []
    curves: dict[str, MatchResult] = {}
    for (method, imgsz), image_group in images.groupby(["method", "imgsz"], sort=False):
        config = f"{method} imgsz={imgsz}"
        ground_truth = load_ground_truth(
            image_group["image"].tolist(), args.images, args.labels, args.gt_classes, args.ignore
        )
        config_boxes = boxes[(boxes["method"] == method) & (boxes["imgsz"] == imgsz)]
        results = evaluate_config(config_boxes, ground_truth, args.iou)
        curves[config] = results[ALL_SIZES]
        for size_label, match in results.items():
            recall, precision = operating_point(match, args.conf)
            recall_max, _ = operating_point(match, 0.0)
            rows.append(
                {
                    "config": config,
                    "size_bin": size_label,
                    "n_images": len(ground_truth),
                    "n_gt": match.n_gt,
                    "AP": round(average_precision(match), 4),
                    "recall": round(recall, 4),
                    "precision": round(precision, 4),
                    "recall_max": round(recall_max, 4),
                }
            )

    table = pd.DataFrame(rows)
    table.to_csv(args.output / "eval_by_size.csv", index=False)
    plot_results(curves, table, args.iou, args.conf, args.output / "eval_by_size.png")
    write_run_config(args.output, Path(__file__).name, None, None, vars(args))
    print(f"IoU ≥ {args.iou:g}; recall và precision tại conf ≥ {args.conf:g}; recall_max là recall khi giữ mọi dự đoán.")
    print(table.to_string(index=False))
    print(f"\nKết quả lưu tại: {args.output}")


if __name__ == "__main__":
    main()
