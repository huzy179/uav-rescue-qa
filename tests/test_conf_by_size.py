from __future__ import annotations

import numpy as np

from eval.conf_by_size import ImageData, count, fit_thresholds, recall_precision, size_bin


def _image(confs: list[float], sides: list[float], tp: list[bool]) -> ImageData:
    """Ảnh giả: dự đoán i khớp nhãn i nếu tp[i] (IoU 0,9), không khớp gì nếu không."""
    n_gt = sum(tp)
    ious = np.zeros((len(confs), n_gt))
    j = 0
    for i, t in enumerate(tp):
        if t:
            ious[i, j] = 0.9
            j += 1
    gt_sides = [s for s, t in zip(sides, tp) if t]
    return ImageData(np.asarray(confs), size_bin(np.asarray(sides)), ious, np.zeros(len(confs), bool), size_bin(np.asarray(gt_sides)))


def test_size_bin_edges() -> None:
    assert size_bin(np.array([0.0, 7.99, 8.0, 15.99, 16.0, 32.0, 500.0])).tolist() == [0, 0, 1, 1, 2, 3, 3]


def test_count_respects_per_bin_thresholds() -> None:
    im = _image([0.9, 0.2, 0.2], [5, 5, 40], [True, True, False])
    rows = count([im], np.array([0.25, 0.25, 0.25, 0.25]), 0.5)
    assert recall_precision(rows.sum(axis=0)) == (0.5, 1.0)
    rows = count([im], np.array([0.1, 0.25, 0.25, 0.25]), 0.5)  # hạ ngưỡng người nhỏ: thêm một đúng
    assert recall_precision(rows.sum(axis=0)) == (1.0, 1.0)


def test_fit_trades_thresholds_between_bins() -> None:
    # Người nhỏ đúng có conf 0,2; người to sai có conf 0,3. Ngưỡng chung 0,25: recall 1/2, precision 1/2.
    # Hạ ngưỡng nhỏ và nâng ngưỡng to cùng lúc mới tăng được recall mà precision không giảm.
    im = _image([0.9, 0.2, 0.3], [40, 5, 40], [True, True, False])
    thresholds, log = fit_thresholds([im], 0.25, [0.1, 0.25, 0.35], 0.5)
    r, p = recall_precision(count([im], thresholds, 0.5).sum(axis=0))
    assert (r, p) == (1.0, 1.0)
    assert thresholds[0] <= 0.2 and thresholds[3] > 0.3
    assert log[0]["recall"] == 0.5
