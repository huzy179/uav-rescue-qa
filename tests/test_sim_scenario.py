"""Kiểm tra detector giả của mô phỏng RQ3 khi recall theo cỡ người."""

from __future__ import annotations

import random

import pytest
from pathlib import Path

from edge.georef import Camera
from sim.scenario import RecallCurve, simulate_detections


def test_recall_curve_bac_thang_va_ngoai_mien(tmp_path: Path) -> None:
    path = tmp_path / "r.csv"
    path.write_text("model,lo,hi,recall\nA,4,8,0.2\nA,8,inf,0.9\nB,4,inf,0.0\n", encoding="utf-8")
    curve = RecallCurve.from_csv(path, "A")
    assert curve(5) == 0.2 and curve(8) == 0.9 and curve(1000) == 0.9 and curve(1) == 0.2
    cam = Camera(1000, 1000, 90.0)
    boxes = [(0, (0.0, 0.0, 5.0, 20.0)), (1, (100.0, 100.0, 130.0, 130.0))]
    dets = simulate_detections(0, 0.0, boxes, cam, RecallCurve.from_csv(path, "B"), 0.0, random.Random(0))
    assert dets == []  # recall 0 ở mọi cỡ
    dets = simulate_detections(0, 0.0, boxes, cam, lambda px: 1.0 if px >= 30 else 0.0, 0.0, random.Random(0))
    assert [d.box_px for d in dets] == [(100.0, 100.0, 130.0, 130.0)]


def test_duong_recall_khi_thu_nho() -> None:
    curve = RecallCurve((0.0, 10.0), (10.0, float("inf")), (0.2, 0.8))
    half = curve.scaled(2.0)  # thu nhỏ 2 lần: người 15 px còn 7,5 px
    assert curve(15.0) == 0.8 and half(15.0) == 0.2 and half(25.0) == 0.8


def test_bay_zigzag_di_ve_va_chuyen_duong() -> None:
    from sim.flight import ZigzagFlight

    f = ZigzagFlight(21.0, 105.8, 50.0, 10.0, 0.0, leg_m=100.0, spacing_m=40.0)
    assert f.local(5.0) == (50.0, 0.0, 0.0)  # đường 1, đi về phía trước
    assert f.local(12.0) == (100.0, 20.0, 90.0)  # đang chuyển sang đường 2
    assert f.local(19.0) == (50.0, 40.0, 180.0)  # đường 2, đi ngược lại
    assert f.at(19.0).yaw_deg == 180.0
    assert f.n_legs(60.0) == 4  # 600 m: 100 + 40 + 100 + 40 + 100 + 40 + 100 = 520 m


def test_ho_so_do_cao() -> None:
    from sim.flight import AltitudeProfile

    p = AltitudeProfile.parse("0:120,20:120,30:40")
    assert (p(-1), p(10), p(25), p(30), p(99)) == (120, 120, 80, 40, 40)


def test_gps_sigma_profile_giu_nguyen_khi_hang_so_va_doi_theo_thoi_gian() -> None:
    from sim.flight import SigmaProfile
    from sim.scenario import GaussMarkovGps

    # Hồ sơ hằng số 3 m cho cùng chuỗi sai số như σ cố định 3 m (cùng seed): kết quả cũ không đổi khi chuyển sang hồ sơ.
    fixed, profiled = GaussMarkovGps(3.0, 30.0, 7), GaussMarkovGps(0.0, 30.0, 7, SigmaProfile.parse("0:3"))
    for k in range(20):
        a, b = fixed.step(k * 0.5), profiled.step(k * 0.5)
        assert a == pytest.approx(b)
    # Cùng seed nên cùng z: sai số tỉ lệ đúng theo σ(t).
    low, ramp = GaussMarkovGps(0.0, 30.0, 1, SigmaProfile.parse("0:1")), GaussMarkovGps(0.0, 30.0, 1, SigmaProfile.parse("0:1,10:1,11:5"))
    for k in range(30):
        x, y = low.step(k * 0.5), ramp.step(k * 0.5)
        factor = ramp.sigma_at(k * 0.5)  # 1 tới giây 10, tăng dần tới 5 ở giây 11
        assert y == pytest.approx((x[0] * factor, x[1] * factor))
    assert ramp.sigma_at(5.0) == 1.0 and ramp.sigma_at(10.5) == pytest.approx(3.0) and ramp.sigma_at(20) == 5.0
    assert SigmaProfile.parse("0:0").__call__(3.0) == 0.0
    with pytest.raises(ValueError):
        SigmaProfile.parse("0:-1")


def test_telemetry_csv_doc_do_chinh_xac_gps(tmp_path) -> None:
    from edge.telemetry import SampledTelemetry

    path = tmp_path / "tel.csv"
    path.write_text("t,lat,lon,alt_agl_m,yaw_deg,gps_acc_m\n0,21,105,50,0,1\n2,21,105,50,0,5\n", encoding="utf-8")
    assert SampledTelemetry.from_csv(path).at(1.0).gps_acc_m == pytest.approx(3.0)
    path.write_text("t,lat,lon,alt_agl_m,yaw_deg\n0,21,105,50,0\n", encoding="utf-8")
    assert SampledTelemetry.from_csv(path).at(0.0).gps_acc_m is None


def test_place_people_in_groups() -> None:
    import math

    from edge.georef import ground_distance_m
    from sim.flight import StraightFlight
    from sim.scenario import place_people

    flight = StraightFlight(21.0, 105.8, 50.0, 10.0, 0.0)
    single = place_people(flight, 10, (50.0, 500.0), 25.0, 0.0, 3)
    assert single == place_people(flight, 10, (50.0, 500.0), 25.0, 0.0, 3, None, 1, 2.0)  # mặc định giữ chuỗi cũ
    people = place_people(flight, 10, (50.0, 500.0), 25.0, 0.0, 3, None, 4, 2.0)
    assert len(people) == 10 and [p.person_id for p in people] == list(range(10))
    groups = [people[i:i + 4] for i in range(0, 10, 4)]
    assert [len(g) for g in groups] == [4, 4, 2]
    for g in groups:  # mọi người trong nhóm nằm trong đường kính 2 × 2 m
        assert max(ground_distance_m(a.lat, a.lon, b.lat, b.lon) for a in g for b in g) <= 4.0 + 1e-6
    assert not math.isclose(people[0].lat, people[4].lat)
