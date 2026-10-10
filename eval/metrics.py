"""So khớp box dự đoán với nhãn và tính AP, recall, precision theo nhóm kích thước."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from eval.report import SIZE_BIN_EDGES, SIZE_BIN_LABELS

ALL_SIZES = "all"
# Mỗi nhóm kích thước là một khoảng [cận dưới, cận trên) của cạnh ngắn, tính bằng pixel.
SIZE_RANGES: dict[str, tuple[float, float]] = {ALL_SIZES: (0.0, float("inf"))}
SIZE_RANGES.update({label: (lo, hi) for label, lo, hi in zip(SIZE_BIN_LABELS, SIZE_BIN_EDGES, SIZE_BIN_EDGES[1:])})


@dataclass
class MatchResult:
    """Kết quả so khớp của một cấu hình trong một nhóm kích thước, đã sắp theo conf giảm dần."""

    confs: np.ndarray
    is_tp: np.ndarray
    n_gt: int


def load_yolo_labels(label_path: Path, width: int, height: int, classes: Sequence[int]) -> np.ndarray:
    """Đọc file nhãn YOLO (class cx cy w h, chuẩn hoá) và trả về mảng xyxy theo pixel của các lớp được chọn."""
    boxes = []
    if label_path.is_file():
        for line in label_path.read_text().splitlines():
            parts = line.split()
            if len(parts) < 5 or int(float(parts[0])) not in classes:
                continue
            cx, cy, w, h = (float(v) for v in parts[1:5])
            boxes.append(
                [(cx - w / 2) * width, (cy - h / 2) * height, (cx + w / 2) * width, (cy + h / 2) * height]
            )
    return np.asarray(boxes, dtype=float).reshape(-1, 4)


def iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Ma trận IoU giữa hai tập box xyxy, kích thước (len(a), len(b))."""
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    union = area_a[:, None] + area_b[None, :] - inter
    return np.where(union > 0, inter / np.maximum(union, 1e-12), 0.0)


def ioa_matrix(a: np.ndarray, regions: np.ndarray) -> np.ndarray:
    """Tỉ lệ diện tích của mỗi box trong `a` nằm trong từng vùng của `regions`, kích thước (len(a), len(regions))."""
    if len(a) == 0 or len(regions) == 0:
        return np.zeros((len(a), len(regions)))
    x1 = np.maximum(a[:, None, 0], regions[None, :, 0])
    y1 = np.maximum(a[:, None, 1], regions[None, :, 1])
    x2 = np.minimum(a[:, None, 2], regions[None, :, 2])
    y2 = np.minimum(a[:, None, 3], regions[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    return inter / np.maximum(area_a[:, None], 1e-12)


def _short_side(boxes: np.ndarray) -> np.ndarray:
    """Cạnh ngắn của từng box xyxy, làm tròn 0,01 px.

    Nhãn YOLO lưu toạ độ chuẩn hoá 6 chữ số, nên box rộng đúng 8 px có thể đọc lại thành 7,9999 px và rơi
    sang nhóm "<8". Làm tròn để box nằm đúng nhóm như khi đo trên nhãn gốc.
    """
    return np.round(np.minimum(boxes[:, 2] - boxes[:, 0], boxes[:, 3] - boxes[:, 1]), 2)


def match_image(
    pred_boxes: np.ndarray,
    pred_confs: np.ndarray,
    gt_boxes: np.ndarray,
    size_range: tuple[float, float],
    iou_thr: float,
    ignore_regions: np.ndarray | None = None,
    ioa_thr: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, int]:
    """So khớp tham lam theo conf giảm dần trên một ảnh, theo quy ước của COCO cho từng nhóm kích thước.

    Nhãn ngoài nhóm được coi là "bỏ qua": dự đoán khớp với chúng không bị tính là sai. Dự đoán không khớp
    nhãn nào và bản thân nằm ngoài nhóm cũng được bỏ qua. Trả về (conf, is_tp) của các dự đoán được tính
    và số nhãn thuộc nhóm.

    Dự đoán không khớp nhãn nào mà có ít nhất `ioa_thr` diện tích nằm trong một vùng bỏ qua (ví dụ vùng
    "ignored" của VisDrone) cũng không bị tính là sai.
    """
    lo, hi = size_range
    gt_side = _short_side(gt_boxes)
    gt_in_range = (gt_side >= lo) & (gt_side < hi)
    pred_side = _short_side(pred_boxes)
    pred_in_range = (pred_side >= lo) & (pred_side < hi)

    order = np.argsort(-pred_confs)
    ious = iou_matrix(pred_boxes, gt_boxes)
    in_ignored = (
        ioa_matrix(pred_boxes, ignore_regions).max(axis=1) >= ioa_thr
        if ignore_regions is not None and len(ignore_regions)
        else np.zeros(len(pred_boxes), dtype=bool)
    )
    gt_taken = np.zeros(len(gt_boxes), dtype=bool)
    confs: list[float] = []
    is_tp: list[bool] = []
    for i in order:
        candidates = np.where((ious[i] >= iou_thr) & ~gt_taken)[0]
        if len(candidates):
            # Ưu tiên nhãn thuộc nhóm, sau đó mới tới IoU cao nhất.
            best = max(candidates, key=lambda j: (gt_in_range[j], ious[i, j]))
            gt_taken[best] = True
            if gt_in_range[best]:
                confs.append(float(pred_confs[i]))
                is_tp.append(True)
        elif pred_in_range[i] and not in_ignored[i]:
            confs.append(float(pred_confs[i]))
            is_tp.append(False)
    return np.asarray(confs), np.asarray(is_tp, dtype=bool), int(gt_in_range.sum())


def merge_matches(parts: list[tuple[np.ndarray, np.ndarray, int]]) -> MatchResult:
    """Gộp kết quả so khớp của nhiều ảnh và sắp theo conf giảm dần."""
    confs = np.concatenate([p[0] for p in parts]) if parts else np.zeros(0)
    is_tp = np.concatenate([p[1] for p in parts]) if parts else np.zeros(0, dtype=bool)
    order = np.argsort(-confs, kind="stable")
    return MatchResult(confs[order], is_tp[order], sum(p[2] for p in parts))


def pr_curve(match: MatchResult) -> tuple[np.ndarray, np.ndarray]:
    """Đường precision-recall khi hạ dần ngưỡng conf."""
    tp = np.cumsum(match.is_tp)
    fp = np.cumsum(~match.is_tp)
    recall = tp / match.n_gt if match.n_gt else np.zeros(len(tp))
    precision = tp / np.maximum(tp + fp, 1)
    return recall, precision


def average_precision(match: MatchResult) -> float:
    """AP nội suy 101 điểm như COCO; trả về NaN nếu nhóm không có nhãn nào."""
    if match.n_gt == 0:
        return float("nan")
    recall, precision = pr_curve(match)
    if len(recall) == 0:
        return 0.0
    # Bao lồi precision: tại mỗi mức recall lấy precision tốt nhất ở các mức recall lớn hơn hoặc bằng.
    envelope = np.maximum.accumulate(precision[::-1])[::-1]
    grid = np.linspace(0, 1, 101)
    idx = np.searchsorted(recall, grid, side="left")
    reached = idx < len(envelope)
    values = np.zeros(len(grid))
    values[reached] = envelope[idx[reached]]
    return float(values.mean())


def operating_point(match: MatchResult, conf_thr: float) -> tuple[float, float]:
    """Recall và precision khi chỉ giữ các dự đoán có conf từ ngưỡng trở lên."""
    keep = match.confs >= conf_thr
    tp = int(match.is_tp[keep].sum())
    n_pred = int(keep.sum())
    recall = tp / match.n_gt if match.n_gt else float("nan")
    precision = tp / n_pred if n_pred else float("nan")
    return recall, precision
