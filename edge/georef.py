"""Đổi giữa pixel trên ảnh và toạ độ GPS, giả định camera nhìn thẳng xuống (TECHNICAL mục 8)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

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


def expected_person_px(tel: Telemetry, cam: Camera, person_m: float = 0.5) -> float:
    """Kích thước dự kiến (px) của vật cỡ person_m mét trên ảnh gốc, camera nhìn thẳng xuống."""
    return person_m * cam.f_px / tel.alt_agl_m


@dataclass(frozen=True)
class ErrorModel:
    """Độ lệch chuẩn của từng nguồn sai số định vị (TECHNICAL mục 8.4). Mặc định: GPS thường, chưa hiệu chỉnh."""

    gps_sigma_m: float = 3.0
    alt_sigma_m: float = 2.0
    yaw_sigma_deg: float = 2.0
    tilt_sigma_deg: float = 1.0
    box_sigma_px: float = 2.0


# Sai số mặt đất hai chiều, mỗi trục Gauss σ: khoảng cách r theo phân bố Rayleigh, P(r ≤ kσ) = 1 − exp(−k²/2).
# Bán kính 1σ chỉ chứa khoảng 39 %; vùng chứa 95 % có bán kính √(−2 ln 0,05) σ ≈ 2,448 σ (dùng cho vòng tròn trên bản đồ).
R95_FACTOR = math.sqrt(-2.0 * math.log(0.05))


def position_error_m(u: float, v: float, tel: Telemetry, cam: Camera, model: ErrorModel) -> float:
    """Sai số vị trí (1σ, mét) của điểm ảnh (u, v) sau pixel_to_gps: căn tổng bình phương các nguồn độc lập.

    Với d là khoảng cách mặt đất từ điểm ngay dưới UAV tới điểm đó và h là độ cao:
    GPS σ_GPS; độ cao d·δh/h; hướng d·δψ; nghiêng camera h·(1 + d²/h²)·δθ (đạo hàm của h·tanθ tại θ = atan(d/h):
    ở tâm là h·δθ, ra mép lớn dần); box lệch δpx·h/f. Điểm càng xa tâm ảnh thì sai số càng lớn.
    """
    h = tel.alt_agl_m
    gsd = h / cam.f_px
    d = math.hypot(u - cam.width / 2.0, v - cam.height / 2.0) * gsd
    parts = (
        model.gps_sigma_m,
        d * model.alt_sigma_m / h,
        d * math.radians(model.yaw_sigma_deg),
        h * (1.0 + (d / h) ** 2) * math.radians(model.tilt_sigma_deg),
        model.box_sigma_px * gsd,
    )
    return math.sqrt(sum(p * p for p in parts))


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


def frame_motion(tel_prev: Telemetry, tel_cur: Telemetry, cam: Camera) -> np.ndarray:
    """Phép biến đổi affine 2×3 đưa pixel của khung trước về vị trí của cùng điểm mặt đất trong khung này.

    Lấy 4 góc ảnh: pixel → GPS bằng telemetry khung trước, rồi GPS → pixel bằng telemetry khung này, và khớp affine
    bình phương tối thiểu. Với camera nadir, phép này là dịch + xoay (đổi hướng) + co giãn (đổi độ cao), nên khớp đúng.
    Dùng để bù chuyển động camera cho bytetrack_cmc (TECHNICAL mục 9.3).
    """
    corners = [(0.0, 0.0), (cam.width, 0.0), (0.0, cam.height), (cam.width, cam.height)]
    src = np.array([[u, v, 1.0] for u, v in corners])
    dst = np.array([gps_to_pixel(*pixel_to_gps(u, v, tel_prev, cam), tel_cur, cam) for u, v in corners])
    affine, *_ = np.linalg.lstsq(src, dst, rcond=None)
    return affine.T
