"""Kiểu dữ liệu dùng chung giữa các khối của pipeline (TECHNICAL mục 7.1)."""

from __future__ import annotations

from pydantic import BaseModel, Field

Box = tuple[float, float, float, float]  # x1, y1, x2, y2 trên ảnh gốc (pixel)
# Mã chỉ gồm chữ, số, "_", ".", "-": an toàn khi ghép vào URL và HTML của trạm mặt đất.
ID_PATTERN = r"^[A-Za-z0-9_.-]{1,64}$"


class Telemetry(BaseModel):
    """Trạng thái UAV tại một thời điểm."""

    t: float  # giây, theo đồng hồ của chuyến bay
    lat: float  # độ, WGS84
    lon: float
    alt_agl_m: float  # độ cao so với mặt đất/mặt nước, KHÔNG phải so với mực nước biển
    yaw_deg: float  # hướng của đỉnh ảnh, 0 = Bắc, theo chiều kim đồng hồ
    pitch_deg: float = -90.0  # -90 = nhìn thẳng xuống
    roll_deg: float = 0.0


class Detection(BaseModel):
    """Một người phát hiện được trong một khung."""

    frame_id: int
    t: float
    box_px: Box
    conf: float
    lat: float | None = None  # điền bởi georef
    lon: float | None = None


class Confirmation(BaseModel):
    """Một cụm vừa đủ số lần thấy để cảnh báo; mỗi cụm chỉ sinh một lần."""

    cluster_id: int
    t: float
    lat: float
    lon: float
    frames_seen: int  # số khung thấy cụm trong cửa sổ đếm
    confidence: float  # conf trung bình của các lần thấy đó
    frame_id: int  # khung của lần thấy cuối, dùng để cắt ảnh gửi kèm cảnh báo
    box_px: Box


class Alert(BaseModel):
    """Gói toạ độ gửi về trạm mặt đất (vài trăm byte); luôn gửi trước ảnh cắt."""

    schema_version: int = 1
    alert_id: str = Field(pattern=ID_PATTERN)  # "<uav_id>-<số thứ tự>", duy nhất, dùng để bỏ trùng
    uav_id: str = Field(pattern=ID_PATTERN)
    t: float  # giây theo đồng hồ chuyến bay (pipeline không đọc đồng hồ máy)
    lat: float
    lon: float
    position_error_m: float
    altitude_m: float
    cluster_id: int
    confidence: float
    frames_confirmed: int
    box_px: tuple[int, int, int, int]
    model: str


class AlertCrop(BaseModel):
    """Ảnh cắt quanh người, gửi sau gói toạ độ cùng alert_id."""

    alert_id: str = Field(pattern=ID_PATTERN)
    jpeg_base64: str
