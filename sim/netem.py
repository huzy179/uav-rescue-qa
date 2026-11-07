"""Giả lập đường truyền chập chờn quanh một Transport (TECHNICAL mục 11.1)."""

from __future__ import annotations

import bisect
import random

from edge.alerts import OutboxMessage, Transport


class GilbertElliott:
    """Đường truyền đổi qua lại giữa trạng thái tốt và xấu (mất theo cụm), theo thời gian mô phỏng.

    Thời gian ở mỗi trạng thái theo phân phối mũ với trung bình mean_bad_s, mean_good_s (chuỗi Markov hai trạng thái
    liên tục theo thời gian, dạng Gilbert–Elliott). Bắt đầu ở trạng thái tốt. Tỉ lệ thời gian xấu trung bình là
    mean_bad_s / (mean_bad_s + mean_good_s): đặt bằng xác suất mất gói của mất ngẫu nhiên thì hai cách có cùng tỉ lệ
    mất trung bình, chỉ khác mất rải rác hay theo cụm. Các mốc đổi trạng thái sinh dần khi cần, chỉ phụ thuộc seed.
    """

    def __init__(self, mean_bad_s: float, mean_good_s: float, seed: int = 0) -> None:
        if mean_bad_s <= 0 or mean_good_s <= 0:
            raise ValueError(f"Thời gian trung bình mỗi trạng thái phải dương, nhận được: xấu {mean_bad_s}, tốt {mean_good_s}")
        self.mean_bad_s, self.mean_good_s = mean_bad_s, mean_good_s
        self._rng = random.Random(seed)
        self._switches: list[float] = []  # mốc đổi trạng thái; chỉ số chẵn: tốt → xấu, lẻ: xấu → tốt

    @property
    def bad_fraction(self) -> float:
        """Tỉ lệ thời gian ở trạng thái xấu, tính theo trung bình (không phải của một lần sinh)."""
        return self.mean_bad_s / (self.mean_bad_s + self.mean_good_s)

    def _extend(self, t: float) -> None:
        while not self._switches or self._switches[-1] <= t:
            last = self._switches[-1] if self._switches else 0.0
            mean = self.mean_good_s if len(self._switches) % 2 == 0 else self.mean_bad_s
            self._switches.append(last + self._rng.expovariate(1.0 / mean))

    def bad_at(self, t: float) -> bool:
        """Trạng thái xấu tại thời điểm t (giây, t ≥ 0)."""
        self._extend(t)
        return bisect.bisect_right(self._switches, t) % 2 == 1

    def bad_intervals(self, until: float) -> list[tuple[float, float]]:
        """Các khoảng xấu [bắt đầu, kết thúc) giao với [0, until]."""
        self._extend(until)
        return [(self._switches[i], min(self._switches[i + 1], until))
                for i in range(0, len(self._switches) - 1, 2) if self._switches[i] < until]


class NetemTransport:
    """Mất gói rải rác (Bernoulli), mất theo cụm (Gilbert–Elliott) và các khoảng mất sóng hoàn toàn, theo đồng hồ mô
    phỏng và seed cố định.

    burst = (mean_bad_s, mean_good_s) bật mất theo cụm: ở trạng thái xấu mỗi lần gửi mất với xác suất burst_loss, thêm
    vào mất rải rác loss. Không bật thì chuỗi sự kiện giống hệt trước khi có tuỳ chọn này (kết quả RQ3d giữ nguyên).

    shortcut: chưa có độ trễ truyền và giới hạn băng thông.
    """

    def __init__(
        self, inner: Transport, loss: float = 0.0, outages: list[tuple[float, float]] | None = None, seed: int = 0,
        burst: tuple[float, float] | None = None, burst_loss: float = 1.0,
    ) -> None:
        if not 0.0 <= loss <= 1.0:
            raise ValueError(f"loss phải trong [0, 1], nhận được: {loss}")
        if not 0.0 <= burst_loss <= 1.0:
            raise ValueError(f"burst_loss phải trong [0, 1], nhận được: {burst_loss}")
        self.inner, self.loss, self.outages = inner, loss, outages or []
        self._rng = random.Random(seed)
        self.burst = GilbertElliott(burst[0], burst[1], seed + 104729) if burst else None
        self.burst_loss = burst_loss
        self._burst_rng = random.Random(seed + 130363)

    def link_down(self, now: float) -> bool:
        """Đang mất sóng hẳn hoặc đang ở trạng thái xấu của mất theo cụm (để hiện banner, không rút số ngẫu nhiên)."""
        return any(start <= now < end for start, end in self.outages) or (self.burst is not None and self.burst.bad_at(now))

    def send(self, msg: OutboxMessage, now: float) -> bool:
        # Luôn rút số ngẫu nhiên, kể cả lúc mất sóng, để chuỗi sự kiện chỉ phụ thuộc seed và số lần gửi.
        dropped = self._rng.random() < self.loss
        if self.burst is not None:
            in_burst_drop = self._burst_rng.random() < self.burst_loss
            dropped = dropped or (self.burst.bad_at(now) and in_burst_drop)
        if dropped or any(start <= now < end for start, end in self.outages):
            return False
        return self.inner.send(msg, now)
