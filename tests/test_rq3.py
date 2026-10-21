"""Kiểm tra mô phỏng RQ3 và cách tính chỉ số bằng ví dụ tính tay."""

import random

import pytest

from edge.georef import Camera, ground_offset_m, offset_gps
from eval.rq3_metrics import compute_metrics, presence
from shared.schema import Alert, Telemetry
from sim.flight import StraightFlight
from sim.scenario import GaussMarkovGps, Person, noisy_telemetry, simulate_detections, visible_boxes

LAT0, LON0 = 21.0, 105.8


def alert(seq: int, t: float, north_m: float, east_m: float = 0.0) -> Alert:
    lat, lon = offset_gps(LAT0, LON0, north_m, east_m)
    return Alert(
        alert_id=f"uav1-{seq}", uav_id="uav1", t=t, lat=lat, lon=lon, position_error_m=5.0, altitude_m=50.0,
        cluster_id=seq, confidence=0.6, frames_confirmed=3, box_px=(0, 0, 10, 10), model="m.pt",
    )


def truth_two_people() -> dict:
    """Người 0 ở gốc, người 1 cách 100 m về phía Bắc; người 2 đứng ngay cạnh người 0 (4 m về phía Đông)."""
    p1 = offset_gps(LAT0, LON0, 100.0, 0.0)
    p2 = offset_gps(LAT0, LON0, 0.0, 4.0)
    return {
        "fps": 1.0,
        "duration_s": 120.0,
        "people": [
            {"person_id": 0, "lat": LAT0, "lon": LON0},
            {"person_id": 1, "lat": p1[0], "lon": p1[1]},
            {"person_id": 2, "lat": p2[0], "lon": p2[1]},
            {"person_id": 3, "lat": LAT0, "lon": LON0 + 1.0},  # không bao giờ vào khung: không tính
        ],
        "frames": [
            {"frame_id": 0, "t": 10.0, "visible": [{"person_id": 0}, {"person_id": 2}]},
            {"frame_id": 1, "t": 20.0, "visible": [{"person_id": 0}, {"person_id": 1}, {"person_id": 2}]},
            {"frame_id": 2, "t": 30.0, "visible": [{"person_id": 1}]},
        ],
    }


def test_presence_spans() -> None:
    assert presence(truth_two_people()) == {0: (10.0, 20.0), 2: (10.0, 20.0), 1: (20.0, 30.0)}


def test_metrics_hand_example() -> None:
    """4 cảnh báo: uav1-1 và uav1-2 đều trong 10 m của cả người 0 lẫn người 2 (cách nhau 4 m) nên cả hai là gộp nhầm,
    cùng gán người gần nhất là người 0 (sai số 1 m và 0 m), nên người 0 bị tách nhầm;
    uav1-3 ở chỗ không có ai (báo động giả), uav1-4 vào người 1 nhưng quá muộn (t_out 30 + tail 10 < 50: bỏ sót)."""
    truth = truth_two_people()
    alerts = [alert(1, 15.0, 1.0), alert(2, 18.0, 0.0), alert(3, 25.0, 50.0), alert(4, 50.0, 100.0)]
    sends = [
        {"t": 15.0, "msg_id": "uav1-1:coords", "kind": "coords", "ok": True, "bytes": 300},
        {"t": 18.0, "msg_id": "uav1-2:coords", "kind": "coords", "ok": False, "bytes": 300},
        {"t": 21.0, "msg_id": "uav1-2:coords", "kind": "coords", "ok": True, "bytes": 300},
        {"t": 25.0, "msg_id": "uav1-3:coords", "kind": "coords", "ok": True, "bytes": 300},
        {"t": 25.0, "msg_id": "uav1-3:crop", "kind": "crop", "ok": True, "bytes": 2048},
    ]
    summary, per_person = compute_metrics(alerts, sends, truth, r_eval_m=10.0, tail_s=10.0)
    assert summary["n_people"] == 3
    assert summary["false_alarms"] == 1 and summary["false_alarms_per_min"] == pytest.approx(0.5)
    assert summary["merge_errors"] == 2 and summary["split_errors"] == 1
    assert summary["missed_rate"] == pytest.approx(2 / 3)  # người 1 (quá muộn) và người 2 (bị gộp vào người 0)
    by_id = {p["person_id"]: p for p in per_person}
    assert by_id[0]["time_to_alert_s"] == pytest.approx(5.0)
    assert by_id[0]["position_error_m"] == pytest.approx(1.0, abs=1e-6)
    assert summary["delivery_delay_s_median"] == pytest.approx(0.0) and summary["delivery_delay_s_max"] == pytest.approx(3.0)
    assert summary["lost_rate"] == pytest.approx(0.25)  # uav1-4 chưa từng được ack
    assert summary["kb_per_alert"] == pytest.approx((4 * 300 + 2048) / 1024 / 4)


def test_visible_boxes_and_person_size() -> None:
    """Người ngay dưới UAV nằm giữa khung, box cạnh = 0,5 m × f / h; người ở xa 200 m không trong khung."""
    cam = Camera(3840, 2160, 90.0)  # f = 1920 px
    tel = Telemetry(t=0.0, lat=LAT0, lon=LON0, alt_agl_m=50.0, yaw_deg=0.0)
    far = offset_gps(LAT0, LON0, 200.0, 0.0)
    boxes = visible_boxes([Person(0, LAT0, LON0), Person(1, *far)], tel, cam, 0.0)
    assert [pid for pid, _ in boxes] == [0]
    x1, y1, x2, y2 = boxes[0][1]
    assert (x2 - x1, (x1 + x2) / 2, (y1 + y2) / 2) == pytest.approx((19.2, 1920.0, 1080.0))


def test_drifting_person() -> None:
    lat, lon = Person(0, LAT0, LON0, drift_n_mps=0.5).at(10.0)
    assert ground_offset_m(LAT0, LON0, lat, lon) == pytest.approx((5.0, 0.0), abs=1e-6)


def test_gauss_markov_gps_is_correlated_and_has_target_sigma() -> None:
    """Hai mẫu cách 1 s gần như giống nhau (τ = 30 s); trên chuỗi dài, độ lệch chuẩn gần σ."""
    gps = GaussMarkovGps(sigma_m=3.0, tau_s=30.0, seed=0)
    series = [gps.step(float(t))[0] for t in range(20000)]
    assert abs(series[1] - series[0]) < 1.5
    mean = sum(series) / len(series)
    std = (sum((x - mean) ** 2 for x in series) / len(series)) ** 0.5
    assert 2.4 < std < 3.6
    assert GaussMarkovGps(0.0, 30.0, 0).step(5.0) == (0.0, 0.0)


def test_noisy_telemetry_moves_position_only() -> None:
    tel = StraightFlight(LAT0, LON0, 50.0, 10.0, 0.0).at(0.0)
    noisy = noisy_telemetry(tel, GaussMarkovGps(5.0, 30.0, 1))
    assert (noisy.alt_agl_m, noisy.yaw_deg) == (tel.alt_agl_m, tel.yaw_deg)
    assert noisy.lat != tel.lat


def test_simulated_detection_rates() -> None:
    """Recall 0,7 và 0,5 báo nhầm mỗi khung, đo lại trên 4000 khung."""
    cam = Camera(3840, 2160, 90.0)
    rng = random.Random(0)
    boxes = [(0, (100.0, 100.0, 120.0, 120.0))]
    dets = [simulate_detections(k, 0.0, boxes, cam, 0.7, 0.5, rng) for k in range(4000)]
    hits = sum(any(d.box_px == boxes[0][1] for d in frame) for frame in dets)
    false = sum(sum(d.box_px != boxes[0][1] for d in frame) for frame in dets)
    assert hits / 4000 == pytest.approx(0.7, abs=0.03)
    assert false / 4000 == pytest.approx(0.5, abs=0.05)


def test_yaw_bias_and_tilt() -> None:
    """Lệch hướng chỉ đổi yaw; nghiêng 1° ở 50 m dời vùng chụp 50·tan 1° ≈ 0,87 m về phía trước."""
    from sim.scenario import tilted_view

    tel = Telemetry(t=0.0, lat=LAT0, lon=LON0, alt_agl_m=50.0, yaw_deg=359.0)
    noisy = noisy_telemetry(tel, GaussMarkovGps(0.0, 30.0, 0), yaw_bias_deg=3.0)
    assert (noisy.lat, noisy.yaw_deg) == (tel.lat, pytest.approx(2.0))
    view = tilted_view(tel.model_copy(update={"yaw_deg": 90.0}), 1.0)
    assert ground_offset_m(LAT0, LON0, view.lat, view.lon) == pytest.approx((0.0, 0.8727), abs=1e-3)
    assert tilted_view(tel, 0.0) is tel


def test_sweep_summary_and_config_validation(tmp_path) -> None:
    from pydantic import ValidationError

    from sim.sweep_rq3 import METRICS, SweepConfig, summarize, validate

    rows = [{"confirm": "geo", "seed": s, **{m: None for m in METRICS}, "missed_rate": v} for s, v in enumerate([0.0, 0.2, 0.4])]
    item = summarize(rows, ["confirm"])[0]
    assert (item["n_seeds"], item["missed_rate_mean"], item["missed_rate_std"]) == (3, 0.2, 0.2)
    assert item["time_to_alert_s_median_mean"] is None and item["time_to_alert_s_median_n"] == 0

    with pytest.raises(ValidationError):
        SweepConfig(output=tmp_path, grid={"gps_sigma_m": [1]})  # thiếu tiền tố scenario./pipeline.
    with pytest.raises(SystemExit, match="không tồn tại"):
        validate(SweepConfig(output=tmp_path, grid={"pipeline.confrim": ["geo"]}))
    with pytest.raises(SystemExit, match="tự đặt"):
        validate(SweepConfig(output=tmp_path, scenario={"seed": 3}))
