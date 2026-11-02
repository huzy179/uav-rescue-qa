"""Kiểm tra xếp ưu tiên sự cố: điểm tính tay từng phần, thẻ của người vận hành, sự cố đã đóng xếp cuối."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ground.app import create_app
from ground.priority import PriorityRule, priority, rank


def incident(i: int, lat: float, **kw: object) -> dict:
    base = {"incident_id": i, "lat": lat, "lon": 105.8, "first_t": 0.0, "last_t": 0.0, "max_confidence": 0.5,
            "uav_ids": ["uav1"], "status": "open", "tag": None}
    return {**base, **kw}


def test_diem_tinh_tay() -> None:
    rule = PriorityRule()
    a = incident(1, 21.0, tag="water", uav_ids=["uav1", "uav2"], max_confidence=0.8)
    b = incident(2, 21.0001)  # cách a khoảng 11 m: cùng nhóm
    score, reasons = priority(a, [a, b], now_t=300.0, rule=rule)
    # dưới nước 3 + tin cậy 0,8 + một drone thêm 0,5 + một người gần 0,5 + chờ 300/600 × 2 = 1
    assert score == pytest.approx(3 + 0.8 + 0.5 + 0.5 + 1.0)
    assert reasons[0] == "dưới nước (+3,00)" and any("nhóm 2 người" in r for r in reasons)


def test_su_co_dong_xep_cuoi() -> None:
    rule = PriorityRule()
    items = [
        incident(1, 21.0, max_confidence=0.9),
        incident(2, 21.01, tag="water", max_confidence=0.3),
        incident(3, 21.02, status="resolved", max_confidence=1.0, last_t=10.0),
    ]
    ranked = rank(items, rule)
    assert [i["incident_id"] for i in ranked] == [2, 1, 3]
    assert ranked[2]["priority"] == 0.0 and ranked[2]["priority_reasons"] == ["đã xử lý"]


def test_api_gan_the_va_dong(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "g.sqlite"))
    for k, lat in enumerate([21.0, 21.01], start=1):
        client.post("/api/alerts", json={
            "alert_id": f"uav1-{k}", "uav_id": "uav1", "t": float(k), "lat": lat, "lon": 105.8, "position_error_m": 3.0,
            "altitude_m": 50.0, "cluster_id": k, "confidence": 0.6, "frames_confirmed": 3, "box_px": [0, 0, 10, 10],
            "model": "m",
        })
    first, second = client.get("/api/incidents").json()
    assert client.patch(f"/api/incidents/{first['incident_id']}", json={"tag": "boat"}).status_code == 400
    assert client.patch(f"/api/incidents/{second['incident_id']}", json={"tag": "water"}).status_code == 200
    assert client.get("/api/incidents").json()[0]["incident_id"] == second["incident_id"]
    client.patch(f"/api/incidents/{second['incident_id']}", json={"status": "false_alarm"})
    ranked = client.get("/api/incidents").json()
    assert ranked[-1]["incident_id"] == second["incident_id"] and ranked[-1]["status"] == "false_alarm"
    assert client.patch("/api/incidents/99", json={"status": "resolved"}).status_code == 404
