"""Kiểm tra so khớp và AP theo nhóm kích thước bằng các ví dụ tính tay."""

import numpy as np
import pytest

from eval.metrics import SIZE_RANGES, average_precision, match_image, merge_matches, operating_point

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
