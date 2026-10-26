"""Gộp cảnh báo thành sự cố ở trạm mặt đất (TECHNICAL mục 12.3).

Một người có thể sinh nhiều cảnh báo: hai drone cùng thấy, hoặc một drone tách nhầm khi GPS trôi
(docs/results/sds_mot_confirm.md). Chặn ở biên thì có thể bỏ sót người đứng gần (docs/results/alert_memory.md),
nên ở đây không bỏ cảnh báo nào: cảnh báo mới gắn vào sự cố gần nhất còn mở nếu đủ gần cả về chỗ lẫn về thời gian,
không thì mở sự cố mới. Người vận hành xem sự cố, mở ra vẫn thấy từng cảnh báo và ảnh cắt.

Không import edge/ (trạm mặt đất chỉ dùng shared/), nên có hàm khoảng cách riêng.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

EARTH_RADIUS_M = 6_371_000.0


@dataclass
class MergeRule:
    """Ngưỡng gộp: bán kính max(radius_m, error_weight × tổng position_error_m của hai bên); cách nhau quá
    window_s giây (theo đồng hồ chuyến bay, coi như các drone cùng mốc giờ) thì không gộp.

    Mặc định không dùng position_error_m: edge/main.py hiện gửi một hằng số (--position-error-m, 5 m) chưa hiệu
    chỉnh, và bán kính 10 m gộp nhầm cả nhóm người bơi gần nhau (docs/results/alert_memory.md, mục trạm mặt đất).
    """

    radius_m: float = 5.0
    error_weight: float = 0.0
    window_s: float = 300.0


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Khoảng cách mặt đất xấp xỉ phẳng (equirectangular); đủ chính xác ở cự ly vài trăm mét."""
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return EARTH_RADIUS_M * math.hypot(x, y)


def choose_incident(
    lat: float, lon: float, error_m: float, t: float, incidents: list[dict[str, Any]], rule: MergeRule
) -> int | None:
    """incident_id của sự cố gần nhất mà cảnh báo được gộp vào; None nếu phải mở sự cố mới.

    Mỗi sự cố là dict có incident_id, lat, lon, position_error_m, last_t.
    """
    best, best_d = None, math.inf
    for inc in incidents:
        if abs(t - inc["last_t"]) > rule.window_s:
            continue
        d = distance_m(lat, lon, inc["lat"], inc["lon"])
        if d <= max(rule.radius_m, rule.error_weight * (error_m + inc["position_error_m"])) and d < best_d:
            best, best_d = inc["incident_id"], d
    return best


def merged_position(inc: dict[str, Any], lat: float, lon: float, error_m: float) -> tuple[float, float, float]:
    """Vị trí sự cố sau khi thêm một cảnh báo: trung bình cộng các cảnh báo; sai số lấy nhỏ nhất."""
    n = inc["n_alerts"]
    return (
        (inc["lat"] * n + lat) / (n + 1),
        (inc["lon"] * n + lon) / (n + 1),
        min(inc["position_error_m"], error_m),
    )
