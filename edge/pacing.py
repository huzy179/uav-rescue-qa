"""Giữ nhịp thời gian thực cho demo: chờ tới khi đồng hồ thật bắt kịp thời gian mô phỏng.

Chỉ dùng khi trình bày (--realtime). Không đổi kết quả nào: pipeline vẫn chạy theo dấu thời gian khung, ở đây chỉ ngủ
cho đủ để cảnh báo hiện trên trạm mặt đất đúng lúc như một chuyến bay thật. Đồng hồ thật đọc bằng perf_counter như
phần đo thời gian xử lý (ROADMAP mục 3.2).
"""

from __future__ import annotations

import time
from collections.abc import Callable


class RealtimePacer:
    """Ngủ để thời gian thật đã trôi (nhân speed) không nhỏ hơn thời gian mô phỏng t."""

    def __init__(
        self, speed: float = 1.0, clock: Callable[[], float] = time.perf_counter, sleep: Callable[[float], None] = time.sleep
    ) -> None:
        if speed <= 0:
            raise ValueError(f"speed phải dương, nhận được {speed}")
        self.speed, self._clock, self._sleep = speed, clock, sleep
        self._start: float | None = None

    def wait_until(self, t: float) -> None:
        """Lần gọi đầu đặt mốc 0; các lần sau chờ tới mốc + t / speed. Chậm hơn thời gian thực thì không chờ."""
        now = self._clock()
        if self._start is None:
            self._start = now - t / self.speed
            return
        delay = self._start + t / self.speed - now
        if delay > 0:
            self._sleep(delay)
