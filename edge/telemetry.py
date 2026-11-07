"""Nguồn telemetry của UAV, truy vấn theo thời gian của khung hình (TECHNICAL mục 7.3)."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from typing import Protocol

import numpy as np

from edge.georef import ground_offset_m
from shared.schema import Telemetry

CSV_FIELDS = ["lat", "lon", "alt_agl_m", "yaw_deg", "pitch_deg", "roll_deg", "gps_acc_m"]
REQUIRED = {"t", "lat", "lon", "alt_agl_m", "yaw_deg"}


class TelemetrySource(Protocol):
    def at(self, t: float) -> Telemetry: ...


class SampledTelemetry:
    """Chuỗi mẫu telemetry rời rạc; at(t) nội suy tuyến tính giữa hai mẫu gần nhất."""

    def __init__(self, samples: list[dict[str, float]], source: str = "") -> None:
        if not samples:
            raise ValueError(f"Không có mẫu telemetry nào: {source}")
        missing = REQUIRED - set(samples[0])
        if missing:
            raise ValueError(f"Telemetry {source} thiếu cột: {', '.join(sorted(missing))}")
        samples = sorted(samples, key=lambda row: row["t"])
        self._t = np.array([row["t"] for row in samples])
        self._fields = {name: np.array([row[name] for row in samples]) for name in CSV_FIELDS if name in samples[0]}
        # Mở góc hướng thành chuỗi liên tục để nội suy theo đường ngắn nhất (359° → 1° là +2°).
        self._fields["yaw_deg"] = np.unwrap(self._fields["yaw_deg"], period=360.0)

    @classmethod
    def from_csv(cls, path: Path) -> SampledTelemetry:
        """File CSV có cột t, lat, lon, alt_agl_m, yaw_deg (pitch_deg, roll_deg, gps_acc_m tuỳ chọn)."""
        with path.open(newline="", encoding="utf-8") as f:
            rows = [{key: float(value) for key, value in row.items()} for row in csv.DictReader(f)]
        return cls(rows, str(path))

    @classmethod
    def from_srt(cls, path: Path, alt_offset_m: float = 0.0, default_yaw_deg: float = 0.0) -> SampledTelemetry:
        """File phụ đề .SRT đi kèm video DJI; xem parse_dji_srt."""
        return cls(parse_dji_srt(path.read_text(encoding="utf-8", errors="replace"), alt_offset_m, default_yaw_deg), str(path))

    def at(self, t: float) -> Telemetry:
        """Nội suy tại thời điểm t; ngoài khoảng có dữ liệu thì lấy mẫu đầu hoặc cuối."""
        values = {name: float(np.interp(t, self._t, series)) for name, series in self._fields.items()}
        values["yaw_deg"] %= 360.0
        return Telemetry(t=t, **values)


_NUM = r"(-?\d+(?:\.\d+)?)"
_SRT_TIME = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->")
_SRT_PATTERNS = {
    "lat": re.compile(rf"\blatitude\s*:\s*{_NUM}", re.I),
    "lon": re.compile(rf"\blongt?itude\s*:\s*{_NUM}", re.I),  # một số máy ghi sai chính tả "longtitude"
    "alt": re.compile(rf"\brel_alt\s*:\s*{_NUM}", re.I),
    "yaw": re.compile(rf"\bgb_yaw\s*:\s*{_NUM}", re.I),
    "pitch": re.compile(rf"\bgb_pitch\s*:\s*{_NUM}", re.I),
}
_OLD_GPS = re.compile(rf"GPS\s*\(\s*{_NUM}\s*,\s*{_NUM}")  # Phantom 4 cũ: GPS(kinh độ, vĩ độ, ...)
_OLD_BARO = re.compile(rf"BAROMETER\s*:?\s*{_NUM}", re.I)


def parse_dji_srt(text: str, alt_offset_m: float = 0.0, default_yaw_deg: float = 0.0) -> list[dict[str, float]]:
    """Đọc các khối phụ đề DJI thành mẫu telemetry; t là thời điểm bắt đầu khối.

    Dùng độ cao tương đối (so với điểm cất cánh) cộng alt_offset_m làm độ cao so với mặt nước. Không có
    góc gimbal thì yaw lấy default_yaw_deg. Khối thiếu vị trí hoặc độ cao bị bỏ qua.
    shortcut: mới viết theo định dạng đã biết (Mavic 3/Mini/M30 và Phantom 4), chưa thử trên file thật.
    """
    samples: list[dict[str, float]] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        time_match = _SRT_TIME.search(block)
        if time_match is None:
            continue
        h, m, s, frac = time_match.groups()
        t = int(h) * 3600 + int(m) * 60 + int(s) + int(frac) / 10 ** len(frac)
        found = {key: pattern.search(block) for key, pattern in _SRT_PATTERNS.items()}
        old_gps, old_baro = _OLD_GPS.search(block), _OLD_BARO.search(block)
        if found["lat"] and found["lon"]:
            lat, lon = float(found["lat"].group(1)), float(found["lon"].group(1))
        elif old_gps:
            lon, lat = float(old_gps.group(1)), float(old_gps.group(2))
        else:
            continue
        alt_match = found["alt"] or old_baro
        if alt_match is None:
            continue
        sample = {
            "t": t,
            "lat": lat,
            "lon": lon,
            "alt_agl_m": float(alt_match.group(1)) + alt_offset_m,
            "yaw_deg": float(found["yaw"].group(1)) if found["yaw"] else default_yaw_deg,
        }
        if found["pitch"]:
            sample["pitch_deg"] = float(found["pitch"].group(1))
        samples.append(sample)
    # Có khối có pitch, có khối không: bỏ cột để mọi mẫu cùng cột.
    if any("pitch_deg" not in sample for sample in samples):
        for sample in samples:
            sample.pop("pitch_deg", None)
    return samples


def main() -> None:
    """Kiểm tra nhanh một file .SRT thật: đọc được bao nhiêu khối, khoảng thời gian, độ cao, có góc gimbal không."""
    import argparse

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("srt", type=Path, help="File .SRT đi kèm video DJI")
    path = parser.parse_args().srt
    text = path.read_text(encoding="utf-8", errors="replace")
    n_blocks = len(_SRT_TIME.findall(text))
    samples = parse_dji_srt(text, default_yaw_deg=float("nan"))
    print(f"{path}: đọc được {len(samples)}/{n_blocks} khối phụ đề")
    if not samples:
        first_block = re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip())[0]
        raise SystemExit(f"Không nhận ra định dạng; khối đầu tiên:\n{first_block}\n→ cần thêm biểu thức chính quy trong parse_dji_srt.")
    ts = [s["t"] for s in samples]
    alts = [s["alt_agl_m"] for s in samples]
    has_yaw = not any(np.isnan(s["yaw_deg"]) for s in samples)
    print(f"  t: {ts[0]:.3f} → {ts[-1]:.3f} s, khoảng cách mẫu trung vị {np.median(np.diff(ts)) if len(ts) > 1 else 0:.3f} s")
    print(f"  độ cao tương đối: {min(alts):.1f} → {max(alts):.1f} m (cần --alt-offset-m nếu mặt nước khác điểm cất cánh)")
    print(f"  góc gimbal yaw: {'có' if has_yaw else 'KHÔNG có, phải cho --yaw-deg'}; pitch: {'có' if 'pitch_deg' in samples[0] else 'không'}")
    print(f"  mẫu đầu: {samples[0]}")
    if len(samples) < n_blocks:
        print(f"[cảnh báo] {n_blocks - len(samples)} khối không đọc được (thiếu vị trí hoặc độ cao)")


if __name__ == "__main__":
    main()


class NadirTelemetry:
    """Bọc một nguồn telemetry, ép pitch về −90° (nhìn thẳng xuống): giữ hành vi cũ của phép chiếu khi chưa bật
    --use-pitch, vì mọi kết quả trước 7/11 tính với giả định camera nhìn thẳng xuống (TECHNICAL 8.3)."""

    def __init__(self, inner: TelemetrySource) -> None:
        self.inner = inner

    def at(self, t: float) -> Telemetry:
        return self.inner.at(t).model_copy(update={"pitch_deg": -90.0, "roll_deg": 0.0})


class ShiftedTelemetry:
    """Bọc một nguồn telemetry, đọc giá trị ở t + lag_s: bù độ trễ giữa metadata và khung ảnh (docs/CAI_TIEN.md 3.6).

    lag_s > 0 nghĩa là metadata ghi **trễ** hơn ảnh: giá trị đúng cho khung ở t nằm ở dòng t + lag_s. Trường t của
    kết quả giữ nguyên t của khung.
    """

    def __init__(self, inner: TelemetrySource, lag_s: float) -> None:
        self.inner, self.lag_s = inner, lag_s

    def at(self, t: float) -> Telemetry:
        return self.inner.at(t + self.lag_s).model_copy(update={"t": t})


class SmoothedAngles:
    """Bọc một nguồn telemetry, thay pitch và yaw bằng trung bình trong cửa sổ ±window_s/2 quanh t.

    Góc gimbal trong metadata dao động vài độ giữa các mẫu; khi camera nghiêng, mỗi độ sai đẩy điểm chiếu đi xa
    (TECHNICAL 8.3). Trung bình lấy n_samples điểm đều nhau trong cửa sổ; yaw lấy trung bình theo vectơ đơn vị để
    359° và 1° cho 0°, không phải 180°. Vị trí và độ cao giữ nguyên.
    """

    def __init__(self, inner: TelemetrySource, window_s: float, n_samples: int = 9) -> None:
        if window_s <= 0 or n_samples < 2:
            raise ValueError("window_s phải > 0 và n_samples ≥ 2")
        self.inner, self.window_s, self.n_samples = inner, window_s, n_samples

    def at(self, t: float) -> Telemetry:
        base = self.inner.at(t)
        times = np.linspace(t - self.window_s / 2.0, t + self.window_s / 2.0, self.n_samples)
        samples = [self.inner.at(float(s)) for s in times]
        pitch = float(np.mean([s.pitch_deg for s in samples]))
        yaw_rad = np.radians([s.yaw_deg for s in samples])
        yaw = float(np.degrees(np.arctan2(np.mean(np.sin(yaw_rad)), np.mean(np.cos(yaw_rad))))) % 360.0
        return base.model_copy(update={"pitch_deg": pitch, "yaw_deg": yaw})


def _wrap180(deg: float) -> float:
    """Đưa góc về [−180°, 180°)."""
    return (deg + 180.0) % 360.0 - 180.0


class YawCalibrated:
    """Bọc một nguồn telemetry, ước lượng và trừ lệch cố định của la bàn (docs/CAI_TIEN.md 3.3, TECHNICAL 8.4).

    Khi drone bay thẳng đủ nhanh, hướng di chuyển tính từ hai điểm GPS cách nhau baseline_s giây bằng hướng mũi máy
    (máy bay quét theo đường thẳng, camera nhìn theo hướng bay). Hiệu yaw − hướng di chuyển ở mỗi điểm như vậy là một
    mẫu của lệch la bàn; lệch ước lượng là trung vị các mẫu gần nhất. Nhiễu GPS làm mỗi mẫu sai vài độ (σ GPS chia
    quãng đường baseline), trung vị nhiều mẫu khử phần đó.

    Chỉ dùng telemetry đến thời điểm hỏi (không nhìn trước): mẫu lấy trên lưới thời gian cố định step_s, nên kết quả
    không phụ thuộc thứ tự gọi at(). Điểm bị bỏ khi: chậm hơn min_speed_mps (đứng yên, GPS trôi cho hướng ngẫu
    nhiên), hướng di chuyển hoặc yaw đổi quá max_turn_deg giữa hai đoạn liên tiếp (đang rẽ). Chưa đủ min_samples mẫu,
    hoặc các mẫu tản quá max_spread_deg (yaw thật khác hướng bay, ví dụ drone bay ngang), thì không hiệu chỉnh.
    """

    def __init__(
        self,
        inner: TelemetrySource,
        baseline_s: float = 2.0,
        step_s: float = 0.5,
        min_speed_mps: float = 3.0,
        max_turn_deg: float = 5.0,
        min_samples: int = 10,
        max_samples: int = 120,
        max_spread_deg: float = 10.0,
        max_bias_deg: float = 30.0,
    ) -> None:
        self.inner = inner
        self.baseline_s, self.step_s = baseline_s, step_s
        self.min_speed_mps, self.max_turn_deg = min_speed_mps, max_turn_deg
        self.min_samples, self.max_samples = min_samples, max_samples
        self.max_spread_deg, self.max_bias_deg = max_spread_deg, max_bias_deg
        self._residuals: list[float] = []
        self._history: list[tuple[float, float]] = []  # (thời điểm lưới, lệch ước lượng tại đó)
        self._next_k = 0  # chỉ số lưới tiếp theo chưa xét: thời điểm = k·step_s

    def _course(self, t0: float, t1: float) -> tuple[float, float]:
        """Hướng di chuyển (độ, 0 = Bắc) và vận tốc (m/s) từ t0 tới t1."""
        a, b = self.inner.at(t0), self.inner.at(t1)
        north, east = ground_offset_m(a.lat, a.lon, b.lat, b.lon)
        return math.degrees(math.atan2(east, north)) % 360.0, math.hypot(north, east) / (t1 - t0)

    def _residual(self, tau: float) -> float | None:
        b = self.baseline_s
        if tau < 2 * b:
            return None
        course, speed = self._course(tau - b, tau)
        prev_course, prev_speed = self._course(tau - 2 * b, tau - b)
        if min(speed, prev_speed) < self.min_speed_mps or abs(_wrap180(course - prev_course)) > self.max_turn_deg:
            return None
        yaw, prev_yaw = self.inner.at(tau).yaw_deg, self.inner.at(tau - b).yaw_deg
        if abs(_wrap180(yaw - prev_yaw)) > self.max_turn_deg:
            return None
        return _wrap180(yaw - course)

    def _estimate(self) -> float:
        recent = self._residuals[-self.max_samples :]
        if len(recent) < self.min_samples:
            return 0.0
        median = float(np.median(recent))
        spread = float(np.median([abs(r - median) for r in recent]))
        if spread > self.max_spread_deg or abs(median) > self.max_bias_deg:
            return 0.0
        return median

    def _advance(self, t: float) -> None:
        while self._next_k * self.step_s <= t + 1e-9:
            tau = self._next_k * self.step_s
            residual = self._residual(tau)
            if residual is not None:
                self._residuals.append(residual)
            self._history.append((tau, self._estimate()))
            self._next_k += 1

    def bias_at(self, t: float) -> float:
        """Lệch la bàn ước lượng được, chỉ từ telemetry đến t (độ; dương là la bàn chỉ lệch theo chiều kim đồng hồ)."""
        self._advance(t)
        if not self._history:
            return 0.0
        index = int(math.floor(t / self.step_s + 1e-9))
        return self._history[max(0, min(index, len(self._history) - 1))][1]

    @property
    def n_samples(self) -> int:
        return len(self._residuals)

    def at(self, t: float) -> Telemetry:
        tel = self.inner.at(t)
        bias = self.bias_at(t)
        return tel if bias == 0.0 else tel.model_copy(update={"yaw_deg": (tel.yaw_deg - bias) % 360.0})
