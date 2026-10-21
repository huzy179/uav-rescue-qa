"""Kiểm tra nội suy telemetry và chuyến bay giả lập."""

from pathlib import Path

import pytest

from edge.georef import ground_offset_m
from edge.telemetry import SampledTelemetry, parse_dji_srt
from sim.flight import StraightFlight


def test_csv_interpolation_and_yaw_wrap(tmp_path: Path) -> None:
    """Nội suy tuyến tính; góc hướng đi đường ngắn nhất 359° → 1°; ngoài khoảng thì giữ mẫu biên."""
    path = tmp_path / "tel.csv"
    path.write_text("t,lat,lon,alt_agl_m,yaw_deg\n0,21.0,105.0,50,359\n2,21.002,105.0,60,1\n", encoding="utf-8")
    telemetry = SampledTelemetry.from_csv(path)
    mid = telemetry.at(1.0)
    assert (mid.lat, mid.alt_agl_m) == pytest.approx((21.001, 55.0))
    assert mid.yaw_deg == pytest.approx(0.0, abs=1e-9) or mid.yaw_deg == pytest.approx(360.0)
    assert telemetry.at(0.5).yaw_deg == pytest.approx(359.5)
    assert telemetry.at(10.0).alt_agl_m == pytest.approx(60.0)
    assert mid.pitch_deg == -90.0


def test_csv_missing_column(tmp_path: Path) -> None:
    path = tmp_path / "tel.csv"
    path.write_text("t,lat,lon\n0,21,105\n", encoding="utf-8")
    with pytest.raises(ValueError, match="alt_agl_m"):
        SampledTelemetry.from_csv(path)


def test_straight_flight_moves_along_heading() -> None:
    flight = StraightFlight(21.0, 105.8, 50.0, 10.0, yaw_deg=90.0)
    tel = flight.at(3.0)
    assert ground_offset_m(21.0, 105.8, tel.lat, tel.lon) == pytest.approx((0.0, 30.0), abs=1e-6)
    assert (tel.alt_agl_m, tel.yaw_deg) == (50.0, 90.0)


SRT_NEW = """1
00:00:00,000 --> 00:00:00,033
<font size="28">FrameCnt: 1, DiffTime: 33ms
2026-10-01 10:00:00.000
[iso: 100] [shutter: 1/1000.0] [fnum: 2.8] [focal_len: 24.00] [latitude: 21.028500] [longitude: 105.854200] [rel_alt: 50.000 abs_alt: 62.000] [gb_yaw: -90.0 gb_pitch: -90.0 gb_roll: 0.0] </font>

2
00:00:01,000 --> 00:00:01,033
<font size="28">FrameCnt: 31, DiffTime: 33ms
[latitude: 21.028600] [longitude: 105.854200] [rel_alt: 52.000 abs_alt: 64.000] [gb_yaw: -90.0 gb_pitch: -90.0 gb_roll: 0.0] </font>
"""

SRT_OLD = """1
00:00:00,000 --> 00:00:01,000
HOME(105.8542,21.0285) 2026.10.01 10:00:00
GPS(105.8543,21.0286,19) BAROMETER:48.5
ISO:100 Shutter:500 EV:0 Fnum:F2.8

2
00:00:01,000 --> 00:00:02,000
no position in this block
"""


def test_parse_dji_srt_new_format() -> None:
    samples = parse_dji_srt(SRT_NEW, alt_offset_m=-2.0)
    assert [s["t"] for s in samples] == [0.0, 1.0]
    assert samples[0] == {"t": 0.0, "lat": 21.0285, "lon": 105.8542, "alt_agl_m": 48.0, "yaw_deg": -90.0, "pitch_deg": -90.0}
    assert samples[1]["alt_agl_m"] == 50.0


def test_parse_dji_srt_old_format_lon_first_and_skips_empty_block() -> None:
    samples = parse_dji_srt(SRT_OLD, default_yaw_deg=45.0)
    assert samples == [{"t": 0.0, "lat": 21.0286, "lon": 105.8543, "alt_agl_m": 48.5, "yaw_deg": 45.0}]


def test_srt_file_interpolates(tmp_path: Path) -> None:
    path = tmp_path / "DJI_0001.SRT"
    path.write_text(SRT_NEW, encoding="utf-8")
    tel = SampledTelemetry.from_srt(path).at(0.5)
    assert (tel.lat, tel.alt_agl_m, tel.yaw_deg) == pytest.approx((21.02855, 51.0, 270.0))
