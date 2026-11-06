"""Kiểm tra lớp đáp án: lấy mẫu theo thời gian và chuyển ground_truth.json của mô phỏng."""

from tools.make_truth_layer import from_rq3, sample_times


def test_sample_times_keeps_ends() -> None:
    assert sample_times([0.0, 0.25, 0.5, 1.0, 1.25, 2.1], 1.0) == [0.0, 1.0, 2.1]
    assert sample_times([3.0], 1.0) == [3.0]


def test_from_rq3_uses_visible_span_and_drift() -> None:
    truth = {
        "people": [
            {"person_id": 0, "lat": 21.0, "lon": 105.8, "drift_n_mps": 1.0, "drift_e_mps": 0.0},
            {"person_id": 1, "lat": 21.1, "lon": 105.8},  # không bao giờ vào khung: bỏ
        ],
        "frames": [{"t": t, "visible": [{"person_id": 0}]} for t in (2.0, 2.5, 3.0, 4.0)],
    }
    (person,) = from_rq3(truth, 1.0)
    assert (person["id"], person["t_in"], person["t_out"]) == (0, 2.0, 4.0)
    assert [p[0] for p in person["track"]] == [2.0, 3.0, 4.0]
    assert person["track"][-1][1] > person["track"][0][1]  # trôi về phía Bắc
