"""Xếp ưu tiên sự cố ở trạm mặt đất bằng luật cộng điểm giải thích được (TECHNICAL mục 12.4).

Điểm là tổng các phần, mỗi phần kèm một dòng lý do để người vận hành (và hội đồng) thấy vì sao sự cố này đứng trên:
- **thẻ của người vận hành** khi xem ảnh cắt: dưới nước cộng nhiều nhất, trên mái hay chỗ cao cộng ít;
- **độ tin cậy** cao nhất trong các cảnh báo của sự cố (0–1);
- **xác nhận chéo**: thêm drone thứ hai, thứ ba cùng thấy;
- **nhóm người**: số sự cố đang mở khác trong bán kính group_radius_m (một chuyến cứu được nhiều người);
- **chờ lâu**: tăng dần theo thời gian kể từ cảnh báo đầu, bão hoà ở wait_full_s.
Sự cố đã xử lý hoặc báo nhầm không có điểm và xếp cuối. Trọng số nằm trong PriorityRule, không học từ dữ liệu: không có
dữ liệu cứu hộ thật để học, và luật cố định thì giải thích được.

Không import edge/ (trạm mặt đất chỉ dùng shared/).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ground.incidents import distance_m

TAGS = {"water": "dưới nước", "roof": "trên mái, chỗ cao"}
STATUSES = {"open", "resolved", "false_alarm"}


@dataclass
class PriorityRule:
    """Trọng số điểm ưu tiên; mặc định để thẻ "dưới nước" lớn hơn mọi phần khác cộng lại trừ chờ lâu."""

    water: float = 3.0
    roof: float = 0.5
    confidence: float = 1.0
    per_extra_uav: float = 0.5
    per_neighbor: float = 0.5
    max_neighbors: int = 4
    group_radius_m: float = 30.0
    wait: float = 2.0
    wait_full_s: float = 600.0


def _vn(x: float) -> str:
    """Số hai chữ số thập phân, dấu phẩy như cách viết tiếng Việt trên giao diện."""
    return f"{x:.2f}".replace(".", ",")


def priority(inc: dict[str, Any], others: list[dict[str, Any]], now_t: float, rule: PriorityRule) -> tuple[float, list[str]]:
    """Điểm ưu tiên và lý do của một sự cố.

    inc có status, tag, max_confidence, uav_ids (list), lat, lon, first_t; others là các sự cố khác (để đếm nhóm).
    now_t theo đồng hồ chuyến bay (trạm lấy t lớn nhất đã nhận), không phải đồng hồ máy.
    """
    if inc.get("status", "open") != "open":
        return 0.0, ["đã xử lý" if inc.get("status") == "resolved" else "báo nhầm"]
    parts: list[tuple[float, str]] = []
    tag = inc.get("tag")
    if tag in TAGS:
        parts.append((getattr(rule, tag), TAGS[tag]))
    parts.append((rule.confidence * inc["max_confidence"], f"độ tin cậy {_vn(inc['max_confidence'])}"))
    n_uavs = len(inc["uav_ids"])
    if n_uavs > 1:
        parts.append((rule.per_extra_uav * (n_uavs - 1), f"{n_uavs} drone cùng thấy"))
    neighbors = sum(
        1 for o in others
        if o["incident_id"] != inc["incident_id"] and o.get("status", "open") == "open"
        and distance_m(inc["lat"], inc["lon"], o["lat"], o["lon"]) <= rule.group_radius_m
    )
    if neighbors:
        parts.append((rule.per_neighbor * min(neighbors, rule.max_neighbors), f"nhóm {neighbors + 1} người trong {rule.group_radius_m:g} m"))
    waited = max(0.0, now_t - inc["first_t"])
    if waited > 0:
        parts.append((rule.wait * min(waited / rule.wait_full_s, 1.0), f"chờ {waited / 60:.0f} phút"))
    return sum(p for p, _ in parts), [f"{reason} (+{_vn(p)})" for p, reason in parts]


def rank(incidents: list[dict[str, Any]], rule: PriorityRule) -> list[dict[str, Any]]:
    """Gắn priority, priority_reasons vào từng sự cố; trả danh sách: sự cố mở theo điểm giảm dần, rồi sự cố đã đóng."""
    now_t = max((i["last_t"] for i in incidents), default=0.0)
    for inc in incidents:
        inc["priority"], inc["priority_reasons"] = priority(inc, incidents, now_t, rule)
    return sorted(incidents, key=lambda i: (i.get("status", "open") != "open", -i["priority"], -i["last_t"]))
