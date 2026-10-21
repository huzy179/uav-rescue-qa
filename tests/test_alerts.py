"""Kiểm tra outbox: toạ độ trước, ảnh sau, gửi lại khi mất mạng, không mất cảnh báo khi khởi động lại."""

from pathlib import Path

import numpy as np
import pytest

from edge.alerts import FakeTransport, OutboxMessage, Outbox, crop_jpeg_base64
from shared.schema import Alert, AlertCrop
from sim.netem import NetemTransport


def alert(seq: int) -> Alert:
    return Alert(
        alert_id=f"uav1-{seq}", uav_id="uav1", t=0.0, lat=21.0, lon=105.8, position_error_m=5.0,
        altitude_m=50.0, cluster_id=seq, confidence=0.6, frames_confirmed=3, box_px=(0, 0, 10, 10), model="m.pt",
    )


def crop(seq: int) -> AlertCrop:
    return AlertCrop(alert_id=f"uav1-{seq}", jpeg_base64="AA==")


class FlakyTransport(FakeTransport):
    """Thất bại khi now nằm trong khoảng down."""

    def __init__(self, down: tuple[float, float]) -> None:
        super().__init__()
        self.down = down

    def send(self, msg: OutboxMessage, now: float) -> bool:
        if self.down[0] <= now < self.down[1]:
            return False
        return super().send(msg, now)


def test_coords_sent_before_crops(tmp_path: Path) -> None:
    transport = FakeTransport()
    outbox = Outbox(tmp_path / "o.sqlite", transport)
    outbox.enqueue(alert(1), crop(1), 0.0)
    outbox.enqueue(alert(2), crop(2), 0.0)
    outbox.pump(0.0)
    assert [m.msg_id for _, m in transport.received] == ["uav1-1:coords", "uav1-2:coords", "uav1-1:crop", "uav1-2:crop"]
    assert outbox.pending() == 0


def test_retry_after_outage_with_backoff(tmp_path: Path) -> None:
    """Mất mạng từ 0 đến 10 s: thời gian chờ tăng dần (1, 2, 4… s ± nhiễu), gửi được ngay khi có lại sóng."""
    transport = FlakyTransport(down=(0.0, 10.0))
    outbox = Outbox(tmp_path / "o.sqlite", transport, jitter=0.0)
    outbox.enqueue(alert(1), crop(1), 0.0)
    attempts = [r for now in range(0, 20) for r in outbox.pump(float(now))]
    failed_times = [r["t"] for r in attempts if not r["ok"]]
    assert failed_times == [0.0, 1.0, 3.0, 7.0]  # chờ 1, 2, 4 giây
    first_ok = next(r for r in attempts if r["ok"])
    assert (first_ok["t"], first_ok["msg_id"]) == (15.0, "uav1-1:coords")  # lần chờ tiếp theo là 8 s
    assert outbox.pending() == 0


def test_crop_waits_for_coords_ack(tmp_path: Path) -> None:
    """Mất gói toạ độ thì không gửi ảnh cắt trong lượt đó."""
    transport = FlakyTransport(down=(0.0, 1.0))
    outbox = Outbox(tmp_path / "o.sqlite", transport, jitter=0.0)
    outbox.enqueue(alert(1), crop(1), 0.0)
    assert [r["msg_id"] for r in outbox.pump(0.0)] == ["uav1-1:coords"]
    assert [r["msg_id"] for r in outbox.pump(1.0)] == ["uav1-1:coords", "uav1-1:crop"]


def test_pending_messages_survive_restart(tmp_path: Path) -> None:
    db = tmp_path / "o.sqlite"
    outbox = Outbox(db, FlakyTransport(down=(0.0, 100.0)))
    outbox.enqueue(alert(1), crop(1), 0.0)
    outbox.pump(0.0)
    outbox.close()
    transport = FakeTransport()
    outbox = Outbox(db, transport)
    outbox.pump(200.0)
    assert len(transport.received) == 2


def test_enqueue_twice_is_idempotent(tmp_path: Path) -> None:
    outbox = Outbox(tmp_path / "o.sqlite", FakeTransport())
    outbox.enqueue(alert(1), None, 0.0)
    outbox.enqueue(alert(1), None, 0.0)
    assert outbox.pending() == 1


def test_netem_same_seed_same_events() -> None:
    msg = OutboxMessage("a:coords", "a", "coords", "{}")

    def run(seed: int) -> list[bool]:
        netem = NetemTransport(FakeTransport(), loss=0.3, outages=[(5.0, 8.0)], seed=seed)
        return [netem.send(msg, float(t)) for t in range(20)]

    assert run(1) == run(1)
    assert run(1) != run(2)
    assert not any(run(1)[5:8])
    with pytest.raises(ValueError):
        NetemTransport(FakeTransport(), loss=1.5)


def test_crop_near_border_has_full_size() -> None:
    import base64

    import cv2

    frame = np.full((300, 400, 3), 128, dtype=np.uint8)
    jpeg = base64.b64decode(crop_jpeg_base64(frame, (390, 290, 399, 299), size=256))
    image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    assert image.shape == (256, 256, 3)
