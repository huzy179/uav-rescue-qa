"""Đổi giữa pixel trên ảnh và toạ độ GPS, giả định camera nhìn thẳng xuống (TECHNICAL mục 8)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from shared.schema import R95_FACTOR, Detection, Telemetry  # noqa: F401 (R95_FACTOR dùng lại từ đây)

EARTH_RADIUS_M = 6_378_137.0
FOOTPRINT_MAX_RANGE = 10.0  # vùng camera nhìn khi nghiêng: cắt ở 10 lần độ cao phía trước


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




def position_error_m(u: float, v: float, tel: Telemetry, cam: Camera, model: ErrorModel) -> float:
    """Sai số vị trí (1σ, mét) của điểm ảnh (u, v) sau pixel_to_gps: căn tổng bình phương các nguồn độc lập.

    Với d là khoảng cách mặt đất từ điểm ngay dưới UAV tới điểm đó và h là độ cao:
    GPS σ_GPS; độ cao d·δh/h; hướng d·δψ; nghiêng camera h·(1 + d²/h²)·δθ (đạo hàm của h·tanθ tại θ = atan(d/h):
    ở tâm là h·δθ, ra mép lớn dần); box lệch δpx·h/f. Điểm càng xa tâm ảnh thì sai số càng lớn.
    """
    h = tel.alt_agl_m
    gsd = h / cam.f_px
    # d: khoảng cách mặt đất thật (đúng cả khi camera nghiêng); camera nhìn thẳng xuống thì bằng khoảng cách pixel × GSD.
    d = math.hypot(*_ground_offset(u, v, tel, cam))
    parts = (
        model.gps_sigma_m,
        d * model.alt_sigma_m / h,
        d * math.radians(model.yaw_sigma_deg),
        h * (1.0 + (d / h) ** 2) * math.radians(model.tilt_sigma_deg),
        model.box_sigma_px * gsd,
    )
    return math.sqrt(sum(p * p for p in parts))


def _tilt(tel: Telemetry) -> float:
    """Góc nghiêng của trục quang về phía trước so với phương thẳng đứng (radian): pitch −90° (nhìn thẳng xuống) là 0."""
    return math.radians(90.0 + tel.pitch_deg)


def _ground_offset(u: float, v: float, tel: Telemetry, cam: Camera) -> tuple[float, float]:
    """(phía trước, bên phải) tính bằng mét từ điểm ngay dưới UAV tới điểm mặt đất của pixel (u, v).

    Tia qua pixel trong hệ camera là (x, y, 1) với x = (u − c_x)/f, y = (v − c_y)/f. Camera nghiêng về phía trước một
    góc α so với nhìn thẳng xuống (TECHNICAL 8.3), nên thành phần phía trước của tia là s − y·c, thành phần hướng xuống
    là c + y·s (c = cos α, s = sin α), bên phải là x; giao với mặt nước ở độ sâu h. α = 0 thu về công thức nadir (8.1).
    Pixel ở trên đường chân trời không chạm mặt nước: ValueError.
    """
    x = (u - cam.width / 2.0) / cam.f_px
    y = (v - cam.height / 2.0) / cam.f_px
    alpha = _tilt(tel)
    c, s = math.cos(alpha), math.sin(alpha)
    down = c + y * s
    if down <= 1e-6:
        raise ValueError(f"Pixel ({u:.0f}, {v:.0f}) ở trên đường chân trời (camera nghiêng {math.degrees(alpha):.0f}°)")
    h = tel.alt_agl_m
    return h * (s - y * c) / down, h * x / down


def pixel_to_gps(u: float, v: float, tel: Telemetry, cam: Camera) -> tuple[float, float]:
    """Pixel (u sang phải, v xuống dưới) → (lat, lon) của điểm trên mặt đất (mặt nước phẳng; tính cả góc nghiêng
    của camera trong tel.pitch_deg; pitch −90° là nhìn thẳng xuống)."""
    forward, right = _ground_offset(u, v, tel, cam)
    yaw = math.radians(tel.yaw_deg)
    north = forward * math.cos(yaw) - right * math.sin(yaw)
    east = forward * math.sin(yaw) + right * math.cos(yaw)
    return offset_gps(tel.lat, tel.lon, north, east)


def gps_to_pixel(lat: float, lon: float, tel: Telemetry, cam: Camera) -> tuple[float, float]:
    """(lat, lon) → pixel (u, v); kết quả có thể nằm ngoài khung ảnh; điểm ở phía sau camera trả về (nan, nan)."""
    north, east = ground_offset_m(tel.lat, tel.lon, lat, lon)
    yaw = math.radians(tel.yaw_deg)
    a = (north * math.cos(yaw) + east * math.sin(yaw)) / tel.alt_agl_m  # phía trước / h
    r = (-north * math.sin(yaw) + east * math.cos(yaw)) / tel.alt_agl_m  # bên phải / h
    alpha = _tilt(tel)
    c, s = math.cos(alpha), math.sin(alpha)
    if c + a * s <= 1e-9:
        return math.nan, math.nan
    # Giải ngược _ground_offset: a = (s − y·c)/(c + y·s) và r = x/(c + y·s).
    y = (s - a * c) / (c + a * s)
    x = r * (c + y * s)
    return cam.width / 2.0 + x * cam.f_px, cam.height / 2.0 + y * cam.f_px


def footprint(tel: Telemetry, cam: Camera) -> list[tuple[float, float]]:
    """Vùng mặt đất camera đang nhìn: (lat, lon) của bốn góc ảnh theo thứ tự trên trái, trên phải, dưới phải, dưới trái.

    Thứ tự góc cố định nên mọi vùng có cùng chiều quay; trạm mặt đất tô hợp các vùng bằng luật nonzero mà không đậm
    dần ở chỗ chồng nhau.
    """
    top = 0.0
    alpha = _tilt(tel)
    if alpha > 1e-9:
        # Camera nghiêng: mép trên ảnh có thể ở xa hoặc trên chân trời; cắt vùng ở FOOTPRINT_MAX_RANGE × độ cao.
        a = FOOTPRINT_MAX_RANGE
        c, s = math.cos(alpha), math.sin(alpha)
        y_far = (s - a * c) / (c + a * s)
        top = min(max(0.0, cam.height / 2.0 + y_far * cam.f_px), float(cam.height) - 1.0)
    corners = ((0.0, top), (float(cam.width), top), (float(cam.width), float(cam.height)), (0.0, float(cam.height)))
    return [pixel_to_gps(u, v, tel, cam) for u, v in corners]


def locate(det: Detection, tel: Telemetry, cam: Camera) -> Detection:
    """Điền lat/lon cho phát hiện, lấy tâm đáy box (chân người đứng; gần trùng tâm khi nhìn từ trên)."""
    x1, _, x2, y2 = det.box_px
    lat, lon = pixel_to_gps((x1 + x2) / 2.0, y2, tel, cam)
    return det.model_copy(update={"lat": lat, "lon": lon})


def frame_motion(tel_prev: Telemetry, tel_cur: Telemetry, cam: Camera) -> np.ndarray:
    """Phép biến đổi affine 2×3 đưa pixel của khung trước về vị trí của cùng điểm mặt đất trong khung này.

    Lấy 4 góc ảnh: pixel → GPS bằng telemetry khung trước, rồi GPS → pixel bằng telemetry khung này, và khớp affine
    bình phương tối thiểu. Với camera nadir, phép này là dịch + xoay (đổi hướng) + co giãn (đổi độ cao), nên khớp đúng;
    camera nghiêng thì đúng là phép chiếu phối cảnh, affine chỉ xấp xỉ.
    Dùng để bù chuyển động camera cho bytetrack_cmc (TECHNICAL mục 9.3).
    """
    corners = [(0.0, 0.0), (cam.width, 0.0), (0.0, cam.height), (cam.width, cam.height)]
    src = np.array([[u, v, 1.0] for u, v in corners])
    dst = np.array([gps_to_pixel(*pixel_to_gps(u, v, tel_prev, cam), tel_cur, cam) for u, v in corners])
    affine, *_ = np.linalg.lstsq(src, dst, rcond=None)
    return affine.T
