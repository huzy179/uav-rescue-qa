"""Kiểm tra phép chiếu pixel ↔ GPS bằng vòng đi–về và trường hợp tính tay."""

import math

import numpy as np
import pytest

from edge.georef import Camera, ground_offset_m, gps_to_pixel, pixel_to_gps
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
