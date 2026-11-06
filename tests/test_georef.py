"""Kiểm tra phép chiếu pixel ↔ GPS bằng vòng đi–về và trường hợp tính tay."""

import math

import numpy as np
import pytest

from edge.georef import Camera, ErrorModel, ground_offset_m, gps_to_pixel, pixel_to_gps, position_error_m
from shared.schema import Telemetry

CAM = Camera(width=3840, height=2160, hfov_deg=90.0)  # f = 1920 px: 1 px = h/1920 m


def tel(yaw: float) -> Telemetry:
    return Telemetry(t=0.0, lat=21.0, lon=105.8, alt_agl_m=50.0, yaw_deg=yaw)


@pytest.mark.parametrize("yaw", [0.0, 37.0, 90.0, 270.0, 359.0])
@pytest.mark.parametrize("uv", [(0.0, 0.0), (1920.0, 1080.0), (3839.0, 2159.0), (100.5, 2000.25)])
def test_round_trip(yaw: float, uv: tuple[float, float]) -> None:
    """pixel → GPS → pixel ra đúng điểm cũ (sai số dưới 0,01 px)."""
    lat, lon = pixel_to_gps(*uv, tel(yaw), CAM)
    assert gps_to_pixel(lat, lon, tel(yaw), CAM) == pytest.approx(uv, abs=0.01)


def test_center_is_uav_position() -> None:
    assert pixel_to_gps(1920.0, 1080.0, tel(45.0), CAM) == pytest.approx((21.0, 105.8))


def test_hand_computed_offsets() -> None:
    """Điểm cách tâm 1920 px lên trên = 50 m về phía đỉnh ảnh: Bắc khi ψ = 0, Đông khi ψ = 90°."""
    lat, lon = pixel_to_gps(1920.0, 1080.0 - 1920.0, tel(0.0), CAM)
    assert ground_offset_m(21.0, 105.8, lat, lon) == pytest.approx((50.0, 0.0), abs=1e-6)
    lat, lon = pixel_to_gps(1920.0, 1080.0 - 1920.0, tel(90.0), CAM)
    assert ground_offset_m(21.0, 105.8, lat, lon) == pytest.approx((0.0, 50.0), abs=1e-6)
    # ψ = 90°: bên phải ảnh là phía Nam.
    lat, lon = pixel_to_gps(1920.0 + 1920.0, 1080.0, tel(90.0), CAM)
    assert ground_offset_m(21.0, 105.8, lat, lon) == pytest.approx((-50.0, 0.0), abs=1e-6)


def test_diagonal_fov_matches_gsd_calc() -> None:
    """82° chéo trên khung 16:9 ứng với góc ngang khoảng 74,0°."""
    cam = Camera.from_fov(82.0, "diagonal", 3840, 2160)
    expected = math.degrees(2 * math.atan(math.tan(math.radians(41.0)) * 3840 / math.hypot(3840, 2160)))
    assert cam.hfov_deg == pytest.approx(expected)
    assert 73.0 < cam.hfov_deg < 75.0


def test_frame_motion_identity_and_forward_flight() -> None:
    """Cùng telemetry: affine đơn vị. Bay 5 m về phía đỉnh ảnh ở 50 m (f = 1920 px): mặt đất dịch xuống 192 px."""
    from edge.georef import frame_motion
    from sim.flight import StraightFlight

    assert frame_motion(tel(30.0), tel(30.0), CAM) == pytest.approx(np.array([[1, 0, 0], [0, 1, 0.0]]), abs=1e-6)
    flight = StraightFlight(21.0, 105.8, 50.0, 10.0, yaw_deg=0.0)
    warp = frame_motion(flight.at(0.0), flight.at(0.5), CAM)
    assert warp == pytest.approx(np.array([[1, 0, 0], [0, 1, 192.0]]), abs=1e-3)


def test_co_nguoi_du_kien_va_he_so_thu_nho() -> None:
    from edge.detector import person_scale
    from edge.georef import expected_person_px

    cam = Camera(4000, 3000, 90.0)  # f = 2000 px
    tel = Telemetry(t=0.0, lat=21.0, lon=105.8, alt_agl_m=50.0, yaw_deg=0.0, pitch_deg=-90.0)
    assert expected_person_px(tel, cam, 0.5) == pytest.approx(20.0)
    assert person_scale(40.0, 20.0) == 2.0
    assert person_scale(10.0, 20.0) == 1.0  # không phóng to
    assert person_scale(40.0, None) == 1.0


def test_sai_so_vi_tri_tinh_tay() -> None:
    # Ảnh rộng 1000 px, góc ngang 90°: f = 500 px; ở 50 m GSD = 0,1 m/px.
    cam = Camera(1000, 1000, 90.0)
    tel = Telemetry(t=0, lat=21.0, lon=105.8, alt_agl_m=50.0, yaw_deg=0.0)
    model = ErrorModel(gps_sigma_m=3.0, alt_sigma_m=2.0, yaw_sigma_deg=2.0, tilt_sigma_deg=1.0, box_sigma_px=2.0)
    # Tâm ảnh (d = 0): GPS 3, nghiêng 50·tan1° ≈ 0,8727, box 0,2.
    assert position_error_m(500, 500, tel, cam, model) == pytest.approx(math.sqrt(9 + 0.872665**2 + 0.04), rel=1e-5)
    # Mép phải (d = 50 m): GPS 3; độ cao 50·2/50 = 2; hướng 50·0,034907 = 1,745; nghiêng 50·2·0,017453 = 1,745; box 0,2.
    assert position_error_m(1000, 500, tel, cam, model) == pytest.approx(math.sqrt(9 + 4 + 2 * 1.745329**2 + 0.04), rel=1e-5)
    # Không có sai số nào trừ GPS: đúng bằng σ_GPS ở mọi chỗ.
    assert position_error_m(1000, 0, tel, cam, ErrorModel(3.0, 0, 0, 0, 0)) == pytest.approx(3.0)


def test_footprint_corners_round_trip() -> None:
    """Bốn góc vùng camera nhìn chiếu ngược về đúng bốn góc ảnh; ở 50 m, f = 1920 px, ảnh rộng 3840 px phủ 100 m."""
    from edge.georef import footprint

    corners = footprint(tel(30.0), CAM)
    pixels = [gps_to_pixel(lat, lon, tel(30.0), CAM) for lat, lon in corners]
    assert pixels == [pytest.approx(p, abs=0.01) for p in [(0, 0), (3840, 0), (3840, 2160), (0, 2160)]]
    north, east = ground_offset_m(*corners[0], *corners[1])
    assert math.hypot(north, east) == pytest.approx(100.0, rel=1e-4)


def tilted(yaw: float, pitch: float) -> Telemetry:
    return Telemetry(t=0.0, lat=21.0, lon=105.8, alt_agl_m=50.0, yaw_deg=yaw, pitch_deg=pitch)


@pytest.mark.parametrize("pitch", [-90.0, -75.0, -60.0, -45.0])
@pytest.mark.parametrize("yaw", [0.0, 37.0, 200.0])
@pytest.mark.parametrize("uv", [(0.0, 2159.0), (1920.0, 1080.0), (3839.0, 1500.0), (800.5, 1200.25)])
def test_round_trip_tilted(pitch: float, yaw: float, uv: tuple[float, float]) -> None:
    """Camera nghiêng: pixel → GPS → pixel vẫn về đúng điểm cũ."""
    lat, lon = pixel_to_gps(*uv, tilted(yaw, pitch), CAM)
    assert gps_to_pixel(lat, lon, tilted(yaw, pitch), CAM) == pytest.approx(uv, abs=0.01)


def test_tilted_hand_computed() -> None:
    """Nghiêng 30° về phía trước (pitch −60°), hướng Bắc, cao 50 m: tâm ảnh nằm phía trước 50·tan30° = 28,868 m;
    pixel thấp hơn tâm f·tan30° (tia thẳng đứng) rơi đúng xuống điểm dưới UAV."""
    tel = tilted(0.0, -60.0)
    north, east = ground_offset_m(21.0, 105.8, *pixel_to_gps(1920.0, 1080.0, tel, CAM))
    assert (north, east) == pytest.approx((50.0 * math.tan(math.radians(30.0)), 0.0), abs=1e-3)
    v_nadir = 1080.0 + CAM.f_px * math.tan(math.radians(30.0))
    assert ground_offset_m(21.0, 105.8, *pixel_to_gps(1920.0, v_nadir, tel, CAM)) == pytest.approx((0.0, 0.0), abs=1e-3)


def test_above_horizon_and_footprint_when_tilted() -> None:
    """Nghiêng 80°: mép trên ảnh ở trên chân trời; footprint cắt ở 10 lần độ cao và là hình thang (mép xa rộng hơn)."""
    from edge.georef import FOOTPRINT_MAX_RANGE, footprint

    tel = tilted(0.0, -10.0)
    with pytest.raises(ValueError, match="chân trời"):
        pixel_to_gps(1920.0, 0.0, tel, CAM)
    corners = [ground_offset_m(21.0, 105.8, lat, lon) for lat, lon in footprint(tel, CAM)]
    assert corners[0][0] == pytest.approx(FOOTPRINT_MAX_RANGE * 50.0, rel=1e-3)
    far_width = corners[1][1] - corners[0][1]
    near_width = corners[2][1] - corners[3][1]
    assert far_width > near_width > 0


def test_spread_metric_is_robust_median() -> None:
    """Bốn điểm trùng nhau và một điểm lệch 100 m: trung vị khoảng cách vẫn là 0."""
    from edge.georef import offset_gps
    from tools.eval_georef_pitch import spread_m

    points = [(21.0, 105.8)] * 4 + [offset_gps(21.0, 105.8, 100.0, 0.0)]
    assert spread_m(points) == pytest.approx(0.0, abs=1e-6)
