"""Trạm mặt đất: nhận cảnh báo, bỏ trùng theo alert_id, gộp thành sự cố, hiển thị trên bản đồ (TECHNICAL mục 12).

Chạy: FLOODEYE_GROUND_DB=runs/ground.sqlite .venv/bin/python -m uvicorn --factory ground.app:default_app --port 8000
Không import torch, ultralytics hay opencv; chỉ dùng shared/.
"""

from __future__ import annotations

import base64
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse

from ground.incidents import MergeRule, choose_incident, merged_position
from shared.schema import Alert, AlertCrop

MAP_HTML = Path(__file__).with_name("map.html")


def create_app(db_path: Path | str, rule: MergeRule | None = None) -> FastAPI:
    """Tạo ứng dụng với một file SQLite; tách hàm để kiểm thử dùng file tạm."""
    rule = rule or MergeRule()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db_path = str(db_path)
    with sqlite3.connect(db_path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute(
            """CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY, uav_id TEXT NOT NULL, t REAL NOT NULL, lat REAL NOT NULL,
                lon REAL NOT NULL, position_error_m REAL, altitude_m REAL, cluster_id INTEGER,
                confidence REAL, frames_confirmed INTEGER, model TEXT, received_at TEXT NOT NULL)"""
        )
        if "incident_id" not in {row[1] for row in db.execute("PRAGMA table_info(alerts)")}:
            db.execute("ALTER TABLE alerts ADD COLUMN incident_id INTEGER")  # file cũ, trước khi có sự cố
        db.execute(
            """CREATE TABLE IF NOT EXISTS incidents (
                incident_id INTEGER PRIMARY KEY, lat REAL NOT NULL, lon REAL NOT NULL, position_error_m REAL NOT NULL,
                first_t REAL NOT NULL, last_t REAL NOT NULL, n_alerts INTEGER NOT NULL, uav_ids TEXT NOT NULL)"""
        )
        db.execute("CREATE TABLE IF NOT EXISTS crops (alert_id TEXT PRIMARY KEY, jpeg BLOB NOT NULL, received_at TEXT NOT NULL)")

    app = FastAPI(title="FloodEye – trạm mặt đất")

    def now_iso() -> str:
        # Trạm mặt đất không thuộc pipeline mô phỏng nên dùng đồng hồ thật để ghi lúc nhận.
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    @app.post("/api/alerts")
    def post_alert(alert: Alert) -> dict[str, str]:
        """Nhận gói toạ độ; trùng alert_id vẫn ack nhưng không ghi lại (gửi lại không sinh cảnh báo trùng).

        Cảnh báo mới được gắn vào một sự cố (ground/incidents.py) trong cùng giao dịch; BEGIN IMMEDIATE để hai
        cảnh báo tới cùng lúc không cùng mở hai sự cố cho một người.
        """
        db = sqlite3.connect(db_path, isolation_level=None)
        try:
            db.execute("BEGIN IMMEDIATE")
            inserted = db.execute(
                "INSERT OR IGNORE INTO alerts (alert_id, uav_id, t, lat, lon, position_error_m, altitude_m, cluster_id,"
                " confidence, frames_confirmed, model, received_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    alert.alert_id, alert.uav_id, alert.t, alert.lat, alert.lon, alert.position_error_m,
                    alert.altitude_m, alert.cluster_id, alert.confidence, alert.frames_confirmed, alert.model, now_iso(),
                ),
            ).rowcount
            if inserted:
                attach_incident(db, alert)
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        return {"ack": f"{alert.alert_id}:coords"}

    def attach_incident(db: sqlite3.Connection, alert: Alert) -> None:
        db.row_factory = sqlite3.Row
        candidates = [dict(r) for r in db.execute("SELECT * FROM incidents WHERE last_t >= ?", (alert.t - rule.window_s,))]
        incident_id = choose_incident(alert.lat, alert.lon, alert.position_error_m, alert.t, candidates, rule)
        if incident_id is None:
            incident_id = db.execute(
                "INSERT INTO incidents (lat, lon, position_error_m, first_t, last_t, n_alerts, uav_ids)"
                " VALUES (?, ?, ?, ?, ?, 1, ?)",
                (alert.lat, alert.lon, alert.position_error_m, alert.t, alert.t, alert.uav_id),
            ).lastrowid
        else:
            inc = next(c for c in candidates if c["incident_id"] == incident_id)
            lat, lon, error = merged_position(inc, alert.lat, alert.lon, alert.position_error_m)
            uavs = sorted(set(inc["uav_ids"].split(",")) | {alert.uav_id})
            db.execute(
                "UPDATE incidents SET lat = ?, lon = ?, position_error_m = ?, first_t = MIN(first_t, ?),"
                " last_t = MAX(last_t, ?), n_alerts = n_alerts + 1, uav_ids = ? WHERE incident_id = ?",
                (lat, lon, error, alert.t, alert.t, ",".join(uavs), incident_id),
            )
        db.execute("UPDATE alerts SET incident_id = ? WHERE alert_id = ?", (incident_id, alert.alert_id))

    @app.post("/api/alerts/{alert_id}/crop")
    def post_crop(alert_id: str, crop: AlertCrop) -> dict[str, str]:
        """Nhận ảnh cắt; gói toạ độ phải tới trước."""
        if crop.alert_id != alert_id:
            raise HTTPException(400, "alert_id trong đường dẫn và trong nội dung không khớp")
        try:
            jpeg = base64.b64decode(crop.jpeg_base64, validate=True)
        except ValueError as error:
            raise HTTPException(400, "jpeg_base64 không hợp lệ") from error
        with sqlite3.connect(db_path) as db:
            if db.execute("SELECT 1 FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone() is None:
                raise HTTPException(409, "Chưa nhận gói toạ độ của cảnh báo này")
            db.execute("INSERT OR IGNORE INTO crops VALUES (?, ?, ?)", (alert_id, jpeg, now_iso()))
        return {"ack": f"{alert_id}:crop"}

    @app.get("/api/alerts")
    def list_alerts(since: str | None = None) -> list[dict[str, Any]]:
        """Danh sách cảnh báo, mới nhất trước; since lọc theo received_at (ISO 8601)."""
        with sqlite3.connect(db_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT a.*, c.alert_id IS NOT NULL AS has_crop FROM alerts a LEFT JOIN crops c USING (alert_id)"
                " WHERE a.received_at > ? ORDER BY a.received_at DESC",
                (since or "",),
            ).fetchall()
        return [dict(row) for row in rows]

    @app.get("/api/incidents")
    def list_incidents() -> list[dict[str, Any]]:
        """Sự cố, mới nhất trước; mỗi sự cố kèm danh sách cảnh báo (mới nhất trước) để mở ảnh cắt."""
        with sqlite3.connect(db_path) as db:
            db.row_factory = sqlite3.Row
            incidents = [dict(r) for r in db.execute("SELECT * FROM incidents ORDER BY last_t DESC")]
            alerts = db.execute(
                "SELECT a.*, c.alert_id IS NOT NULL AS has_crop FROM alerts a LEFT JOIN crops c USING (alert_id)"
                " WHERE a.incident_id IS NOT NULL ORDER BY a.t DESC"
            ).fetchall()
        by_incident: dict[int, list[dict[str, Any]]] = {}
        for row in alerts:
            by_incident.setdefault(row["incident_id"], []).append(dict(row))
        for inc in incidents:
            inc["uav_ids"] = inc["uav_ids"].split(",")
            inc["alerts"] = by_incident.get(inc["incident_id"], [])
        return incidents

    @app.get("/api/alerts/{alert_id}/crop")
    def get_crop(alert_id: str) -> Response:
        with sqlite3.connect(db_path) as db:
            row = db.execute("SELECT jpeg FROM crops WHERE alert_id = ?", (alert_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Chưa có ảnh cắt")
        return Response(row[0], media_type="image/jpeg")

    @app.get("/", response_class=HTMLResponse)
    def map_page() -> str:
        return MAP_HTML.read_text(encoding="utf-8")

    return app


def default_app() -> FastAPI:
    """Factory cho uvicorn; file SQLite lấy từ biến môi trường FLOODEYE_GROUND_DB."""
    return create_app(os.environ.get("FLOODEYE_GROUND_DB", "runs/ground.sqlite"))
