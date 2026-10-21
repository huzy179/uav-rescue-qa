"""Nguồn telemetry của UAV, truy vấn theo thời gian của khung hình (TECHNICAL mục 7.3)."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Protocol

import numpy as np

from shared.schema import Telemetry

CSV_FIELDS = ["lat", "lon", "alt_agl_m", "yaw_deg", "pitch_deg", "roll_deg"]
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
        """File CSV có cột t, lat, lon, alt_agl_m, yaw_deg (pitch_deg, roll_deg tuỳ chọn)."""
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
