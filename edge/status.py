"""Trạng thái drone gửi về trạm mặt đất và luồng video xem trực tiếp cho demo (TECHNICAL mục 10.6).

StatusReporter gửi UavState mỗi `every_s` giây theo đồng hồ chuyến bay, qua một Transport riêng (không qua outbox): gói
trạng thái cũ vô giá trị nên hỏng thì bỏ, không gửi lại. Khi bọc bằng NetemTransport, mất sóng làm trạm không nhận
được trạng thái, đúng như thực tế; NetemTransport đó có seed riêng nên không đổi chuỗi sự kiện mạng của cảnh báo.

LiveView phát khung đã vẽ dưới dạng MJPEG (multipart/x-mixed-replace) trên một cổng cục bộ, để trang bản đồ nhúng
video bằng thẻ <img>. Chỉ để trình bày: drone thật không gửi video về trạm (TECHNICAL mục 10.4).
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, TextIO

import cv2

from edge.alerts import OutboxMessage, Transport
from edge.georef import Camera, footprint
from shared.schema import Telemetry, UavState


class StatusReporter:
    """Gửi trạng thái drone tối đa một lần mỗi `every_s` giây; ghi mỗi lần gửi vào log JSONL nếu có."""

    def __init__(self, transport: Transport, uav_id: str, every_s: float, log: TextIO | None = None) -> None:
        if every_s <= 0:
            raise ValueError(f"every_s phải dương, nhận được: {every_s}")
        self.transport, self.uav_id, self.every_s, self.log = transport, uav_id, every_s, log
        self.last_t: float | None = None
        self.seq = 0

    def maybe_send(self, t: float, tel: Telemetry, cam: Camera, force: bool = False, **info: Any) -> bool | None:
        """Gửi nếu đã tới hạn (hoặc force); trả về True/False theo ack, None nếu chưa tới hạn."""
        if not force and self.last_t is not None and t - self.last_t < self.every_s - 1e-9:
            return None
        self.last_t = t
        self.seq += 1
        state = UavState(
            uav_id=self.uav_id, seq=self.seq, t=t, lat=tel.lat, lon=tel.lon, alt_m=tel.alt_agl_m, yaw_deg=tel.yaw_deg,
            footprint=footprint(tel, cam), **info,
        )
        msg = OutboxMessage(f"{self.uav_id}:state:{self.seq}", self.uav_id, "state", state.model_dump_json())
        ok = self.transport.send(msg, t)
        if self.log is not None:
            self.log.write(json.dumps({"t": t, "seq": self.seq, "ok": ok, "bytes": len(msg.payload)}) + "\n")
        return ok


class LiveView:
    """Máy chủ MJPEG nhỏ: luôn phát khung mới nhất; trình duyệt chậm thì bỏ khung, không làm chậm pipeline."""

    def __init__(self, port: int, max_width: int = 1280, quality: int = 75) -> None:
        self.max_width, self.quality = max_width, quality
        self._jpeg: bytes | None = None
        self._seq = 0
        self._cond = threading.Condition()
        view = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 (tên do http.server đặt)
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                seen = -1
                try:
                    while True:
                        with view._cond:
                            view._cond.wait_for(lambda: view._seq != seen, timeout=5.0)
                            jpeg, seen = view._jpeg, view._seq
                        if jpeg is None:
                            continue
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                         + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
                except (BrokenPipeError, ConnectionResetError):
                    return

            def log_message(self, *args: Any) -> None:  # im lặng, không in mỗi lần trình duyệt nối
                return

        self.server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def publish(self, image: Any) -> None:
        """Nén khung (thu về max_width) và đánh thức mọi người xem."""
        scale = self.max_width / image.shape[1]
        if scale < 1:
            image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
        if not ok:
            return
        with self._cond:
            self._jpeg, self._seq = buffer.tobytes(), self._seq + 1
            self._cond.notify_all()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
