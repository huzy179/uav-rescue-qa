"""Phân tích lỗi cho giao diện: từng ảnh có bao nhiêu người được thấy, bị bỏ sót, bao nhiêu báo nhầm, ở đâu.

So khớp giống eval/metrics.match_image ở một ngưỡng conf (điểm vận hành): dự đoán theo conf giảm dần nhận nhãn còn
trống có IoU cao nhất ≥ iou_thr; dự đoán không khớp mà nằm ít nhất một nửa trong vùng bỏ qua thì không tính là sai.
Lọc theo nhóm kích thước theo cạnh ngắn của nhãn (người bị bỏ sót) hoặc của dự đoán (báo nhầm), như eval_by_size.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from PIL import Image

from eval.metrics import SIZE_RANGES, _short_side, ioa_matrix, iou_matrix, load_yolo_labels
from eval.splits import image_paths

CONFIG = Path("configs/console.yaml")


@dataclass(frozen=True)
class Dataset:
    name: str
    title: str
    runs: Path
    images: Path
    labels: Path
    ignore: Path | None = None
    tags: Path | None = None
    require_lock: Path | None = None

    @property
    def available(self) -> bool:
        """Có ảnh, và với tập test lũ thì đã khoá."""
        return self.images.is_dir() and (self.require_lock is None or self.require_lock.is_file())


@dataclass
class ImageErrors:
    """Kết quả so khớp của một ảnh ở một ngưỡng; chỉ số là thứ tự trong gts và preds."""

    tp: list[tuple[int, int]] = field(default_factory=list)  # (dự đoán, nhãn)
    fp: list[int] = field(default_factory=list)
    fn: list[int] = field(default_factory=list)
    ignored: list[int] = field(default_factory=list)  # dự đoán không khớp nằm trong vùng bỏ qua


def load_datasets(path: Path = CONFIG) -> dict[str, Dataset]:
    """Đọc danh sách tập từ configs/console.yaml."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = {}
    for d in raw["datasets"]:
        out[d["name"]] = Dataset(
            d["name"], d.get("title", d["name"]), Path(d["runs"]), Path(d["images"]), Path(d["labels"]),
            *(Path(d[k]) if d.get(k) else None for k in ("ignore", "tags", "require_lock")),
        )
    return out


def match_errors(
    preds: np.ndarray, confs: np.ndarray, gts: np.ndarray, iou_thr: float, ignore: np.ndarray | None = None,
    ioa_thr: float = 0.5, prefer: np.ndarray | None = None,
) -> ImageErrors:
    """So khớp tham lam theo conf giảm dần; preds, confs đã lọc theo ngưỡng conf.

    prefer (mặt nạ theo gts): giữa các nhãn đủ IoU, ưu tiên nhãn thuộc nhóm kích thước đang xét rồi mới tới IoU cao
    nhất, đúng như eval/metrics.match_image, để số theo nhóm khớp bảng eval_by_size.
    """
    ious = iou_matrix(preds, gts)
    in_ignored = (
        ioa_matrix(preds, ignore).max(axis=1) >= ioa_thr if ignore is not None and len(ignore) else np.zeros(len(preds), bool)
    )
    taken = np.zeros(len(gts), dtype=bool)
    result = ImageErrors()
    for i in np.argsort(-confs, kind="stable"):
        candidates = np.where((ious[i] >= iou_thr) & ~taken)[0] if len(gts) else np.array([], dtype=int)
        if len(candidates):
            if prefer is None:
                j = int(candidates[np.argmax(ious[i, candidates])])
            else:
                j = int(max(candidates, key=lambda c: (bool(prefer[c]), ious[i, c])))
            taken[j] = True
            result.tp.append((int(i), j))
        elif in_ignored[i]:
            result.ignored.append(int(i))
        else:
            result.fp.append(int(i))
    result.fn = [int(j) for j in np.where(~taken)[0]]
    return result


def short_side(boxes: np.ndarray) -> np.ndarray:
    """Cạnh ngắn (px) của từng box xyxy, làm tròn như eval/metrics (người rộng đúng 8 px đọc lại thành 7,9999 px)."""
    return _short_side(boxes) if len(boxes) else np.zeros(0)


def list_runs(dataset: Dataset) -> list[dict[str, Any]]:
    """Các lần chạy có boxes.csv trong thư mục kết quả của tập, kèm các cấu hình (method, imgsz) trong đó."""
    if not dataset.runs.is_dir():
        return []
    runs = []
    for boxes in sorted(dataset.runs.glob("*/boxes.csv")):
        configs = pd.read_csv(boxes, usecols=["method", "imgsz"]).drop_duplicates()
        runs.append({
            "name": boxes.parent.name,
            "configs": [f"{m} imgsz={i}" for m, i in configs.itertuples(index=False)],
        })
    return runs


@lru_cache(maxsize=8)
def _ground_truth(images: Path, labels: Path, ignore: Path | None) -> dict[str, tuple[np.ndarray, np.ndarray | None, tuple[int, int]]]:
    """Nhãn và vùng bỏ qua (pixel) của mọi ảnh trong thư mục, kèm kích thước ảnh."""
    out = {}
    for path in image_paths(images):
        with Image.open(path) as img:
            width, height = img.size
        gts = load_yolo_labels(labels / f"{path.stem}.txt", width, height, [0])
        ign = load_yolo_labels(ignore / f"{path.stem}.txt", width, height, [0]) if ignore is not None else None
        out[path.name] = (gts, ign, (width, height))
    return out


@lru_cache(maxsize=16)
def _predictions(boxes_csv: Path, config: str, mtime: float) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Dự đoán của một cấu hình trong boxes.csv, theo ảnh; mtime chỉ để làm mới bộ nhớ đệm khi file đổi."""
    df = pd.read_csv(boxes_csv)
    method, imgsz = config.split(" imgsz=")
    df = df[(df["method"] == method) & (df["imgsz"].astype(str) == imgsz)]
    return {
        name: (g[["x1", "y1", "x2", "y2"]].to_numpy(float), g["conf"].to_numpy(float))
        for name, g in df.groupby("image")
    }


def _tags(dataset: Dataset) -> dict[str, list[str]]:
    """Thẻ của từng ảnh (tập lũ: tags_<split>.csv, cột 0/1)."""
    if dataset.tags is None or not dataset.tags.is_file():
        return {}
    df = pd.read_csv(dataset.tags)
    return {row["image"]: [c for c in df.columns if c != "image" and row[c] == 1] for _, row in df.iterrows()}


def image_errors(
    dataset: Dataset, run: str, config: str, image: str, iou_thr: float, conf_thr: float,
    size_range: tuple[float, float] | None = None,
) -> tuple[ImageErrors, np.ndarray, np.ndarray, np.ndarray, np.ndarray | None, tuple[int, int]]:
    """So khớp một ảnh; trả (lỗi, preds, confs, gts, vùng bỏ qua, kích thước). size_range: ưu tiên nhãn trong nhóm."""
    boxes_csv = dataset.runs / run / "boxes.csv"
    preds_by_image = _predictions(boxes_csv, config, boxes_csv.stat().st_mtime)
    gts, ignore, size = _ground_truth(dataset.images, dataset.labels, dataset.ignore)[image]
    preds, confs = preds_by_image.get(image, (np.zeros((0, 4)), np.zeros(0)))
    keep = confs >= conf_thr
    preds, confs = preds[keep], confs[keep]
    prefer = None
    if size_range is not None:
        side = short_side(gts)
        prefer = (side >= size_range[0]) & (side < size_range[1])
    return match_errors(preds, confs, gts, iou_thr, ignore, prefer=prefer), preds, confs, gts, ignore, size


def summarize(
    dataset: Dataset, run: str, config: str, iou_thr: float, conf_thr: float, size: str = "all", tag: str | None = None
) -> dict[str, Any]:
    """Số người thấy, bỏ sót, báo nhầm của từng ảnh trong nhóm kích thước; và tổng của cả tập."""
    lo, hi = SIZE_RANGES[size]
    tags = _tags(dataset)
    rows = []
    for image in _ground_truth(dataset.images, dataset.labels, dataset.ignore):
        if tag is not None and tag not in tags.get(image, []):
            continue
        err, preds, _, gts, _, _ = image_errors(dataset, run, config, image, iou_thr, conf_thr, (lo, hi))
        gt_side, pred_side = short_side(gts), short_side(preds)
        in_gt = (gt_side >= lo) & (gt_side < hi)
        in_pred = (pred_side >= lo) & (pred_side < hi)
        rows.append({
            "image": image,
            "n_gt": int(in_gt.sum()),
            "tp": sum(bool(in_gt[j]) for _, j in err.tp),
            "fn": sum(bool(in_gt[j]) for j in err.fn),
            "fp": sum(bool(in_pred[i]) for i in err.fp),
            "tags": tags.get(image, []),
        })
    n_gt, tp, fp = (sum(r[k] for r in rows) for k in ("n_gt", "tp", "fp"))
    return {
        "images": rows,
        "total": {
            "n_images": len(rows), "n_gt": n_gt, "tp": tp, "fn": n_gt - tp, "fp": fp,
            "recall": round(tp / n_gt, 4) if n_gt else None,
            "precision": round(tp / (tp + fp), 4) if tp + fp else None,
        },
        "tags": sorted({t for ts in tags.values() for t in ts}),
    }
