"""Ngưỡng tin cậy theo cỡ box dự đoán (docs/CAI_TIEN.md mục 1.4): chọn trên một tập, kiểm chứng trên tập khác.

Hiện recall và precision vận hành dùng một ngưỡng conf 0,25 cho mọi box. Người nhỏ thường có conf thấp hơn người to,
nên một ngưỡng chung có thể bỏ người nhỏ đúng trong khi giữ box to sai. Ở đây mỗi nhóm cỡ của **box dự đoán** (cạnh
ngắn < 8, 8–16, 16–32, > 32 px; lúc chạy chỉ biết cỡ box, không biết cỡ nhãn) có ngưỡng riêng.

Chọn (--fit, ví dụ VisDrone val): tối đa recall với điều kiện precision chung không thấp hơn precision của ngưỡng
chung --base-conf trên chính tập đó, nghĩa là bắt thêm người mà không thêm tỉ lệ báo nhầm. Vét cạn mọi tổ hợp trên
lưới --grid (fit_thresholds), rồi so khớp lại chính xác: bỏ box theo ngưỡng riêng không phải là cắt một đoạn đầu danh
sách theo conf, nên kết quả so khớp có thể khác chút ít so với lần so khớp chung dùng để tìm.

Kiểm chứng (--test, một hay nhiều tập): recall và precision của ngưỡng chung và ngưỡng theo cỡ, recall theo nhóm cỡ
nhãn, hiệu số bằng bootstrap cặp theo ảnh hoặc theo video (--cluster-pattern của từng tập). Không chọn gì trên tập test.

Ví dụ:
    .venv/bin/python eval/conf_by_size.py \\
        --fit runs/visdrone/E2c data/processed/visdrone/images/val data/processed/visdrone/labels/val \\
        --fit-ignore data/processed/visdrone/ignore/val \\
        --test visdrone-testdev runs/visdrone-testdev/E2c data/processed/visdrone/images/test-dev \\
               data/processed/visdrone/labels/test-dev '^(\\d+)_' data/processed/visdrone/ignore/test-dev \\
        --test sds_det runs/sds_det/E2c_tiled_px10 data/processed/sds_det/images/val data/processed/sds_det/labels/val \\
               '^(v\\d+)_' - \\
        --output runs/conf_by_size
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from eval.eval_by_size import image_clusters, load_ground_truth
from eval.metrics import SIZE_RANGES, _draw_counts, _short_side, ioa_matrix, iou_matrix
from eval.report import SIZE_BIN_EDGES, SIZE_BIN_LABELS
from shared.config import parse_args_with_config
from shared.provenance import write_run_config

GRID = [round(0.05 * k, 2) for k in range(1, 13)]  # 0,05 … 0,60


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fit", nargs=3, required=True, metavar=("RUN", "IMAGES", "LABELS"), help="Tập chọn ngưỡng")
    parser.add_argument("--fit-ignore", type=Path, default=None, help="Vùng bỏ qua của tập chọn ngưỡng")
    parser.add_argument("--fit-cluster-pattern", default=None, help="Regex mã video của tập chọn ngưỡng (chỉ để ghi)")
    parser.add_argument("--test", nargs=6, action="append", default=[],
                        metavar=("NAME", "RUN", "IMAGES", "LABELS", "CLUSTER", "IGNORE"),
                        help="Tập kiểm chứng; CLUSTER và IGNORE là '-' nếu không có")
    parser.add_argument("--base-conf", type=float, default=0.25, help="Ngưỡng chung để so (quy ước recall vận hành)")
    parser.add_argument("--grid", type=float, nargs="+", default=GRID, help="Các ngưỡng được thử cho mỗi nhóm cỡ")
    parser.add_argument("--iou", type=float, default=0.5, help="Ngưỡng IoU")
    parser.add_argument("--bootstrap", type=int, default=1000, help="Số lần bootstrap")
    parser.add_argument("--output", type=Path, required=True, help="Thư mục kết quả")
    return parse_args_with_config(parser)


def size_bin(sides: np.ndarray) -> np.ndarray:
    """Chỉ số nhóm cỡ (0: < 8, 1: 8–16, 2: 16–32, 3: > 32) của từng cạnh ngắn."""
    return np.clip(np.searchsorted(np.asarray(SIZE_BIN_EDGES[1:-1]), sides, side="right"), 0, len(SIZE_BIN_LABELS) - 1)


@dataclass
class ImageData:
    """Dự đoán (đã sắp conf giảm dần) và nhãn của một ảnh, kèm IoU tính sẵn."""

    confs: np.ndarray
    pred_bin: np.ndarray
    ious: np.ndarray       # (số dự đoán, số nhãn)
    in_ignored: np.ndarray
    gt_bin: np.ndarray


def prepare(boxes: pd.DataFrame, ground_truth: dict, min_conf: float) -> list[ImageData]:
    """Mỗi ảnh một ImageData; bỏ trước các dự đoán dưới min_conf (ngưỡng nhỏ nhất có thể dùng)."""
    by_image = {name: g for name, g in boxes[boxes["conf"] >= min_conf].groupby("image")}
    empty = boxes.iloc[0:0]
    out = []
    for name, (gt, ignore) in ground_truth.items():
        p = by_image.get(name, empty).sort_values("conf", ascending=False, kind="stable")
        pb = p[["x1", "y1", "x2", "y2"]].to_numpy(dtype=float).reshape(-1, 4)
        in_ignored = (ioa_matrix(pb, ignore).max(axis=1) >= 0.5) if ignore is not None and len(ignore) else np.zeros(len(pb), bool)
        out.append(ImageData(p["conf"].to_numpy(dtype=float), size_bin(_short_side(pb)), iou_matrix(pb, gt), in_ignored,
                             size_bin(_short_side(gt))))
    return out


def count(images: list[ImageData], thresholds: np.ndarray, iou_thr: float) -> np.ndarray:
    """Mỗi ảnh một dòng: [TP, số dự đoán tính, số nhãn, TP theo 4 nhóm cỡ nhãn…, số nhãn theo 4 nhóm…].

    So khớp tham lam theo conf giảm dần như eval.metrics.match_image (nhóm "all"): dự đoán sai nằm trong vùng bỏ qua
    không bị tính.
    """
    nb = len(SIZE_BIN_LABELS)
    rows = np.zeros((len(images), 3 + 2 * nb))
    for k, im in enumerate(images):
        keep = im.confs >= thresholds[im.pred_bin]
        taken = np.zeros(im.ious.shape[1], dtype=bool)
        tp = n_pred = 0
        tp_bin = np.zeros(nb)
        for i in np.flatnonzero(keep):
            cand = np.flatnonzero((im.ious[i] >= iou_thr) & ~taken)
            if len(cand):
                j = cand[np.argmax(im.ious[i, cand])]
                taken[j] = True
                tp += 1
                n_pred += 1
                tp_bin[im.gt_bin[j]] += 1
            elif not im.in_ignored[i]:
                n_pred += 1
        rows[k, :3] = (tp, n_pred, im.ious.shape[1])
        rows[k, 3:3 + nb] = tp_bin
        rows[k, 3 + nb:] = np.bincount(im.gt_bin, minlength=nb)
    return rows


def recall_precision(total: np.ndarray) -> tuple[float, float]:
    """(recall, precision) từ tổng các dòng của count()."""
    tp, n_pred, n_gt = total[:3]
    return (tp / n_gt if n_gt else float("nan"), tp / n_pred if n_pred else float("nan"))


def prediction_status(images: list[ImageData], min_conf: float, iou_thr: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """So khớp một lần với mọi dự đoán từ min_conf: (nhóm cỡ, conf, trạng thái 1 đúng / 0 sai / -1 trong vùng bỏ qua)."""
    bins, confs, status = [], [], []
    for im in images:
        taken = np.zeros(im.ious.shape[1], dtype=bool)
        for i in np.flatnonzero(im.confs >= min_conf):
            cand = np.flatnonzero((im.ious[i] >= iou_thr) & ~taken)
            if len(cand):
                taken[cand[np.argmax(im.ious[i, cand])]] = True
                st = 1
            else:
                st = -1 if im.in_ignored[i] else 0
            bins.append(im.pred_bin[i])
            confs.append(im.confs[i])
            status.append(st)
    return np.asarray(bins, dtype=int), np.asarray(confs), np.asarray(status)


def fit_thresholds(images: list[ImageData], base_conf: float, grid: list[float], iou_thr: float,
                   n_verify: int = 200) -> tuple[np.ndarray, list[dict]]:
    """Tối đa recall với precision ≥ precision của ngưỡng chung (cả hai tính chính xác bằng count()).

    Vét cạn mọi tổ hợp ngưỡng trên lưới cho bốn nhóm cỡ, dùng số đúng, số dự đoán của từng nhóm theo một lần so khớp
    chung (cộng được giữa các nhóm); rồi so khớp lại chính xác các tổ hợp tốt nhất theo thứ tự recall giảm dần và lấy
    tổ hợp đầu tiên thoả điều kiện precision. Tìm từng nhóm một không đủ: hạ ngưỡng một nhóm luôn làm precision giảm,
    phải nâng ngưỡng nhóm khác cùng lúc.
    """
    nb = len(SIZE_BIN_LABELS)
    base = np.full(nb, base_conf)
    n_gt = sum(im.ious.shape[1] for im in images)
    base_recall, base_precision = recall_precision(count(images, base, iou_thr).sum(axis=0))
    grid = sorted(set(grid) | {base_conf})
    bins, confs, status = prediction_status(images, min(grid), iou_thr)
    # tp[b, k], npred[b, k]: số đúng và số dự đoán được tính của nhóm b ở ngưỡng grid[k]
    tp = np.array([[np.sum((bins == b) & (confs >= t) & (status == 1)) for t in grid] for b in range(nb)])
    npred = np.array([[np.sum((bins == b) & (confs >= t) & (status >= 0)) for t in grid] for b in range(nb)])
    idx = np.stack(np.meshgrid(*[np.arange(len(grid))] * nb, indexing="ij"), -1).reshape(-1, nb)
    tp_sum = tp[np.arange(nb), idx].sum(axis=1)
    np_sum = npred[np.arange(nb), idx].sum(axis=1)
    approx_ok = tp_sum >= base_precision * np_sum - 1e-9
    # recall giảm dần; cùng recall thì ít dự đoán hơn (precision cao hơn) trước
    order = [i for i in np.lexsort((np_sum, -tp_sum)) if approx_ok[i]][:n_verify]
    log = [{"step": "ngưỡng chung", "thresholds": base.tolist(), "recall": base_recall, "precision": base_precision}]
    best = base
    for i in order:
        trial = np.array([grid[k] for k in idx[i]])
        r, p = recall_precision(count(images, trial, iou_thr).sum(axis=0))
        if p >= base_precision and r > base_recall:
            best = trial
            log.append({"step": "vét cạn", "thresholds": trial.tolist(), "recall": r, "precision": p,
                        "approx_recall": float(tp_sum[i] / n_gt)})
            break
    return best, log


def paired_bootstrap_counts(a: np.ndarray, b: np.ndarray, clusters: np.ndarray | None, n_boot: int,
                            seed: int = 0) -> dict[str, tuple[float, float, float]]:
    """Hiệu B − A của recall, precision và recall từng nhóm cỡ nhãn: (hiệu, cận dưới, cận trên) bootstrap cặp 95%."""
    nb = len(SIZE_BIN_LABELS)

    def metrics(total: np.ndarray) -> np.ndarray:
        r, p = recall_precision(total)
        per_bin = [total[3 + k] / total[3 + nb + k] if total[3 + nb + k] else np.nan for k in range(nb)]
        return np.array([r, p, *per_bin])

    names = ["recall", "precision", *[f"recall_{label}" for label in SIZE_BIN_LABELS]]
    point = metrics(b.sum(axis=0)) - metrics(a.sum(axis=0))
    rng = np.random.default_rng(seed)
    diffs = np.empty((n_boot, len(names)))
    for i in range(n_boot):
        w = _draw_counts(rng, len(a), clusters)
        diffs[i] = metrics(w @ b) - metrics(w @ a)
    lo, hi = np.nanpercentile(diffs, [2.5, 97.5], axis=0)
    return {n: (float(point[k]), float(lo[k]), float(hi[k])) for k, n in enumerate(names)}


def load(run: Path, images: Path, labels: Path, ignore: Path | None) -> tuple[pd.DataFrame, dict, list[str]]:
    """boxes.csv, nhãn và danh sách ảnh của một lần chạy."""
    names = pd.read_csv(run / "per_image.csv")["image"].tolist()
    return pd.read_csv(run / "boxes.csv"), load_ground_truth(names, images, labels, [0], ignore), names


def main() -> None:
    """Chọn ngưỡng trên tập --fit, kiểm chứng trên từng tập --test, ghi JSON và CSV."""
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    min_conf = min(min(args.grid), args.base_conf)
    run, images, labels = map(Path, args.fit)
    boxes, gt, _ = load(run, images, labels, args.fit_ignore)
    thresholds, log = fit_thresholds(prepare(boxes, gt, min_conf), args.base_conf, args.grid, args.iou)
    chosen = dict(zip(SIZE_BIN_LABELS, thresholds.tolist()))
    print(f"Ngưỡng chọn trên {run}: {chosen}")
    for step in log:
        print(f"  {step['step']}: {step['thresholds']} → recall {step['recall']:.4f}, precision {step['precision']:.4f}")
    (args.output / "thresholds.json").write_text(json.dumps({"fit": str(run), "base_conf": args.base_conf, "iou": args.iou,
                                                              "thresholds": chosen, "log": log}, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = []
    for name, run_s, images_s, labels_s, cluster, ignore in args.test:
        boxes, gt, names = load(Path(run_s), Path(images_s), Path(labels_s), None if ignore == "-" else Path(ignore))
        data = prepare(boxes, gt, min_conf)
        a = count(data, np.full(len(SIZE_BIN_LABELS), args.base_conf), args.iou)
        b = count(data, thresholds, args.iou)
        clusters = image_clusters(list(gt), None if cluster == "-" else cluster)
        diff = paired_bootstrap_counts(a, b, clusters, args.bootstrap)
        ra, pa = recall_precision(a.sum(axis=0))
        rb, pb = recall_precision(b.sum(axis=0))
        nb = len(SIZE_BIN_LABELS)
        base_values = {"recall": ra, "precision": pa}
        size_values = {"recall": rb, "precision": pb}
        for k, label in enumerate(SIZE_BIN_LABELS):
            ta, tb = a.sum(axis=0), b.sum(axis=0)
            base_values[f"recall_{label}"] = ta[3 + k] / ta[3 + nb + k] if ta[3 + nb + k] else float("nan")
            size_values[f"recall_{label}"] = tb[3 + k] / tb[3 + nb + k] if tb[3 + nb + k] else float("nan")
        for metric, (d, lo, hi) in diff.items():
            rows.append({"dataset": name, "metric": metric, "base": round(base_values[metric], 4),
                         "by_size": round(size_values[metric], 4), "diff": round(d, 4), "diff_lo": round(lo, 4),
                         "diff_hi": round(hi, 4), "significant": bool(lo > 0 or hi < 0),
                         "n_pred_base": int(a[:, 1].sum()), "n_pred_by_size": int(b[:, 1].sum())})
        print(f"{name}: recall {ra:.4f} → {rb:.4f}, precision {pa:.4f} → {pb:.4f}, "
              f"dự đoán giữ lại {int(a[:, 1].sum())} → {int(b[:, 1].sum())}")
    with (args.output / "results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["dataset"])
        writer.writeheader()
        writer.writerows(rows)
    write_run_config(args.output, "eval/conf_by_size.py", None, None, vars(args))
    print(f"Lưu tại: {args.output}")


if __name__ == "__main__":
    main()
