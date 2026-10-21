"""Hàng đợi cảnh báo kiểu outbox trên SQLite: lưu trước khi gửi, toạ độ trước, ảnh sau (TECHNICAL mục 10)."""

from __future__ import annotations

import base64
import json
import random
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from shared.schema import Alert, AlertCrop, Confirmation, Telemetry

PRIORITY = {"coords": 0, "crop": 1}


@dataclass(frozen=True)
class OutboxMessage:
    msg_id: str  # "<alert_id>:coords" hoặc "<alert_id>:crop"
    alert_id: str
    kind: str  # 'coords' | 'crop'
    payload: str  # JSON của Alert hoặc AlertCrop


class Transport(Protocol):
    def send(self, msg: OutboxMessage, now: float) -> bool: ...  # True nếu nhận được ack


class FakeTransport:
    """Luôn ack và ghi lại thông điệp; dùng cho kiểm thử và khi chạy không có trạm mặt đất."""

    def __init__(self) -> None:
        self.received: list[tuple[float, OutboxMessage]] = []

    def send(self, msg: OutboxMessage, now: float) -> bool:
        self.received.append((now, msg))
        return True


class HttpTransport:
    """POST tới ground/; HTTP 200 kèm đúng msg_id trong trường ack là ack."""

    def __init__(self, base_url: str, timeout_s: float = 5.0) -> None:
        self.base_url, self.timeout_s = base_url.rstrip("/"), timeout_s

    def send(self, msg: OutboxMessage, now: float) -> bool:
        path = "/api/alerts" if msg.kind == "coords" else f"/api/alerts/{msg.alert_id}/crop"
        request = urllib.request.Request(
            self.base_url + path, data=msg.payload.encode(), headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                return response.status == 200 and json.load(response).get("ack") == msg.msg_id
        except (urllib.error.URLError, TimeoutError, ValueError):
            return False


def crop_jpeg_base64(frame: np.ndarray, box_px: tuple[float, float, float, float], size: int = 256) -> str:
    """Cắt ô size×size quanh tâm box (dời vào trong nếu sát mép ảnh), nén JPEG chất lượng 80."""
    height, width = frame.shape[:2]
    cx, cy = (box_px[0] + box_px[2]) / 2.0, (box_px[1] + box_px[3]) / 2.0
    x0 = int(min(max(cx - size / 2.0, 0), max(width - size, 0)))
    y0 = int(min(max(cy - size / 2.0, 0), max(height - size, 0)))
    ok, buffer = cv2.imencode(".jpg", frame[y0 : y0 + size, x0 : x0 + size], [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        raise ValueError("Không nén được ảnh cắt")
    return base64.b64encode(buffer.tobytes()).decode("ascii")


def make_alert(
    c: Confirmation, uav_id: str, seq: int, tel: Telemetry, position_error_m: float, model: str
) -> Alert:
    """Đóng gói một xác nhận thành gói toạ độ."""
    return Alert(
        alert_id=f"{uav_id}-{seq}",
        uav_id=uav_id,
        t=c.t,
        lat=c.lat,
        lon=c.lon,
        position_error_m=position_error_m,
        altitude_m=tel.alt_agl_m,
        cluster_id=c.cluster_id,
        confidence=c.confidence,
        frames_confirmed=c.frames_seen,
        box_px=(int(c.box_px[0]), int(c.box_px[1]), int(c.box_px[2]), int(c.box_px[3])),
        model=model,
    )


class Outbox:
    """Lưu thông điệp vào SQLite trước khi gửi; gửi lại với thời gian chờ tăng dần có nhiễu đến khi được ack.

    Mọi thời gian là đồng hồ mô phỏng truyền từ ngoài vào; nhiễu lấy từ random.Random(seed) để tái lập.
    """

    def __init__(
        self,
        db_path: Path | str,
        transport: Transport,
        base_s: float = 1.0,
        cap_s: float = 30.0,
        jitter: float = 0.2,
        seed: int = 0,
    ) -> None:
        self.db = sqlite3.connect(str(db_path))
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS outbox (
                msg_id TEXT PRIMARY KEY, alert_id TEXT NOT NULL, kind TEXT NOT NULL,
                priority INTEGER NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, next_try_t REAL NOT NULL,
                created_t REAL NOT NULL, acked_t REAL)"""
        )
        self.db.commit()
        self.transport = transport
        self.base_s, self.cap_s, self.jitter = base_s, cap_s, jitter
        self._rng = random.Random(seed)

    def enqueue(self, alert: Alert, crop: AlertCrop | None, now: float) -> None:
        """Ghi gói toạ độ (và ảnh cắt nếu có) vào outbox trong một giao dịch."""
        rows = [("coords", alert.model_dump_json())]
        if crop is not None:
            rows.append(("crop", crop.model_dump_json()))
        with self.db:
            self.db.executemany(
                "INSERT OR IGNORE INTO outbox (msg_id, alert_id, kind, priority, payload, status, next_try_t, created_t)"
                " VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
                [(f"{alert.alert_id}:{kind}", alert.alert_id, kind, PRIORITY[kind], payload, now, now) for kind, payload in rows],
            )

    def pump(self, now: float) -> list[dict[str, object]]:
        """Gửi các thông điệp đến hạn theo (ưu tiên, thời điểm tạo); trả về bản ghi từng lần gửi để ghi log.

        Ảnh cắt chỉ được gửi sau khi gói toạ độ cùng alert_id đã được ack. Gặp lần gửi thất bại đầu tiên thì
        dừng lượt này: đường truyền đang hỏng, gửi tiếp chỉ tốn băng thông.
        """
        records: list[dict[str, object]] = []
        while True:
            # Lấy từng thông điệp một, vì ack của gói toạ độ làm ảnh cắt cùng alert_id đến lượt ngay trong lượt này.
            row = self.db.execute(
                """SELECT msg_id, alert_id, kind, payload, attempts FROM outbox o
                   WHERE status = 'pending' AND next_try_t <= ?
                     AND (kind = 'coords' OR EXISTS (SELECT 1 FROM outbox c WHERE c.msg_id = o.alert_id || ':coords'
                                                     AND c.status = 'acked'))
                   ORDER BY priority, created_t, msg_id LIMIT 1""",
                (now,),
            ).fetchone()
            if row is None:
                break
            msg_id, alert_id, kind, payload, attempts = row
            ok = self.transport.send(OutboxMessage(msg_id, alert_id, kind, payload), now)
            attempts += 1
            with self.db:
                if ok:
                    self.db.execute(
                        "UPDATE outbox SET status = 'acked', attempts = ?, acked_t = ? WHERE msg_id = ?",
                        (attempts, now, msg_id),
                    )
                else:
                    wait = min(self.cap_s, self.base_s * 2 ** (attempts - 1)) * (1.0 + self.jitter * self._rng.random())
                    self.db.execute(
                        "UPDATE outbox SET attempts = ?, next_try_t = ? WHERE msg_id = ?", (attempts, now + wait, msg_id)
                    )
            records.append({"t": now, "msg_id": msg_id, "kind": kind, "ok": ok, "attempts": attempts, "bytes": len(payload)})
            if not ok:
                break
        return records

    def pending(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM outbox WHERE status = 'pending'").fetchone()[0]

    def close(self) -> None:
        self.db.close()
