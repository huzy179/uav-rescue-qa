"""Kiểm tra sân thử: giới hạn tham số, lệnh dựng ra đúng tuỳ chọn, bảng so sánh chỉ giữ tham số khác nhau."""

from pathlib import Path

import pytest
from pydantic import ValidationError

import console.sandbox as sb
from console.sandbox import SandboxRequest, compare, pipeline_args, scenario_args


def test_request_limits_and_devices() -> None:
    with pytest.raises(ValidationError):
        SandboxRequest(alt_m=500)
    with pytest.raises(ValidationError):
        SandboxRequest(device="../../etc/passwd")  # chỉ thiết bị trong configs/devices
    with pytest.raises(ValidationError):
        SandboxRequest(extra_flag=1)
    with pytest.raises(ValidationError, match="trước khi chuyến bay kết thúc"):
        SandboxRequest(duration_s=60, outage_start_s=70, outage_len_s=10)
    assert SandboxRequest(device="orin_nano_super").device == "orin_nano_super"


def test_scenario_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    curve = tmp_path / "recall.csv"
    curve.write_text("model,size_px\n")
    monkeypatch.setattr(sb, "RECALL_CURVE", curve)
    cmd = scenario_args(SandboxRequest(alt_m=120, target_person_px=10, render=False), tmp_path / "s")
    assert cmd[cmd.index("--alt-m") + 1] == "120.0" and "--target-person-px" in cmd and "--render" not in cmd
    monkeypatch.setattr(sb, "RECALL_CURVE", tmp_path / "khong_co.csv")
    with pytest.raises(FileNotFoundError):
        scenario_args(SandboxRequest(), tmp_path / "s")


def test_pipeline_args_network_device_and_live() -> None:
    scen, out = Path("s"), Path("o")
    plain = pipeline_args(SandboxRequest(realtime_speed=0, link_probe=False), scen, out, None)
    assert "--net-loss" not in plain and "--net-outage" not in plain and "--ground-url" not in plain
    assert plain[plain.index("--link-probe-s") + 1] == "0" and "--realtime" not in plain and "--live-port" not in plain
    full = pipeline_args(
        SandboxRequest(net_loss=0.2, outage_start_s=40, outage_len_s=30, device="orin_nano_super", realtime_speed=4),
        scen, out, "http://localhost:8000",
    )
    i = full.index("--net-outage")
    assert full[i + 1:i + 3] == ["40.0", "70.0"] and "--net-loss" in full
    assert full[full.index("--device-profile") + 1].endswith("orin_nano_super.yaml")
    assert "--state-every-s" in full and full[full.index("--live-port") + 1] == str(sb.LIVE_PORT)


def test_compare_keeps_only_changed_params() -> None:
    a = {"id": "a", "request": SandboxRequest(label="x").model_dump(), "metrics": {"missed_rate": 0.1}}
    b = {"id": "b", "request": SandboxRequest(alt_m=120).model_dump(), "metrics": {"missed_rate": 0.2}}
    running = {"id": "c", "request": SandboxRequest(fps=8).model_dump(), "metrics": None}
    table = compare([a, b, running])
    assert table["param_keys"] == ["alt_m"]
    assert [r["metrics"]["missed_rate"] for r in table["rows"]] == [0.1, 0.2]


def test_sandbox_yaw_calib_flag(tmp_path: Path) -> None:
    scen, out = tmp_path / "s", tmp_path / "o"
    assert "--yaw-calib" not in pipeline_args(SandboxRequest(), scen, out, None)
    assert "--yaw-calib" in pipeline_args(SandboxRequest(yaw_calib=True), scen, out, None)
