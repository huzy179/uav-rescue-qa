"""Giả lập thời gian xử lý của thiết bị biên: pipeline chạy trên máy này nhưng "bận" theo hồ sơ của một thiết bị khác.

Không có Jetson (ROADMAP quyết định #2), nên thay vì đo, mỗi khung được gán một độ trễ ước lượng

    độ_trễ_ms = overhead_ms + số_ô × tile_ms + số_lượt_toàn_ảnh × full_ms + megapixel_khung_gốc × resize_ms_per_mpx

(số hạng cuối chỉ khi khung bị thu nhỏ theo độ cao trước khi cắt ô; trên T4 nó lớn hơn cả suy luận, docs/results/rq2_t4.md)

lấy từ hồ sơ thiết bị (configs/devices/*.yaml). Thiết bị bận từ lúc nhận khung t tới t + độ_trễ; khung nguồn tới trong
lúc bận bị bỏ, đúng như trên máy thật, và quyết định (xác nhận, cảnh báo) chỉ có ở t + độ_trễ. Thời gian ở đây là thời
gian mô phỏng theo dấu thời gian khung, không đọc đồng hồ máy. Số trong hồ sơ là ước lượng, không phải số đo
(TECHNICAL mục 14.6): kết quả chỉ dùng để so sánh và để demo, không ghi như số đo trên thiết bị biên.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from edge.detector import tile_origins


class DeviceProfile(BaseModel):
    """Hồ sơ thời gian của một thiết bị, đọc từ YAML; sai tên khoá hay sai kiểu bị báo ngay."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Tên hiển thị trên video và màn hình điều phối")
    calibrated: bool = Field(description="False khi các hệ số chưa lấy từ lần đo RQ2 của chính pipeline này")
    source: str = Field(description="Nguồn của các hệ số và cách tính")
    power_mode: str = Field(description="Chế độ công suất giả định, ví dụ MAXN; Jetson ở chế độ thấp hơn chạy chậm hơn")
    overhead_ms: float = Field(ge=0, description="Phần cố định mỗi khung: đọc khung, cắt ô, gộp box, georef")
    tile_ms: float = Field(gt=0, description="Suy luận một ô (tile, mặc định 640)")
    full_ms: float = Field(gt=0, description="Suy luận một lượt toàn ảnh (imgsz, mặc định 1280)")
    resize_ms_per_mpx: float = Field(0.0, ge=0, description="Thu nhỏ khung trước khi cắt ô, ms cho mỗi megapixel khung gốc")

    def latency_ms(self, n_tiles: int, n_full: int, resize_mpx: float = 0.0) -> float:
        """Độ trễ ước lượng của một khung có n_tiles ô, n_full lượt toàn ảnh, và resize_mpx megapixel phải thu nhỏ
        (0 khi không đổi cỡ khung)."""
        return self.overhead_ms + n_tiles * self.tile_ms + n_full * self.full_ms + resize_mpx * self.resize_ms_per_mpx


def load_profile(path: Path) -> DeviceProfile:
    """Đọc hồ sơ thiết bị từ file YAML."""
    return DeviceProfile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def inference_counts(
    width: int, height: int, scale: float, mode: str, tile: int, overlap: float, full_pass: bool = False
) -> tuple[int, int]:
    """Số ô và số lượt toàn ảnh mà YoloDetector.detect chạy cho một khung, tính từ kích thước khung.

    Cùng cách cắt với detector (thu nhỏ theo scale rồi tile_origins), để chế độ phát lại (--replay, không chạy mô
    hình) vẫn biết khung đó tốn bao nhiêu suy luận.
    """
    if mode == "full":
        return 0, 1
    if scale != 1.0:
        width, height = max(1, round(width / scale)), max(1, round(height / scale))
    n_tiles = len(tile_origins(width, tile, overlap)) * len(tile_origins(height, tile, overlap))
    return n_tiles, int(full_pass)


class BusyDevice:
    """Theo dõi thiết bị đang bận tới lúc nào (giây, thời gian mô phỏng)."""

    def __init__(self, profile: DeviceProfile) -> None:
        self.profile = profile
        self.busy_until = 0.0
        self.n_done = 0
        self.n_skipped = 0
        self.last_latency_ms = 0.0

    def ready(self, t: float) -> bool:
        """Khung tới lúc t có được nhận không; không thì đếm là bỏ."""
        if t + 1e-9 < self.busy_until:
            self.n_skipped += 1
            return False
        return True

    def run(self, t: float, n_tiles: int, n_full: int, resize_mpx: float = 0.0) -> float:
        """Nhận khung lúc t; trả về lúc xử lý xong (giây)."""
        self.last_latency_ms = self.profile.latency_ms(n_tiles, n_full, resize_mpx)
        self.busy_until = t + self.last_latency_ms / 1000.0
        self.n_done += 1
        return self.busy_until

    def achieved_fps(self, t: float) -> float:
        """Số khung đã xử lý chia cho thời gian đã trôi (khung/giây); 0 trước giây đầu tiên."""
        return self.n_done / t if t >= 1.0 else 0.0
