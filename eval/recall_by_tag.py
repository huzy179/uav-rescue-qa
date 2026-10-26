"""Recall theo loại nhiễu trên tập test lũ (TECHNICAL mục 5.7): theo thẻ ảnh và theo thuộc tính từng người.

Đầu vào là boxes_<split>.csv và tags_<split>.csv của tools/convert_cvat.py cùng boxes.csv của một hay nhiều lần chạy
(run_baseline.py, run_sahi.py, run_tiled.py). Mọi chỉ số ở điểm vận hành --conf:
- recall trên tập con người: thuộc ảnh có thẻ (glare, weather, blur, floating_debris), hoặc có thuộc tính
  (partly_submerged, occluded); kèm tập con "không thẻ" / "không thuộc tính" để so;
- báo nhầm mỗi ảnh trên từng tập con ảnh (đo báo động giả do rác trôi ở ảnh floating_debris).

So khớp tham lam theo conf giảm dần, IoU ≥ --iou, như eval/metrics.py; dự đoán không khớp mà nằm trong vùng bỏ qua
(--ignore, IoA ≥ 0,5) không tính là báo nhầm. Tập con nhỏ nên luôn kèm khoảng tin cậy 95% bootstrap theo ảnh,
hoặc theo video khi có --cluster-pattern.

Ví dụ:
    .venv/bin/python eval/recall_by_tag.py --runs runs/flood/E1 runs/flood/E2c --annotations data/processed/flood \\
        --split test --ignore data/processed/flood/ignore/test --cluster-pattern '^(.+)_\\d+$' --output runs/flood/eval_tags
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from eval.eval_by_size import image_clusters
from eval.metrics import ioa_matrix, iou_matrix, load_yolo_labels
from shared.config import parse_args_with_config
from shared.provenance import write_run_config

BOX_ATTRIBUTES = ["partly_submerged", "occluded"]


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=Path, nargs="+", required=True, help="Các thư mục kết quả có boxes.csv")
    parser.add_argument("--annotations", type=Path, required=True, help="Thư mục có boxes_<split>.csv, tags_<split>.csv")
    parser.add_argument("--split", default="test", help="Phần dữ liệu")
    parser.add_argument("--ignore", type=Path, default=None, help="Thư mục vùng bỏ qua dạng YOLO")
    parser.add_argument("--images", type=Path, default=None, help="Thư mục ảnh (để đổi vùng bỏ qua ra pixel); mặc định <annotations>/images/<split>")
    parser.add_argument("--iou", type=float, default=0.5, help="Ngưỡng IoU")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng conf của điểm vận hành")
    parser.add_argument("--bootstrap", type=int, default=1000, help="Số lần lấy mẫu lại (0 để tắt)")
    parser.add_argument("--cluster-pattern", default=None, help="Regex lấy mã video từ tên ảnh để bootstrap theo video")
    parser.add_argument("--output", type=Path, required=True, help="Thư mục ghi recall_by_tag.csv")
    return parse_args_with_config(parser)


def match_flags(
    preds: np.ndarray, confs: np.ndarray, gts: np.ndarray, iou_thr: float, ignore: np.ndarray | None = None
) -> tuple[np.ndarray, int]:
    """Người thật nào được phát hiện (mảng bool theo thứ tự gts) và số báo nhầm, so khớp tham lam theo conf giảm dần."""
    ious = iou_matrix(preds, gts)
    in_ignored = (
        ioa_matrix(preds, ignore).max(axis=1) >= 0.5 if ignore is not None and len(ignore) else np.zeros(len(preds), bool)
    )
    found = np.zeros(len(gts), dtype=bool)
    false_positives = 0
    for i in np.argsort(-confs):
        candidates = np.where((ious[i] >= iou_thr) & ~found)[0] if len(gts) else np.array([], dtype=int)
        if len(candidates):
            found[candidates[np.argmax(ious[i, candidates])]] = True
        elif not in_ignored[i]:
            false_positives += 1
    return found, false_positives


def subsets(gt: pd.DataFrame, tags: pd.DataFrame) -> dict[str, tuple[str, pd.Series, pd.Series]]:
    """Tên tập con → (loại, mặt nạ trên người, mặt nạ trên ảnh)."""
    tag_names = [c for c in tags.columns if c != "image"]
    image_tagged = tags.set_index("image")[tag_names]
    tag_of_gt = image_tagged.reindex(gt["image"]).reset_index(drop=True)
    all_images = pd.Series(True, index=tags.index)
    out = {"tất cả": ("tất cả", pd.Series(True, index=gt.index), all_images)}
    for tag in tag_names:
        out[tag] = ("thẻ ảnh", tag_of_gt[tag] == 1, tags[tag] == 1)
    out["ảnh không thẻ"] = ("thẻ ảnh", tag_of_gt.sum(axis=1) == 0, tags[tag_names].sum(axis=1) == 0)
    attrs = [a for a in BOX_ATTRIBUTES if a in gt.columns]
    for attr in attrs:
        out[attr] = ("thuộc tính người", gt[attr] == 1, pd.Series(False, index=tags.index))
    out["người không thuộc tính"] = ("thuộc tính người", gt[attrs].sum(axis=1) == 0, pd.Series(False, index=tags.index))
    return out


def ratio_ci(num: np.ndarray, den: np.ndarray, clusters: np.ndarray, n_boot: int, seed: int = 0) -> tuple[float, float]:
    """Khoảng tin cậy 95% của sum(num)/sum(den), lấy mẫu lại theo cụm (mỗi ảnh một cụm nếu không có video)."""
    if n_boot <= 0 or den.sum() == 0:
        return float("nan"), float("nan")
    _, index = np.unique(clusters, return_inverse=True)
    num_c, den_c = np.bincount(index, num), np.bincount(index, den)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(num_c), (n_boot, len(num_c)))
    d = den_c[draws].sum(axis=1)
    values = np.where(d > 0, num_c[draws].sum(axis=1) / np.maximum(d, 1e-12), np.nan)
    lo, hi = np.nanpercentile(values, [2.5, 97.5])
    return float(lo), float(hi)


def main() -> None:
    """Tính recall và báo nhầm mỗi ảnh theo từng tập con cho từng lần chạy, ghi CSV."""
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    write_run_config(args.output, Path(__file__).name, None, None, vars(args))
    gt = pd.read_csv(args.annotations / f"boxes_{args.split}.csv")
    tags = pd.read_csv(args.annotations / f"tags_{args.split}.csv")
    images = list(tags["image"])
    image_dir = args.images or args.annotations / "images" / args.split
    ignores = {}
    if args.ignore is not None:
        for name in images:
            with Image.open(image_dir / name) as img:
                ignores[name] = load_yolo_labels(args.ignore / f"{Path(name).stem}.txt", *img.size, [0])
    clusters = image_clusters(images, args.cluster_pattern)
    clusters = np.arange(len(images)) if clusters is None else clusters
    image_pos = {name: i for i, name in enumerate(images)}
    gt_image = gt["image"].map(image_pos).to_numpy()
    defined = subsets(gt, tags)

    rows = []
    for run in args.runs:
        boxes = pd.read_csv(run / "boxes.csv")
        boxes = boxes[boxes["conf"] >= args.conf]
        by_image = {name: g for name, g in boxes.groupby("image")}
        found = np.zeros(len(gt), dtype=bool)
        fps = np.zeros(len(images))
        for name in images:
            preds = by_image.get(name, boxes.iloc[0:0])
            rows_gt = np.where(gt["image"].to_numpy() == name)[0]
            flags, fps[image_pos[name]] = match_flags(
                preds[["x1", "y1", "x2", "y2"]].to_numpy(float), preds["conf"].to_numpy(float),
                gt.loc[rows_gt, ["x1", "y1", "x2", "y2"]].to_numpy(float), args.iou, ignores.get(name),
            )
            found[rows_gt] = flags
        for subset, (kind, gt_mask, image_mask) in defined.items():
            m = gt_mask.to_numpy()
            hits = np.bincount(gt_image[m], found[m], minlength=len(images))
            total = np.bincount(gt_image[m], minlength=len(images)).astype(float)
            n_gt = int(total.sum())
            recall = hits.sum() / n_gt if n_gt else float("nan")
            r_lo, r_hi = ratio_ci(hits, total, clusters, args.bootstrap)
            im = image_mask.to_numpy()
            n_img = int(im.sum())
            fp_rate = fps[im].mean() if n_img else float("nan")
            fp_lo, fp_hi = ratio_ci(fps * im, im.astype(float), clusters, args.bootstrap) if n_img else (float("nan"),) * 2
            rows.append({
                "run": str(run), "subset": subset, "kind": kind, "n_gt": n_gt, "recall": recall,
                "recall_lo": r_lo, "recall_hi": r_hi, "n_images": n_img, "fp_per_image": fp_rate,
                "fp_per_image_lo": fp_lo, "fp_per_image_hi": fp_hi,
            })
    table = pd.DataFrame(rows)
    table.to_csv(args.output / "recall_by_tag.csv", index=False)
    print(table.drop(columns="kind").round(3).to_string(index=False))


if __name__ == "__main__":
    main()
