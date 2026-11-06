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
