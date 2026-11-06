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


def test_ban_kinh_rong_hon_khi_khac_drone() -> None:
    # Sự cố của uav1 sai số 4 m; cảnh báo mới sai số 3 m cách 5,6 m.
    incidents = [{"incident_id": 1, "lat": 21.0, "lon": 105.8, "position_error_m": 4.0, "last_t": 0.0, "uav_ids": "uav1"}]
    far = 21.00005  # khoảng 5,6 m
    rule = MergeRule(radius_m=5.0)
    # Cùng drone: GPS lệch cùng chiều, giữ 5 m.
    assert choose_incident(far, 105.8, 3.0, 0.0, incidents, rule, "uav1") is None
    # Drone khác: căn(3² + 4²) = 5 m chưa đủ; hệ số 1,2 thì 6 m, gộp.
    assert choose_incident(far, 105.8, 3.0, 0.0, incidents, rule, "uav2") is None
    assert choose_incident(far, 105.8, 3.0, 0.0, incidents, MergeRule(radius_m=5.0, cross_uav_error_weight=1.2), "uav2") == 1


def test_stream_bao_khi_co_thay_doi(tmp_path: Path) -> None:
    from ground.app import change_token

    client = TestClient(create_app(tmp_path / "g.sqlite"))
    before = change_token(str(tmp_path / "g.sqlite"))
    post(client, "uav1-1", "uav1", 21.0, 105.8)
    assert change_token(str(tmp_path / "g.sqlite")) != before
    with client.stream("GET", "/api/stream", params={"max_events": 1}) as r:
        body = "".join(r.iter_text())
    assert body.startswith("event: update\ndata: ")


def test_tile_cached_after_first_view_and_served_offline(tmp_path: Path) -> None:
    calls: list[str] = []

    def online(url: str) -> bytes:
        calls.append(url)
        return b"\x89PNG fake"

    client = TestClient(create_app(tmp_path / "g.sqlite", tile_cache=tmp_path / "tiles", fetch=online))
    first = client.get("/tiles/satellite/15/26000/14000")
    assert first.status_code == 200 and first.headers["content-type"] == "image/png"
    assert calls == ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/15/14000/26000"]

    def offline(url: str) -> bytes:
        raise OSError("mất mạng")

    client = TestClient(create_app(tmp_path / "g.sqlite", tile_cache=tmp_path / "tiles", fetch=offline))
    assert client.get("/tiles/satellite/15/26000/14000").content == b"\x89PNG fake"
    assert client.get("/tiles/satellite/15/26000/14001").status_code == 404
    assert client.get("/tiles/khac/15/26000/14000").status_code == 404
    assert client.get("/tiles/satellite/2/9/0").status_code == 404


def test_map_page_works_without_internet(tmp_path: Path) -> None:
    """Trang không tải gì từ internet: mọi địa chỉ http(s) phải là link người dùng tự bấm (mở Google Maps trên điện
    thoại), không phải script, stylesheet hay ảnh."""
    import re

    client = TestClient(create_app(tmp_path / "g.sqlite"))
    allowed = ("https://www.google.com/maps/search/", "http://www.w3.org/2000/svg")  # SVG namespace: không tải gì
    urls = re.findall(r"https?://[^\s\"'`<>)]+", client.get("/").text)
    assert all(url.startswith(allowed) for url in urls), urls
    assert client.get("/static/leaflet/leaflet.js").status_code == 200


def test_incidents_gpx_lists_open_incidents(tmp_path: Path) -> None:
    """Hai sự cố cách xa nhau, đóng một: GPX còn một điểm mốc, toạ độ và tên đúng, XML hợp lệ."""
    import xml.etree.ElementTree as ET

    client = TestClient(create_app(tmp_path / "g.sqlite"))
    post(client, "uav1-1", "uav1", 21.0, 105.8)
    post(client, "uav1-2", "uav1", 21.01, 105.8)
    incidents = client.get("/api/incidents").json()
    closed = next(i for i in incidents if abs(i["lat"] - 21.01) < 1e-9)["incident_id"]
    client.patch(f"/api/incidents/{closed}", json={"status": "resolved"})
    response = client.get("/api/incidents.gpx")
    assert response.headers["content-type"].startswith("application/gpx+xml")
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    (wpt,) = ET.fromstring(response.content).findall("g:wpt", ns)
    assert float(wpt.get("lat")) == 21.0 and float(wpt.get("lon")) == 105.8
    assert wpt.find("g:name", ns).text.startswith("FE-") and "vùng tìm 95%" in wpt.find("g:desc", ns).text


def test_incident_keeps_largest_group_size(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "g.sqlite"))
    for seq, group in ((1, 2), (2, 4), (3, 1)):
        body = {"alert_id": f"uav1-{seq}", "uav_id": "uav1", "t": 3.0 + seq, "lat": 21.0, "lon": 105.8, "position_error_m": 2.0,
                "altitude_m": 50.0, "cluster_id": seq, "confidence": 0.6, "frames_confirmed": 3, "box_px": [0, 0, 10, 10],
                "model": "m.pt", "group_size": group}
        assert client.post("/api/alerts", json=body).status_code == 200
    (inc,) = client.get("/api/incidents").json()
    assert inc["group_size"] == 4 and inc["n_alerts"] == 3
    assert "nhóm khoảng 4 người" in client.get("/api/incidents.gpx").text
