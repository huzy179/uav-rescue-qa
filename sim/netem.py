"""Giả lập đường truyền chập chờn quanh một Transport (TECHNICAL mục 11.1)."""

from __future__ import annotations

import random

from edge.alerts import OutboxMessage, Transport


class NetemTransport:
    """Mất gói rải rác (Bernoulli) và các khoảng mất sóng hoàn toàn, theo đồng hồ mô phỏng và seed cố định.

    shortcut: chưa có mất gói theo cụm (Gilbert–Elliott), độ trễ và giới hạn băng thông; thêm khi làm RQ3.
    """

    def __init__(
        self, inner: Transport, loss: float = 0.0, outages: list[tuple[float, float]] | None = None, seed: int = 0
    ) -> None:
        if not 0.0 <= loss <= 1.0:
            raise ValueError(f"loss phải trong [0, 1], nhận được: {loss}")
        self.inner, self.loss, self.outages = inner, loss, outages or []
        self._rng = random.Random(seed)

    def send(self, msg: OutboxMessage, now: float) -> bool:
        # Luôn rút số ngẫu nhiên, kể cả lúc mất sóng, để chuỗi sự kiện chỉ phụ thuộc seed và số lần gửi.
        dropped = self._rng.random() < self.loss
        if dropped or any(start <= now < end for start, end in self.outages):
            return False
        return self.inner.send(msg, now)
