"""Trạm mặt đất: nhận cảnh báo, bỏ trùng theo alert_id, gộp thành sự cố, hiển thị trên bản đồ (TECHNICAL mục 12).

Chạy: FLOODEYE_GROUND_DB=runs/ground.sqlite .venv/bin/python -m uvicorn --factory ground.app:default_app --port 8000
Bản đồ không cần internet: Leaflet đóng gói trong ground/static/, ô bản đồ đi qua /tiles và được giữ lại trong
FLOODEYE_TILE_CACHE (mặc định runs/ground/tiles) sau lần xem đầu, nên vùng đã xem khi diễn tập vẫn hiện khi mất mạng.
Không import torch, ultralytics hay opencv; chỉ dùng shared/.
"""

from __future__ import annotations

import asyncio
import base64
import os
import sqlite3
import threading
import time
import urllib.request
import zlib
from xml.sax.saxutils import escape, quoteattr
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from ground.incidents import MergeRule, choose_incident, merged_position
from ground.priority import STATUSES, TAGS, PriorityRule, rank
from shared.schema import R95_FACTOR, Alert, AlertCrop, UavState

MAP_HTML = Path(__file__).with_name("map.html")
MAX_TRACK = 7200  # điểm đường bay giữ lại mỗi drone (2 giờ nếu một gói mỗi giây)
STATIC_DIR = Path(__file__).with_name("static")
# Ô ảnh vệ tinh và bản đồ đường của Esri (không cần khoá; tile.openstreetmap.org không trả lời từ mạng của dự án).
TILE_SOURCES = {
    "satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "streets": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
}


def fetch_url(url: str) -> bytes:
    """Tải một ô bản đồ; hết 3 giây thì coi như mất mạng."""
    request = urllib.request.Request(url, headers={"User-Agent": "FloodEye-ground/0.1"})
    with urllib.request.urlopen(request, timeout=3) as response:
        return response.read()


def image_media_type(data: bytes) -> str:
    """Kiểu ảnh theo mấy byte đầu (Esri trả JPEG hoặc PNG tuỳ ô)."""
    return "image/png" if data.startswith(b"\x89PNG") else "image/jpeg"


class TruthPerson(BaseModel):
    """Một người thật trong lớp đáp án (tools/make_truth_layer.py): khoảng thời gian drone thấy và đường đi trên mặt đất."""

    model_config = ConfigDict(extra="forbid")

    id: int
    t_in: float
    t_out: float
    track: list[tuple[float, float, float]]  # (t, lat, lon), t tăng dần


class TruthLayer(BaseModel):
    """Lớp đáp án cho demo: chỉ để đối chiếu trực quan trên bản đồ, không thay cho chỉ số trong docs/results."""

    model_config = ConfigDict(extra="forbid")

    source: str = ""
    note: str = ""
    r_match_m: float = 10.0  # sự cố cách người ≤ r_match_m thì coi là tìm thấy người đó (như r_eval của RQ3)
    tail_s: float = 10.0  # người rời khung quá tail_s mà chưa có sự cố nào thì coi là bỏ sót
    people: list[TruthPerson]


class IncidentUpdate(BaseModel):
    """Người vận hành cập nhật một sự cố: trạng thái và thẻ (dưới nước, trên mái); trường không gửi thì giữ nguyên."""

    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    tag: str | None = None
    clear_tag: bool = False


def create_app(
    db_path: Path | str, rule: MergeRule | None = None, priority_rule: PriorityRule | None = None,
    tile_cache: Path | str = "runs/ground/tiles", fetch: Callable[[str], bytes] = fetch_url,
) -> FastAPI:
    """Tạo ứng dụng với một file SQLite; tách hàm để kiểm thử dùng file tạm (và hàm tải ô giả)."""
    rule = rule or MergeRule()
    priority_rule = priority_rule or PriorityRule()
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
        columns = {row[1] for row in db.execute("PRAGMA table_info(incidents)")}
        if "status" not in columns:  # file cũ, trước khi có xếp ưu tiên
            db.execute("ALTER TABLE incidents ADD COLUMN status TEXT NOT NULL DEFAULT 'open'")
        if "tag" not in columns:
            db.execute("ALTER TABLE incidents ADD COLUMN tag TEXT")
        if "group_size" not in columns:  # file cũ, trước khi có ước tính số người
            db.execute("ALTER TABLE incidents ADD COLUMN group_size INTEGER NOT NULL DEFAULT 1")
        if "group_size" not in {row[1] for row in db.execute("PRAGMA table_info(alerts)")}:
            db.execute("ALTER TABLE alerts ADD COLUMN group_size INTEGER NOT NULL DEFAULT 1")
        db.execute("CREATE TABLE IF NOT EXISTS crops (alert_id TEXT PRIMARY KEY, jpeg BLOB NOT NULL, received_at TEXT NOT NULL)")

    app = FastAPI(title="FloodEye – trạm mặt đất")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    tile_cache = Path(tile_cache)

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
                " confidence, frames_confirmed, model, received_at, group_size) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    alert.alert_id, alert.uav_id, alert.t, alert.lat, alert.lon, alert.position_error_m,
                    alert.altitude_m, alert.cluster_id, alert.confidence, alert.frames_confirmed, alert.model, now_iso(),
                    alert.group_size,
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
        incident_id = choose_incident(
            alert.lat, alert.lon, alert.position_error_m, alert.t, candidates, rule, alert.uav_id
        )
        if incident_id is None:
            incident_id = db.execute(
                "INSERT INTO incidents (lat, lon, position_error_m, first_t, last_t, n_alerts, uav_ids, group_size)"
                " VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                (alert.lat, alert.lon, alert.position_error_m, alert.t, alert.t, alert.uav_id, alert.group_size),
            ).lastrowid
        else:
            inc = next(c for c in candidates if c["incident_id"] == incident_id)
            lat, lon, error = merged_position(inc, alert.lat, alert.lon, alert.position_error_m)
            uavs = sorted(set(inc["uav_ids"].split(",")) | {alert.uav_id})
            db.execute(
                "UPDATE incidents SET lat = ?, lon = ?, position_error_m = ?, first_t = MIN(first_t, ?),"
                " last_t = MAX(last_t, ?), n_alerts = n_alerts + 1, uav_ids = ?, group_size = MAX(group_size, ?)"
                " WHERE incident_id = ?",
                (lat, lon, error, alert.t, alert.t, ",".join(uavs), alert.group_size, incident_id),
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
        """Sự cố theo ưu tiên giảm dần (ground/priority.py), sự cố đã đóng xếp cuối; mỗi sự cố kèm điểm, lý do và
        danh sách cảnh báo (mới nhất trước) để mở ảnh cắt."""
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
            inc["max_confidence"] = max((a["confidence"] for a in inc["alerts"]), default=0.0)
        return rank(incidents, priority_rule)

    @app.get("/api/incidents.gpx")
    def incidents_gpx() -> Response:
        """Sự cố đang mở dạng GPX (điểm mốc theo thứ tự ưu tiên), để nạp vào máy định vị cầm tay hay điện thoại của đội
        cứu hộ khi không có bản đồ trạm. Tên điểm "FE-<số sự cố>", mô tả gồm ưu tiên, lý do, bán kính vùng tìm 95%."""
        rows = [inc for inc in list_incidents() if inc["status"] == "open"]
        points = []
        for inc in rows:
            desc = (f"Ưu tiên {vn(inc['priority'], 2)}; {'; '.join(inc['priority_reasons'])}; "
                    f"vùng tìm 95% bán kính {vn(R95_FACTOR * inc['position_error_m'], 1)} m; {inc['n_alerts']} cảnh báo"
                    + (f"; nhóm khoảng {inc['group_size']} người" if inc.get("group_size", 1) > 1 else ""))
            points.append(
                f'  <wpt lat="{inc["lat"]:.7f}" lon="{inc["lon"]:.7f}"><name>FE-{inc["incident_id"]}</name>'
                f"<desc>{escape(desc)}</desc><sym>Flag, Red</sym></wpt>"
            )
        gpx = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               f'<gpx version="1.1" creator={quoteattr("FloodEye trạm mặt đất")} xmlns="http://www.topografix.com/GPX/1/1">\n'
               + "\n".join(points) + "\n</gpx>\n")
        return Response(gpx, media_type="application/gpx+xml",
                        headers={"Content-Disposition": 'attachment; filename="floodeye_su_co.gpx"'})

    @app.patch("/api/incidents/{incident_id}")
    def update_incident(incident_id: int, update: IncidentUpdate) -> dict[str, Any]:
        """Người vận hành gắn thẻ (water, roof) hoặc đóng sự cố (resolved, false_alarm); open để mở lại."""
        if update.status is not None and update.status not in STATUSES:
            raise HTTPException(400, f"status phải là một trong {sorted(STATUSES)}")
        if update.tag is not None and update.tag not in TAGS:
            raise HTTPException(400, f"tag phải là một trong {sorted(TAGS)}")
        with sqlite3.connect(db_path) as db:
            if db.execute("SELECT 1 FROM incidents WHERE incident_id = ?", (incident_id,)).fetchone() is None:
                raise HTTPException(404, "Không có sự cố này")
            if update.status is not None:
                db.execute("UPDATE incidents SET status = ? WHERE incident_id = ?", (update.status, incident_id))
            if update.tag is not None or update.clear_tag:
                db.execute("UPDATE incidents SET tag = ? WHERE incident_id = ?", (update.tag, incident_id))
        return {"incident_id": incident_id, "status": update.status, "tag": update.tag}

    @app.get("/api/alerts/{alert_id}/crop")
    def get_crop(alert_id: str) -> Response:
        with sqlite3.connect(db_path) as db:
            row = db.execute("SELECT jpeg FROM crops WHERE alert_id = ?", (alert_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Chưa có ảnh cắt")
        return Response(row[0], media_type="image/jpeg")

    @app.get("/api/stream")
    async def stream(max_events: int | None = None) -> StreamingResponse:
        """Server-Sent Events: gửi một sự kiện "update" mỗi khi có cảnh báo, ảnh cắt hay thay đổi sự cố mới.

        Trạm hỏi SQLite mỗi 0,5 giây phía máy chủ (một truy vấn nhẹ cho mọi trình duyệt) thay vì mỗi trình duyệt
        hỏi lại toàn bộ danh sách mỗi 2 giây. max_events để kiểm thử.
        """
        async def events() -> Any:
            last, sent = None, 0
            while max_events is None or sent < max_events:
                token = change_token(db_path)
                if token != last:
                    last, sent = token, sent + 1
                    yield f"event: update\ndata: {token}\n\n"
                await asyncio.sleep(0.5)

        return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    @app.get("/tiles/{layer}/{z}/{x}/{y}")
    def tile(layer: str, z: int, x: int, y: int) -> Response:
        """Ô bản đồ: đọc từ bộ nhớ đệm trên đĩa; chưa có thì tải về rồi giữ lại. Mất mạng và chưa có thì 404.

        Chỉ giữ ô đã được xem (như bộ nhớ đệm của trình duyệt, nhưng còn sau khi tắt máy), không tải trước cả vùng:
        điều khoản của Esri hạn chế tải hàng loạt để dùng ngoại tuyến.
        """
        if layer not in TILE_SOURCES or not (0 <= z <= 20 and 0 <= x < 2**z and 0 <= y < 2**z):
            raise HTTPException(404, "Ô bản đồ không hợp lệ")
        path = tile_cache / layer / str(z) / str(x) / f"{y}.img"
        if not path.exists():
            try:
                data = fetch(TILE_SOURCES[layer].format(z=z, x=x, y=y))
            except OSError:
                raise HTTPException(404, "Mất mạng và chưa có ô này trong bộ nhớ đệm") from None
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        data = path.read_bytes()
        return Response(data, media_type=image_media_type(data), headers={"Cache-Control": "max-age=86400"})

    # Trạng thái drone giữ trong bộ nhớ (không cần bền: gói mới thay gói cũ mỗi giây). Mỗi drone: gói mới nhất, lúc
    # nhận theo đồng hồ của trạm (để biết đã im lặng bao lâu), đường bay và các vùng camera đã nhìn (vùng đã quét).
    uavs: dict[str, dict[str, Any]] = {}
    uav_lock = threading.Lock()

    @app.post("/api/uav/state")
    def post_uav_state(state: UavState) -> dict[str, str]:
        """Nhận trạng thái drone; gói cũ hơn gói đã có (tới muộn) chỉ được ack, không ghi đè."""
        with uav_lock:
            item = uavs.setdefault(state.uav_id, {"track": [], "footprints": [], "state": None})
            if item["state"] is None or state.t >= item["state"]["t"]:
                # Điểm gửi bù (trail) của đoạn mất sóng vào trước, rồi tới điểm hiện tại; chỉ lấy điểm mới hơn điểm cuối.
                last_t = item["state"]["t"] if item["state"] else float("-inf")
                for point in [*sorted(state.trail, key=lambda p: p.t), state]:
                    if point.t > last_t or item["state"] is None:
                        item["track"].append((point.lat, point.lon))
                        item["footprints"].append(point.footprint)
                item["state"], item["received"] = state.model_dump(exclude={"trail"}), time.monotonic()
                del item["track"][:-MAX_TRACK], item["footprints"][:-MAX_TRACK]
        return {"ack": f"{state.uav_id}:state:{state.seq}"}

    @app.get("/api/uavs")
    def list_uavs() -> list[dict[str, Any]]:
        """Mọi drone: trạng thái mới nhất, số giây từ lần nhận cuối (age_s), đường bay và vùng đã quét."""
        now = time.monotonic()
        with uav_lock:
            return [
                {**item["state"], "age_s": now - item["received"], "track": list(item["track"]), "footprints": list(item["footprints"])}
                for item in uavs.values()
            ]

    truth: dict[str, Any] = {}

    @app.post("/api/reset")
    def reset(confirm: bool = False) -> dict[str, bool]:
        """Xoá mọi cảnh báo, ảnh cắt, sự cố, trạng thái drone và lớp đáp án, để bắt đầu một lần chạy mới (sân thử của
        console, demo). Cần ?confirm=true để không xoá nhầm."""
        if not confirm:
            raise HTTPException(400, "Thêm ?confirm=true để xoá toàn bộ dữ liệu của trạm")
        with sqlite3.connect(db_path) as db:
            db.execute("DELETE FROM crops")
            db.execute("DELETE FROM alerts")
            db.execute("DELETE FROM incidents")
        with uav_lock:
            uavs.clear()
        truth.clear()
        return {"reset": True}

    @app.post("/api/truth")
    def post_truth(layer: TruthLayer) -> dict[str, int]:
        """Nạp lớp đáp án (thay lớp cũ)."""
        truth.clear()
        truth.update(layer.model_dump())
        return {"people": len(layer.people)}

    @app.get("/api/truth")
    def get_truth() -> dict[str, Any]:
        """Lớp đáp án đã nạp; chưa nạp thì people rỗng."""
        return truth or {"people": []}

    @app.get("/", response_class=HTMLResponse)
    def map_page() -> str:
        return MAP_HTML.read_text(encoding="utf-8")

    return app


def vn(x: float, digits: int) -> str:
    """Số thập phân kiểu Việt Nam (dấu phẩy), cho chữ hiển thị cho người vận hành."""
    return f"{x:.{digits}f}".replace(".", ",")


def change_token(db_path: str) -> str:
    """Chuỗi đổi khi có cảnh báo, ảnh cắt mới hoặc người vận hành cập nhật sự cố."""
    with sqlite3.connect(db_path) as db:
        n_alerts, n_crops = db.execute("SELECT (SELECT COUNT(*) FROM alerts), (SELECT COUNT(*) FROM crops)").fetchone()
        incidents = db.execute("SELECT COUNT(*), TOTAL(n_alerts), GROUP_CONCAT(status || COALESCE(tag, ''), '') FROM incidents").fetchone()
    return f"{n_alerts}-{n_crops}-{incidents[0]}-{int(incidents[1])}-{zlib.crc32((incidents[2] or '').encode()):x}"


def default_app() -> FastAPI:
    """Factory cho uvicorn; file SQLite lấy từ biến môi trường FLOODEYE_GROUND_DB."""
    return create_app(
        os.environ.get("FLOODEYE_GROUND_DB", "runs/ground.sqlite"),
        tile_cache=os.environ.get("FLOODEYE_TILE_CACHE", "runs/ground/tiles"),
    )
