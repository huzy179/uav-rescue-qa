"""Kiểm tra API trạm mặt đất: bỏ trùng theo alert_id, ảnh cắt phải tới sau toạ độ."""

from pathlib import Path

from fastapi.testclient import TestClient

from ground.app import create_app

ALERT = {
    "alert_id": "uav1-1", "uav_id": "uav1", "t": 3.0, "lat": 21.0, "lon": 105.8, "position_error_m": 5.0,
    "altitude_m": 50.0, "cluster_id": 0, "confidence": 0.7, "frames_confirmed": 3, "box_px": [0, 0, 10, 10],
    "model": "yolo26s.pt",
}


def test_duplicate_alert_acked_but_stored_once(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "g.sqlite"))
    for _ in range(2):
        response = client.post("/api/alerts", json=ALERT)
        assert response.status_code == 200 and response.json() == {"ack": "uav1-1:coords"}
    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 1 and alerts[0]["has_crop"] == 0


def test_crop_requires_coords_first(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "g.sqlite"))
    crop = {"alert_id": "uav1-1", "jpeg_base64": "/9j/"}
    assert client.post("/api/alerts/uav1-1/crop", json=crop).status_code == 409
    client.post("/api/alerts", json=ALERT)
    assert client.post("/api/alerts/uav1-1/crop", json=crop).json() == {"ack": "uav1-1:crop"}
    assert client.get("/api/alerts/uav1-1/crop").content == b"\xff\xd8\xff"
    assert client.get("/api/alerts").json()[0]["has_crop"] == 1


def test_rejects_unsafe_alert_id_and_bad_payload(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "g.sqlite"))
    assert client.post("/api/alerts", json={**ALERT, "alert_id": "<script>"}).status_code == 422
    assert client.post("/api/alerts", json={**ALERT, "lat": "abc"}).status_code == 422
    client.post("/api/alerts", json=ALERT)
    assert client.post("/api/alerts/uav1-1/crop", json={"alert_id": "uav1-2", "jpeg_base64": "AA=="}).status_code == 400
    assert client.post("/api/alerts/uav1-1/crop", json={"alert_id": "uav1-1", "jpeg_base64": "!!"}).status_code == 400


def test_map_page_served(tmp_path: Path) -> None:
    assert "leaflet" in TestClient(create_app(tmp_path / "g.sqlite")).get("/").text
