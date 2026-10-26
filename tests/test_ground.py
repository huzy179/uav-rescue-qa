"""Kiểm tra API trạm mặt đất: bỏ trùng theo alert_id, ảnh cắt phải tới sau toạ độ."""

from pathlib import Path

from fastapi.testclient import TestClient

from ground.app import create_app
from ground.incidents import MergeRule, choose_incident, distance_m

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


def post(client: TestClient, alert_id: str, uav: str, lat: float, lon: float, t: float = 3.0, err: float = 2.0) -> None:
    body = {**ALERT, "alert_id": alert_id, "uav_id": uav, "lat": lat, "lon": lon, "t": t, "position_error_m": err}
    assert client.post("/api/alerts", json=body).status_code == 200


def test_canh_bao_gan_nhau_gop_thanh_mot_su_co(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "g.sqlite"))
    post(client, "uav1-1", "uav1", 21.0, 105.8)
    post(client, "uav2-1", "uav2", 21.00002, 105.8)  # cách 2,2 m, trong bán kính 5 m
    post(client, "uav2-1", "uav2", 21.00002, 105.8)  # gửi lại: không đếm thêm
    post(client, "uav1-2", "uav1", 21.0002, 105.8)  # cách 22 m: sự cố mới
    incidents = client.get("/api/incidents").json()
    assert sorted(i["n_alerts"] for i in incidents) == [1, 2]
    merged = next(i for i in incidents if i["n_alerts"] == 2)
    assert merged["uav_ids"] == ["uav1", "uav2"] and len(merged["alerts"]) == 2
    assert abs(merged["lat"] - 21.00001) < 1e-9


def test_khong_gop_khi_cach_xa_ve_thoi_gian(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "g.sqlite", MergeRule(window_s=60)))
    post(client, "uav1-1", "uav1", 21.0, 105.8, t=0.0)
    post(client, "uav1-2", "uav1", 21.0, 105.8, t=100.0)
    assert len(client.get("/api/incidents").json()) == 2


def test_chon_su_co_gan_nhat_trong_ban_kinh() -> None:
    incidents = [
        {"incident_id": 1, "lat": 21.0, "lon": 105.8, "position_error_m": 1.0, "last_t": 0.0},
        {"incident_id": 2, "lat": 21.00003, "lon": 105.8, "position_error_m": 1.0, "last_t": 0.0},
    ]
    rule = MergeRule(radius_m=3.0)
    assert choose_incident(21.00002, 105.8, 1.0, 0.0, incidents, rule) == 2  # 1,1 m tới #2, 2,2 m tới #1
    assert choose_incident(21.001, 105.8, 1.0, 0.0, incidents, rule) is None
    far = 21.00008  # cách #2 khoảng 5,6 m: ngoài 3 m, trong 2 × (2 + 1) m khi tính sai số
    assert choose_incident(far, 105.8, 2.0, 0.0, incidents, rule) is None
    assert choose_incident(far, 105.8, 2.0, 0.0, incidents, MergeRule(radius_m=3.0, error_weight=2.0)) == 2
    assert abs(distance_m(21.0, 105.8, 21.0001, 105.8) - 11.12) < 0.01


def test_cham_gop_su_co_dem_lan_va_tach() -> None:
    from eval.incident_merge_eval import purity

    # sự cố 0: người 1 và 2 (lẫn); sự cố 1: người 2 nữa (người 2 bị tách); sự cố 2: chỉ cảnh báo nhầm
    r = purity([0, 0, 1, 2], [1, 2, 2, None])
    assert r == {"incidents": 3, "people": 2, "mixed_incidents": 1, "people_split": 1, "people_merged": 2}
