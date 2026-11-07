"""Dùng lại kết quả phát hiện của ô không đổi khi drone gần như đứng yên (docs/CAI_TIEN.md mục 2, results/tile_skip.md).

Khi drone treo tại chỗ, phần lớn ô của khung sau gần như giống hệt khung trước; chạy lại mô hình trên các ô đó là thừa.
TileCache so mỗi ô với chính ô đó ở lần **chạy mô hình gần nhất** (không phải lần thấy gần nhất, để thay đổi chậm không
cộng dồn mà không bị phát hiện) bằng ảnh xám thu nhỏ; ô khác ít hơn ngưỡng thì trả lại box cũ của ô đó. Mỗi ô dùng
lại tối đa max_age lần liên tiếp rồi bắt buộc chạy lại, để người mới xuất hiện không bị bỏ quá lâu.

Chỉ dùng lại khi bên gọi cho phép (drone đứng yên theo telemetry, is_hovering); ngoài ra mọi ô đều chạy. Không import
ultralytics: hàm thuần trên numpy và OpenCV, kiểm thử không cần mô hình.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

TileKey = tuple[int, int, int, int]  # (bề rộng khung, bề cao khung, x, y) sau khi đổi cỡ theo độ cao
TileOutput = tuple[np.ndarray, np.ndarray]  # (box xyxy trong toạ độ ô, conf)


def is_hovering(speed_mps: float | None, yaw_change_deg: float | None, max_speed_mps: float = 0.5,
                max_yaw_change_deg: float = 2.0) -> bool:
    """Drone gần như đứng yên: vận tốc mặt đất và độ đổi hướng trong khoảng vừa qua đều nhỏ (thiếu số liệu thì không)."""
    if speed_mps is None or yaw_change_deg is None:
        return False
    return speed_mps < max_speed_mps and abs(yaw_change_deg) < max_yaw_change_deg


@dataclass
class _Entry:
    signature: np.ndarray
    output: TileOutput
    age: int = 0  # số lần đã dùng lại liên tiếp kể từ lần chạy gần nhất


class TileCache:
    """Quyết định ô nào phải chạy mô hình, và ghép kết quả của ô chạy với kết quả cũ của ô dùng lại."""

    def __init__(self, diff_threshold: float = 4.0, max_age: int = 4, size: int = 32) -> None:
        if diff_threshold < 0 or max_age < 0 or size < 1:
            raise ValueError("diff_threshold, max_age phải ≥ 0 và size ≥ 1")
        self.diff_threshold, self.max_age, self.size = diff_threshold, max_age, size
        self._entries: dict[TileKey, _Entry] = {}
        self._pending: list[tuple[TileKey, np.ndarray, bool]] = []

    def signature(self, tile: np.ndarray) -> np.ndarray:
        """Ảnh xám thu về size × size (float32), đủ để thấy thay đổi cỡ người mà rẻ hơn nhiều so với suy luận."""
        gray = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY) if tile.ndim == 3 else tile
        return cv2.resize(gray, (self.size, self.size), interpolation=cv2.INTER_AREA).astype(np.float32)

    def begin(self, keys: list[TileKey], tiles: list[np.ndarray], allow_reuse: bool) -> list[bool]:
        """Mặt nạ "phải chạy" cho từng ô; gọi finish() với kết quả của đúng các ô phải chạy, theo thứ tự."""
        if len(keys) != len(tiles):
            raise ValueError("keys và tiles phải cùng độ dài")
        self._pending = []
        run = []
        for key, tile in zip(keys, tiles):
            sig = self.signature(tile)
            entry = self._entries.get(key)
            reuse = (
                allow_reuse and entry is not None and entry.age < self.max_age
                and float(np.mean(np.abs(sig - entry.signature))) < self.diff_threshold
            )
            self._pending.append((key, sig, not reuse))
            run.append(not reuse)
        return run

    def finish(self, run_outputs: list[TileOutput]) -> list[TileOutput]:
        """Kết quả cho mọi ô theo thứ tự của begin(); ô chạy cập nhật bộ nhớ, ô dùng lại tăng tuổi."""
        if len(run_outputs) != sum(r for _, _, r in self._pending):
            raise ValueError("Số kết quả khác số ô phải chạy")
        outputs: list[TileOutput] = []
        it = iter(run_outputs)
        for key, sig, ran in self._pending:
            if ran:
                out = next(it)
                self._entries[key] = _Entry(sig, out, 0)
            else:
                entry = self._entries[key]
                entry.age += 1
                out = entry.output
            outputs.append(out)
        self._pending = []
        return outputs
