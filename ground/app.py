"""Trạm mặt đất: nhận cảnh báo, bỏ trùng theo alert_id, hiển thị trên bản đồ (TECHNICAL mục 12).

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

from shared.schema import Alert, AlertCrop

MAP_HTML = Path(__file__).with_name("map.html")


def create_app(db_path: Path | str) -> FastAPI:
    """Tạo ứng dụng với một file SQLite; tách hàm để kiểm thử dùng file tạm."""
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
        db.execute("CREATE TABLE IF NOT EXISTS crops (alert_id TEXT PRIMARY KEY, jpeg BLOB NOT NULL, received_at TEXT NOT NULL)")

    app = FastAPI(title="FloodEye – trạm mặt đất")

    def now_iso() -> str:
        # Trạm mặt đất không thuộc pipeline mô phỏng nên dùng đồng hồ thật để ghi lúc nhận.
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    @app.post("/api/alerts")
    def post_alert(alert: Alert) -> dict[str, str]:
        """Nhận gói toạ độ; trùng alert_id vẫn ack nhưng không ghi lại (gửi lại không sinh cảnh báo trùng)."""
        with sqlite3.connect(db_path) as db:
            db.execute(
                "INSERT OR IGNORE INTO alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    alert.alert_id, alert.uav_id, alert.t, alert.lat, alert.lon, alert.position_error_m,
                    alert.altitude_m, alert.cluster_id, alert.confidence, alert.frames_confirmed, alert.model, now_iso(),
                ),
            )
        return {"ack": f"{alert.alert_id}:coords"}

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
