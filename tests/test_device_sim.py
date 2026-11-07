"""Kiểm tra giả lập thời gian thiết bị biên và giữ nhịp thời gian thực, bằng ví dụ tính tay."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from edge.device_sim import BusyDevice, DeviceProfile, inference_counts, load_profile
from edge.pacing import RealtimePacer

PROFILE = DeviceProfile(name="thu", calibrated=False, source="tính tay", power_mode="MAXN",
                        overhead_ms=20.0, tile_ms=10.0, full_ms=40.0)


def test_latency_is_linear_in_inferences() -> None:
    # 20 + 8 × 10 + 1 × 40 = 140 ms
    assert PROFILE.latency_ms(8, 1) == pytest.approx(140.0)


def test_resize_cost_only_when_frame_is_scaled() -> None:
    profile = PROFILE.model_copy(update={"resize_ms_per_mpx": 5.0})
    # 20 + 6 × 10 + 8,2944 MP × 5 = 121,472 ms; không thu nhỏ thì không cộng
    assert profile.latency_ms(6, 0, 3840 * 2160 / 1e6) == pytest.approx(121.472)
    assert profile.latency_ms(6, 0) == pytest.approx(80.0)
    assert PROFILE.resize_ms_per_mpx == 0.0  # hồ sơ cũ không có khoá này vẫn đọc được


def test_inference_counts_match_detector_tiling() -> None:
    # 1920×1080, ô 640, chồng 0,2 (bước 512): ngang ceil(1280/512)+1 = 4, dọc ceil(440/512)+1 = 2 → 8 ô
    assert inference_counts(1920, 1080, 1.0, "tiled", 640, 0.2) == (8, 0)
    # 3840×2160: ngang 8, dọc 4 → 32 ô; thêm lượt toàn ảnh
    assert inference_counts(3840, 2160, 1.0, "tiled", 640, 0.2, full_pass=True) == (32, 1)
    # thu nhỏ 3 lần: 1280×720 → ngang ceil(640/512)+1 = 3, dọc ceil(80/512)+1 = 2 → 6 ô
    assert inference_counts(3840, 2160, 3.0, "tiled", 640, 0.2) == (6, 0)
    # phóng to 2 lần (scale 0,5): 640×360 → 1280×720 → 6 ô thay vì 1
    assert inference_counts(640, 360, 1.0, "tiled", 640, 0.2) == (1, 0)
    assert inference_counts(640, 360, 0.5, "tiled", 640, 0.2) == (6, 0)
    assert inference_counts(3840, 2160, 1.0, "full", 640, 0.2) == (0, 1)


def test_busy_device_drops_frames_while_busy() -> None:
    device = BusyDevice(PROFILE)
    # Khung 30 khung/giây; mỗi khung 8 ô → 100 ms: nhận khung 0, bỏ khung 1–2 (33, 67 ms), nhận khung 3 (100 ms).
    taken = []
    for k in range(7):
        t = k / 30
        if device.ready(t):
            done = device.run(t, 8, 0)
            taken.append((k, round(done, 4)))
    assert taken == [(0, 0.1), (3, 0.2), (6, 0.3)]
    assert device.n_skipped == 4 and device.n_done == 3


def test_profile_rejects_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "x.yaml"
    path.write_text("name: x\ncalibrated: false\nsource: s\npower_mode: MAXN\noverhead_ms: 0\ntile_ms: 1\nfull_ms: 4\n")
    assert load_profile(path).tile_ms == 1
    path.write_text(path.read_text() + "tile_msx: 2\n")
    with pytest.raises(ValidationError):
        load_profile(path)


def test_device_profiles_in_repo_are_valid() -> None:
    paths = sorted(Path("configs/devices").glob("*.yaml"))
    assert paths
    for path in paths:
        load_profile(path)


def test_pacer_sleeps_until_sim_time() -> None:
    now = [100.0]
    slept: list[float] = []

    def sleep(s: float) -> None:
        slept.append(s)
        now[0] += s

    pacer = RealtimePacer(clock=lambda: now[0], sleep=sleep)
    pacer.wait_until(0.0)          # mốc 0 tại 100 s đồng hồ thật
    now[0] += 0.2                  # xử lý mất 0,2 s thật
    pacer.wait_until(0.5)          # phải chờ thêm 0,3 s
    assert slept == [pytest.approx(0.3)]
    now[0] += 1.0                  # chậm hơn thời gian thực: không chờ
    pacer.wait_until(1.0)
    assert len(slept) == 1


def test_fit_device_profile_from_timings(tmp_path: Path) -> None:
    import importlib.util
    import json
    import subprocess
    import sys

    spec = importlib.util.spec_from_file_location("fit_device_profile", Path("tools/fit_device_profile.py"))
    fit_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fit_mod)
    # infer 80 ms cho 8 ô → 10 ms/ô; phần còn lại 1 + 3 + 0,5 + 0,5 = 5 ms
    rows = [{"tile_ms": 1.0, "infer_ms": 80.0, "merge_ms": 3.0, "georef_ms": 0.5, "confirm_ms": 0.5, "n_tiles": 8.0}] * 3
    assert fit_mod.fit(rows, None) == (5.0, 10.0, 40.0)
    timings = tmp_path / "timings.jsonl"
    timings.write_text("\n".join(json.dumps(r) for r in rows) + "\n" + json.dumps({"frame_id": 9, "n_dets": 0}) + "\n")
    out = tmp_path / "dev.yaml"
    subprocess.run([sys.executable, "tools/fit_device_profile.py", "--tiled", str(timings), "--ratio", "2", "--cpu-ratio", "3",
                    "--ratio-source", "thu", "--name", "thu", "--output", str(out)], check=True, capture_output=True)
    profile = load_profile(out)
    assert profile.calibrated and (profile.overhead_ms, profile.tile_ms, profile.full_ms) == (15.0, 20.0, 80.0)
