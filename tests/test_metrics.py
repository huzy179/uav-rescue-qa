"""Kiểm tra so khớp và AP theo nhóm kích thước bằng các ví dụ tính tay."""

import numpy as np
import pytest

from eval.metrics import SIZE_RANGES, average_precision, bootstrap_ci, match_image, merge_matches, operating_point

GT = np.array([[0, 0, 10, 10], [100, 100, 140, 140.0]])  # một người 10 px, một người 40 px
PREDS = np.array([[100, 100, 140, 141], [300, 300, 320, 320], [0, 0, 10, 11.0]])
CONFS = np.array([0.9, 0.8, 0.7])


def test_ap_all_sizes_matches_hand_computation() -> None:
    """Đúng, sai, đúng: AP 101 điểm = (51 × 1 + 50 × 2/3) / 101."""
    match = merge_matches([match_image(PREDS, CONFS, GT, SIZE_RANGES["all"], 0.5)])
    assert match.is_tp.tolist() == [True, False, True]
    assert average_precision(match) == pytest.approx((51 + 50 * 2 / 3) / 101)


def test_size_bin_ignores_out_of_bin_ground_truth() -> None:
    """Trong nhóm 8–16 px chỉ còn nhãn 10 px; dự đoán khớp nhãn 40 px không bị tính là sai."""
    match = merge_matches([match_image(PREDS, CONFS, GT, SIZE_RANGES["8-16"], 0.5)])
    assert match.n_gt == 1
    assert match.is_tp.tolist() == [True]
    assert operating_point(match, 0.75) == (0.0, pytest.approx(float("nan"), nan_ok=True))


def test_prediction_inside_ignore_region_is_not_false_positive() -> None:
    """Dự đoán sai nằm trọn trong vùng bỏ qua bị loại khỏi phép tính."""
    ignore = np.array([[290, 290, 330, 330.0]])
    match = merge_matches([match_image(PREDS, CONFS, GT, SIZE_RANGES["all"], 0.5, ignore)])
    assert match.is_tp.tolist() == [True, True]
    assert average_precision(match) == pytest.approx(1.0)


def test_integer_box_on_bin_edge_stays_in_its_bin() -> None:
    """Box rộng đúng 8 px, đọc lại từ nhãn chuẩn hoá thành 7,99999 px, vẫn thuộc nhóm 8–16 px."""
    gt = np.array([[100.000004, 50.0, 107.999998, 60.0]])
    match = merge_matches([match_image(np.zeros((0, 4)), np.zeros(0), gt, SIZE_RANGES["8-16"], 0.5)])
    assert match.n_gt == 1


def test_bootstrap_ci_collapses_on_identical_images_and_brackets_the_estimate() -> None:
    """Mọi ảnh giống nhau thì mẫu nào cũng cho cùng AP; ảnh khác nhau thì khoảng tin cậy phải chứa giá trị ước lượng."""
    part = match_image(PREDS, CONFS, GT, SIZE_RANGES["all"], 0.5)
    same = bootstrap_ci([part] * 5, [average_precision], n_boot=50)
    assert same[0] == pytest.approx([average_precision(merge_matches([part]))] * 2)

    miss = match_image(np.zeros((0, 4)), np.zeros(0), GT, SIZE_RANGES["all"], 0.5)  # ảnh bỏ sót cả hai người
    parts = [part] * 5 + [miss] * 5
    lo, hi = bootstrap_ci(parts, [lambda m: operating_point(m, 0.25)[0]], n_boot=200)[0]
    assert lo < operating_point(merge_matches(parts), 0.25)[0] < hi


def _one_gt_per_image(hits: list[bool]) -> list[tuple[np.ndarray, np.ndarray, int]]:
    """Mỗi ảnh một nhãn; hit thì có một dự đoán đúng conf 0,9, không thì không có dự đoán."""
    return [(np.array([0.9]), np.array([True]), 1) if hit else (np.zeros(0), np.zeros(0, dtype=bool), 1) for hit in hits]


def test_paired_bootstrap_identical_configs() -> None:
    from eval.metrics import paired_bootstrap

    parts = _one_gt_per_image([True] * 10 + [False] * 10)
    d = paired_bootstrap(parts, parts, lambda m: operating_point(m, 0.25)[0], n_boot=200)
    assert (d.diff, d.lo, d.hi, d.p_value) == (0.0, 0.0, 0.0, 1.0)


def test_paired_bootstrap_detects_consistent_gain() -> None:
    """B bắt thêm 10/20 người mà A bỏ sót: hiệu recall 0,5, khoảng tin cậy không chứa 0."""
    from eval.metrics import paired_bootstrap

    a = _one_gt_per_image([True] * 10 + [False] * 10)
    b = _one_gt_per_image([True] * 20)
    d = paired_bootstrap(a, b, lambda m: operating_point(m, 0.25)[0], n_boot=500)
    assert d.diff == pytest.approx(0.5)
    assert d.lo > 0 and d.p_value < 0.01
    with pytest.raises(ValueError):
        paired_bootstrap(a, b[:5], average_precision)


def test_cluster_bootstrap_is_wider_when_images_correlated() -> None:
    """20 ảnh từ 2 video: video 1 bắt hết, video 2 sót hết. Theo ảnh thì khoảng tin cậy hẹp giả; theo video thì
    chỉ có 2 đơn vị độc lập nên recall có thể là 0, 0,5 hoặc 1."""
    from eval.metrics import bootstrap_ci

    parts = _one_gt_per_image([True] * 10 + [False] * 10)
    recall = [lambda m: operating_point(m, 0.25)[0]]
    by_image = bootstrap_ci(parts, recall, n_boot=500)[0]
    by_video = bootstrap_ci(parts, recall, n_boot=500, clusters=np.array([1] * 10 + [2] * 10))[0]
    assert 0.2 < by_image[0] < 0.5 < by_image[1] < 0.8
    assert by_video.tolist() == [0.0, 1.0]
