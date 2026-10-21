"""Sinh telemetry giả lập cho chuyến bay (TECHNICAL mục 11.3)."""

from __future__ import annotations

import math

from edge.georef import offset_gps
from shared.schema import Telemetry


class StraightFlight:
    """Bay thẳng với độ cao, vận tốc không đổi; đỉnh ảnh hướng theo chiều bay.

    shortcut: chưa có đường zig-zag và nhiễu GPS Gauss–Markov, thêm khi làm RQ3.
    """

    def __init__(self, lat0: float, lon0: float, alt_agl_m: float, speed_mps: float, yaw_deg: float) -> None:
        self.lat0, self.lon0 = lat0, lon0
        self.alt_agl_m, self.speed_mps, self.yaw_deg = alt_agl_m, speed_mps, yaw_deg

    def at(self, t: float) -> Telemetry:
        """Vị trí sau t giây kể từ điểm xuất phát."""
        distance = self.speed_mps * t
        yaw = math.radians(self.yaw_deg)
        lat, lon = offset_gps(self.lat0, self.lon0, distance * math.cos(yaw), distance * math.sin(yaw))
        return Telemetry(t=t, lat=lat, lon=lon, alt_agl_m=self.alt_agl_m, yaw_deg=self.yaw_deg)
