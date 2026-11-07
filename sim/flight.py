"""Sinh telemetry giả lập cho chuyến bay (TECHNICAL mục 11.3)."""

from __future__ import annotations

import math

from edge.georef import offset_gps
from shared.schema import Telemetry


class StraightFlight:
    """Bay thẳng với độ cao, vận tốc không đổi; đỉnh ảnh hướng theo chiều bay. Nhiễu GPS ở sim/scenario.py."""

    def __init__(self, lat0: float, lon0: float, alt_agl_m: float, speed_mps: float, yaw_deg: float) -> None:
        self.lat0, self.lon0 = lat0, lon0
        self.alt_agl_m, self.speed_mps, self.yaw_deg = alt_agl_m, speed_mps, yaw_deg

    def at(self, t: float) -> Telemetry:
        """Vị trí sau t giây kể từ điểm xuất phát."""
        distance = self.speed_mps * t
        yaw = math.radians(self.yaw_deg)
        lat, lon = offset_gps(self.lat0, self.lon0, distance * math.cos(yaw), distance * math.sin(yaw))
        return Telemetry(t=t, lat=lat, lon=lon, alt_agl_m=self.alt_agl_m, yaw_deg=self.yaw_deg)


class ZigzagFlight:
    """Bay quét kiểu luống cày: các đường dài leg_m theo hướng yaw_deg, lần lượt đi và về, mỗi đường cách nhau
    spacing_m về bên phải; giữa hai đường bay ngang spacing_m. Đỉnh ảnh hướng theo chiều đang bay (quay 180° ở đường về,
    90° khi chuyển đường), như drone khảo sát đặt gimbal theo thân máy.

    shortcut: quay đầu tức thời, không giảm tốc ở góc. Toạ độ cục bộ: forward theo yaw_deg, right vuông góc bên phải.
    """

    def __init__(
        self, lat0: float, lon0: float, alt_agl_m: float, speed_mps: float, yaw_deg: float, leg_m: float, spacing_m: float
    ) -> None:
        if leg_m <= 0 or spacing_m <= 0:
            raise ValueError("leg_m và spacing_m phải dương")
        self.lat0, self.lon0 = lat0, lon0
        self.alt_agl_m, self.speed_mps, self.yaw_deg = alt_agl_m, speed_mps, yaw_deg
        self.leg_m, self.spacing_m = leg_m, spacing_m

    def local(self, t: float) -> tuple[float, float, float]:
        """(forward, right, hướng tương đối so với yaw_deg tính bằng độ) sau t giây."""
        s = self.speed_mps * t
        cycle = self.leg_m + self.spacing_m
        k, r = int(s // cycle), s % cycle
        if r < self.leg_m:
            forward = r if k % 2 == 0 else self.leg_m - r
            return forward, k * self.spacing_m, 0.0 if k % 2 == 0 else 180.0
        return (self.leg_m if k % 2 == 0 else 0.0), k * self.spacing_m + (r - self.leg_m), 90.0

    def n_legs(self, duration_s: float) -> int:
        """Số đường bay đi hết trong duration_s giây (ít nhất 1)."""
        return max(1, int((self.speed_mps * duration_s + self.spacing_m) // (self.leg_m + self.spacing_m)))

    def at(self, t: float) -> Telemetry:
        forward, right, heading = self.local(t)
        yaw = math.radians(self.yaw_deg)
        north = forward * math.cos(yaw) - right * math.sin(yaw)
        east = forward * math.sin(yaw) + right * math.cos(yaw)
        lat, lon = offset_gps(self.lat0, self.lon0, north, east)
        return Telemetry(t=t, lat=lat, lon=lon, alt_agl_m=self.alt_agl_m, yaw_deg=(self.yaw_deg + heading) % 360.0)


class AltitudeProfile:
    """Độ cao thay đổi theo thời gian, nội suy tuyến tính giữa các điểm (t giây, độ cao m); ngoài khoảng giữ điểm đầu, cuối.

    Ví dụ "0:120,20:120,30:40,60:40": bay dò ở 120 m 20 giây, hạ xuống 40 m trong 10 giây, giữ 40 m. Dùng cho tình huống
    tần số xử lý và thu nhỏ khung theo độ cao có ý nghĩa nhất: độ cao đổi giữa chuyến (TECHNICAL mục 11.3).
    """

    allow_zero = False

    def __init__(self, points: list[tuple[float, float]]) -> None:
        if not points or any(v < 0 or (v == 0 and not self.allow_zero) for _, v in points):
            raise ValueError("Cần ít nhất một điểm, giá trị dương" + (" hoặc bằng 0" if self.allow_zero else ""))
        points = sorted(points)
        self.t, self.alt = [p[0] for p in points], [p[1] for p in points]

    @classmethod
    def parse(cls, text: str) -> AltitudeProfile:
        """Đọc chuỗi "t:alt,t:alt,..."."""
        try:
            return cls([(float(t), float(a)) for t, a in (item.split(":") for item in text.split(","))])
        except ValueError as error:
            raise ValueError(f"Hồ sơ phải dạng 't:giá_trị,t:giá_trị', nhận được {text!r}") from error

    def __call__(self, t: float) -> float:
        if t <= self.t[0]:
            return self.alt[0]
        for (t0, a0), (t1, a1) in zip(zip(self.t, self.alt), zip(self.t[1:], self.alt[1:])):
            if t <= t1:
                return a0 + (a1 - a0) * (t - t0) / (t1 - t0) if t1 > t0 else a1
        return self.alt[-1]


class SigmaProfile(AltitudeProfile):
    """Độ lệch chuẩn nhiễu GPS thay đổi theo thời gian, cùng cú pháp "t:σ,t:σ" (σ ≥ 0). Ví dụ "0:1,25:1,30:5": GPS tốt
    25 giây đầu rồi kém đi (mất vệ tinh, nhiễu đa đường gần nhà cao) (docs/CAI_TIEN.md 3.2)."""

    allow_zero = True
