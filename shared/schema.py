"""Kiểu dữ liệu dùng chung giữa các khối của pipeline (TECHNICAL mục 7.1)."""

from __future__ import annotations

from pydantic import BaseModel, Field

Box = tuple[float, float, float, float]  # x1, y1, x2, y2 trên ảnh gốc (pixel)
# Mã chỉ gồm chữ, số, "_", ".", "-": an toàn khi ghép vào URL và HTML của trạm mặt đất.
ID_PATTERN = r"^[A-Za-z0-9_.-]{1,64}$"
# Sai số mặt đất hai chiều, mỗi trục Gauss σ: P(r ≤ kσ) = 1 − exp(−k²/2). Vùng chứa 95 % có bán kính √(−2 ln 0,05)·σ
# ≈ 2,448σ; position_error_m của cảnh báo là 1σ (docs/results/rq3_geoerr.md). Dùng chung cho edge, eval và trạm.
R95_FACTOR = 2.4477468306808166
# Bán kính đếm người cùng nhóm khi xác nhận; bằng bán kính trạm gộp cảnh báo thành sự cố (ground/incidents.py), để
# "số người ước tính" của một sự cố khớp với những người bị gộp vào nó.
GROUP_RADIUS_M = 5.0


class Telemetry(BaseModel):
    """Trạng thái UAV tại một thời điểm."""

    t: float  # giây, theo đồng hồ của chuyến bay
    lat: float  # độ, WGS84
    lon: float
    alt_agl_m: float  # độ cao so với mặt đất/mặt nước, KHÔNG phải so với mực nước biển
    yaw_deg: float  # hướng của đỉnh ảnh, 0 = Bắc, theo chiều kim đồng hồ
    pitch_deg: float = -90.0  # -90 = nhìn thẳng xuống
    roll_deg: float = 0.0
    # Độ chính xác ngang do bộ thu GPS tự báo, quy về độ lệch chuẩn mỗi trục (m); None khi nguồn không có.
    gps_acc_m: float | None = None


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
    group_size: int = 1  # số phát hiện cùng khung trong GROUP_RADIUS_M quanh cụm (kể cả cụm): ước tính số người ở đó


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
    group_size: int = 1  # ước tính số người quanh vị trí này (Confirmation.group_size); trường mới, mặc định 1


class AlertCrop(BaseModel):
    """Ảnh cắt quanh người, gửi sau gói toạ độ cùng alert_id."""

    alert_id: str = Field(pattern=ID_PATTERN)
    jpeg_base64: str


class TrailPoint(BaseModel):
    """Một điểm đường bay kèm vùng camera nhìn, drone gửi bù khi các gói trạng thái trước đó bị mất."""

    t: float
    lat: float
    lon: float
    footprint: list[tuple[float, float]]


class UavState(BaseModel):
    """Gói trạng thái drone gửi về trạm mỗi giây hoặc vài giây (vài trăm byte), để bản đồ hiện drone, vùng camera
    đang nhìn và đường truyền còn sống hay không. Gửi một lần, không gửi lại: gói cũ không còn giá trị."""

    schema_version: int = 1
    uav_id: str = Field(pattern=ID_PATTERN)
    seq: int = 0  # số thứ tự gói, trạm ack "<uav_id>:state:<seq>"
    t: float  # giây theo đồng hồ chuyến bay
    lat: float
    lon: float
    alt_m: float
    yaw_deg: float
    speed_mps: float | None = None
    footprint: list[tuple[float, float]]  # (lat, lon) bốn góc ảnh trên mặt đất (edge.georef.footprint)
    fps: float | None = None  # số khung xử lý mỗi giây đạt được
    pending_alerts: int = 0  # gói đang chờ trong outbox (toạ độ và ảnh cắt)
    alerts_total: int = 0  # số cảnh báo drone đã tạo
    device: str | None = None  # tên hồ sơ thiết bị giả lập, nếu có
    telemetry_real: bool = True  # False khi pipeline dùng đường bay giả lập
    done: bool = False  # chuyến bay đã kết thúc
    # Tự hiệu chỉnh la bàn (--yaw-calib): lệch đang trừ (độ, 0 khi chưa đủ mẫu) và số mẫu bay thẳng đã dùng; None khi tắt.
    yaw_bias_deg: float | None = None
    yaw_calib_samples: int | None = None
    # Điểm đường bay của các gói trạng thái chưa tới trạm (mất sóng), cũ trước mới; gửi bù để vùng đã quét trên bản đồ
    # không bị thủng ở đoạn mất sóng. Rỗng khi gói trước tới đủ.
    trail: list[TrailPoint] = []
