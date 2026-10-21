"""Kiểm tra tổng hợp thời gian từng chặng bằng ví dụ tính tay."""

import pytest

from eval.timing_summary import summarize_timings


def test_totals_percentiles_and_fps() -> None:
    records = [
        {"tile_ms": 1.0, "infer_ms": 99.0, "merge_ms": 0.0, "georef_ms": 0.0, "confirm_ms": 0.0, "n_tiles": 32.0, "n_dets": 4},
        {"tile_ms": 1.0, "infer_ms": 199.0, "merge_ms": 0.0, "georef_ms": 0.0, "confirm_ms": 0.0, "n_tiles": 32.0, "n_dets": 6},
    ]
    row = summarize_timings(records)
    assert row["total_ms_mean"] == 150.0 and row["fps_at_mean"] == pytest.approx(6.67)
    assert row["total_ms_p95"] == pytest.approx(195.0)  # nội suy tuyến tính giữa 100 và 200
    assert row["infer_ms_p50"] == 149.0 and row["n_tiles"] == 32.0 and row["n_dets_mean"] == 5.0


def test_replay_has_no_detector_stages() -> None:
    row = summarize_timings([{"georef_ms": 0.5, "confirm_ms": 0.5, "n_dets": 1}])
    assert row["infer_ms_mean"] is None and row["total_ms_mean"] == 1.0
    with pytest.raises(ValueError):
        summarize_timings([])
