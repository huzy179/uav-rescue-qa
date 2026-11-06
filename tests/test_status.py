"""Kiểm tra gói trạng thái drone: tần suất gửi, đi qua giả lập mạng, trạm nhận và trả cho bản đồ."""

import json
import urllib.request
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from edge.alerts import FakeTransport
from edge.georef import Camera
from edge.status import LiveView, StatusReporter
from ground.app import create_app
from shared.schema import Telemetry, UavState
from sim.netem import NetemTransport

CAM = Camera(width=3840, height=2160, hfov_deg=90.0)


def tel(t: float) -> Telemetry:
    return Telemetry(t=t, lat=21.0 + t * 1e-5, lon=105.8, alt_agl_m=50.0, yaw_deg=0.0)


def test_reporter_sends_every_interval_and_logs() -> None:
    transport, log = FakeTransport(), []

    class Log:
        def write(self, line: str) -> None:
            log.append(json.loads(line))

    reporter = StatusReporter(transport, "uav1", 1.0, Log())
    results = [reporter.maybe_send(t, tel(t), CAM, pending_alerts=2) for t in (0.0, 0.5, 1.0, 1.5, 2.25)]
    assert results == [True, None, True, None, True]
    sent = [UavState.model_validate_json(m.payload) for _, m in transport.received]
    assert [s.t for s in sent] == [0.0, 1.0, 2.25] and [s.seq for s in sent] == [1, 2, 3]
    assert sent[0].pending_alerts == 2 and len(sent[0].footprint) == 4
    assert [m.msg_id for _, m in transport.received] == ["uav1:state:1", "uav1:state:2", "uav1:state:3"]
    assert [r["ok"] for r in log] == [True, True, True]


def test_reporter_goes_silent_during_outage() -> None:
    reporter = StatusReporter(NetemTransport(FakeTransport(), 0.0, [(10.0, 20.0)]), "uav1", 1.0)
    assert [reporter.maybe_send(float(t), tel(t), CAM) for t in (9, 10, 19, 20)] == [True, False, False, True]


def test_ground_keeps_latest_state_track_and_coverage(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "g.sqlite"))
    reporter = StatusReporter(FakeTransport(), "uav1", 1.0)
    for t in (0.0, 1.0, 2.0):
        reporter.maybe_send(t, tel(t), CAM, alerts_total=int(t))
    for _, msg in reporter.transport.received:
        response = client.post("/api/uav/state", json=json.loads(msg.payload))
        assert response.json() == {"ack": msg.msg_id}
    # Gói tới muộn (t nhỏ hơn) được ack nhưng không đè trạng thái mới nhất.
    late = UavState(uav_id="uav1", seq=9, t=0.5, lat=0, lon=0, alt_m=50, yaw_deg=0, footprint=[(0, 0)] * 4)
    assert client.post("/api/uav/state", json=late.model_dump(mode="json")).json() == {"ack": "uav1:state:9"}
    (uav,) = client.get("/api/uavs").json()
    assert uav["t"] == 2.0 and uav["alerts_total"] == 2 and uav["age_s"] >= 0
    assert len(uav["track"]) == 3 and len(uav["footprints"]) == 3


def test_live_view_serves_mjpeg() -> None:
    view = LiveView(0)
    try:
        view.publish(np.zeros((2160, 3840, 3), dtype=np.uint8))
        with urllib.request.urlopen(f"http://127.0.0.1:{view.port}/", timeout=5) as response:
            assert response.headers["Content-Type"].startswith("multipart/x-mixed-replace")
            head = response.read(200)
        assert head.startswith(b"--frame\r\nContent-Type: image/jpeg") and b"\xff\xd8" in head
    finally:
        view.close()


def test_trail_fills_coverage_gap_after_outage(tmp_path: Path) -> None:
    """Mất sóng 10–20 s: gói 10…19 hỏng; gói 20 mang 10 điểm gửi bù, trạm có đủ 21 điểm đường bay từ 0 tới 20."""
    client = TestClient(create_app(tmp_path / "g.sqlite"))

    class Ground(FakeTransport):
        def send(self, msg, now):  # noqa: ANN001
            return client.post("/api/uav/state", json=json.loads(msg.payload)).json()["ack"] == msg.msg_id

    reporter = StatusReporter(NetemTransport(Ground(), 0.0, [(10.0, 20.0)]), "uav1", 1.0)
    for t in range(0, 21):
        reporter.maybe_send(float(t), tel(t), CAM)
    (uav,) = client.get("/api/uavs").json()
    assert len(uav["track"]) == 21 and len(uav["footprints"]) == 21
    assert uav["track"][10][0] == tel(10).lat and "trail" not in uav
    assert reporter.unsent == []


def test_truth_layer_roundtrip(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "g.sqlite"))
    assert client.get("/api/truth").json() == {"people": []}
    layer = {"source": "x", "people": [{"id": 3, "t_in": 1.0, "t_out": 5.0, "track": [[1.0, 21.0, 105.8], [5.0, 21.0, 105.8001]]}]}
    assert client.post("/api/truth", json=layer).json() == {"people": 1}
    got = client.get("/api/truth").json()
    assert got["people"][0]["id"] == 3 and got["r_match_m"] == 10.0
    assert client.post("/api/truth", json={"people": [{"id": 1}]}).status_code == 422


def test_reset_clears_station(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "g.sqlite"))
    reporter = StatusReporter(FakeTransport(), "uav1", 1.0)
    reporter.maybe_send(0.0, tel(0), CAM)
    client.post("/api/uav/state", json=json.loads(reporter.transport.received[0][1].payload))
    client.post("/api/truth", json={"people": [{"id": 1, "t_in": 0, "t_out": 1, "track": [[0, 21.0, 105.8]]}]})
    assert client.post("/api/reset").status_code == 400  # thiếu confirm
    assert client.post("/api/reset?confirm=true").json() == {"reset": True}
    assert client.get("/api/uavs").json() == [] and client.get("/api/truth").json() == {"people": []}
    assert client.get("/api/incidents").json() == []
