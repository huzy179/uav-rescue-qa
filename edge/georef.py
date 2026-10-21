"""Đổi giữa pixel trên ảnh và toạ độ GPS, giả định camera nhìn thẳng xuống (TECHNICAL mục 8)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from shared.schema import Detection, Telemetry

EARTH_RADIUS_M = 6_378_137.0


@dataclass(frozen=True)
class Camera:
    """Kích thước ảnh và góc nhìn ngang của camera."""

    width: int
    height: int
    hfov_deg: float

    @classmethod
    def from_fov(cls, fov_deg: float, fov_type: str, width: int, height: int) -> Camera:
        """Tạo từ góc nhìn ngang hoặc góc chéo (DJI ghi thông số theo góc chéo); cùng công thức với gsd_calc.py."""
        if fov_type == "diagonal":
            half = math.atan(math.tan(math.radians(fov_deg) / 2.0) * width / math.hypot(width, height))
            fov_deg = math.degrees(2.0 * half)
        return cls(width, height, fov_deg)

    @property
    def f_px(self) -> float:
        """Tiêu cự tính bằng pixel."""
        return self.width / 2.0 / math.tan(math.radians(self.hfov_deg) / 2.0)


def offset_gps(lat: float, lon: float, north_m: float, east_m: float) -> tuple[float, float]:
    """Dời một điểm GPS theo hướng Bắc/Đông (mét); xấp xỉ mặt phẳng cục bộ, đủ chính xác trong vài km."""
    dlat = math.degrees(north_m / EARTH_RADIUS_M)
    dlon = math.degrees(east_m / (EARTH_RADIUS_M * math.cos(math.radians(lat))))
    return lat + dlat, lon + dlon


def ground_offset_m(lat0: float, lon0: float, lat: float, lon: float) -> tuple[float, float]:
    """Hàm ngược của offset_gps: trả về (bắc, đông) tính bằng mét từ điểm gốc."""
    north = math.radians(lat - lat0) * EARTH_RADIUS_M
    east = math.radians(lon - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
    return north, east


def ground_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Khoảng cách mặt đất giữa hai điểm gần nhau (mét)."""
    return math.hypot(*ground_offset_m(lat1, lon1, lat2, lon2))


def pixel_to_gps(u: float, v: float, tel: Telemetry, cam: Camera) -> tuple[float, float]:
    """Pixel (u sang phải, v xuống dưới) → (lat, lon) của điểm trên mặt đất."""
    scale = tel.alt_agl_m / cam.f_px
    forward = -(v - cam.height / 2.0) * scale
    right = (u - cam.width / 2.0) * scale
    yaw = math.radians(tel.yaw_deg)
    north = forward * math.cos(yaw) - right * math.sin(yaw)
    east = forward * math.sin(yaw) + right * math.cos(yaw)
    return offset_gps(tel.lat, tel.lon, north, east)


def gps_to_pixel(lat: float, lon: float, tel: Telemetry, cam: Camera) -> tuple[float, float]:
    """(lat, lon) → pixel (u, v); kết quả có thể nằm ngoài khung ảnh."""
    north, east = ground_offset_m(tel.lat, tel.lon, lat, lon)
    yaw = math.radians(tel.yaw_deg)
    forward = north * math.cos(yaw) + east * math.sin(yaw)
    right = -north * math.sin(yaw) + east * math.cos(yaw)
    scale = cam.f_px / tel.alt_agl_m
    return cam.width / 2.0 + right * scale, cam.height / 2.0 - forward * scale


def locate(det: Detection, tel: Telemetry, cam: Camera) -> Detection:
    """Điền lat/lon cho phát hiện, lấy tâm đáy box (chân người đứng; gần trùng tâm khi nhìn từ trên)."""
    x1, _, x2, y2 = det.box_px
    lat, lon = pixel_to_gps((x1 + x2) / 2.0, y2, tel, cam)
    return det.model_copy(update={"lat": lat, "lon": lon})
