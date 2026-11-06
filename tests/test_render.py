"""Kiểm tra ảnh tổng hợp: người được vẽ đúng chỗ phép chiếu đặt họ, với mọi hướng bay."""

import pytest

from edge.georef import Camera, gps_to_pixel, offset_gps
from shared.schema import Telemetry
from sim.render import CLOTHES, FloodScene
from sim.scenario import Person

LAT0, LON0 = 21.05, 105.82
CAM = Camera(width=640, height=360, hfov_deg=90.0)  # f = 320 px; ở 10 m, 1 px = 3,1 cm, người 0,5 m ≈ 16 px


@pytest.mark.parametrize("yaw", [0.0, 37.0, 180.0, 270.0])
def test_person_drawn_at_projected_pixel(yaw: float) -> None:
    lat, lon = offset_gps(LAT0, LON0, 4.0, -3.0)
    person = Person(person_id=0, lat=lat, lon=lon)
    scene = FloodScene(LAT0, LON0, (-30.0, 30.0, -30.0, 30.0), [person], seed=1, roof_share=0.0)
    tel = Telemetry(t=0.0, lat=LAT0, lon=LON0, alt_agl_m=10.0, yaw_deg=yaw)
    frame = scene.render(tel, CAM, 0.0)
    assert frame.shape == (360, 640, 3)
    u, v = gps_to_pixel(lat, lon, tel, CAM)
    # Tâm người là đầu (tối); cạnh đầu, trong bán kính áo, là màu áo của người 0.
    b, g, r = (int(c) for c in frame[round(v), round(u)])
    assert b + g + r < 200
    half = 0.25 * CAM.f_px / 10.0
    ring = [tuple(int(c) for c in frame[round(v), round(u + dx)]) for dx in (-0.7 * half, 0.7 * half)]
    assert any(sum(abs(a - b) for a, b in zip(px, CLOTHES[0])) < 60 for px in ring)
