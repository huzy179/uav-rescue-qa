"""Sân thử mô phỏng: chỉnh tham số chuyến bay, mạng, thiết bị trên giao diện, chạy trọn chuỗi và so các lần chạy.

Một lần chạy (console/sandbox_run.py, tiến trình con) gồm: sinh kịch bản mô phỏng (sim/make_rq3.py, có thể vẽ ảnh tổng
hợp), lớp đáp án (tools/make_truth_layer.py), xoá trạm mặt đất và nạp đáp án, chạy pipeline (edge/main.py, phát lại phát
hiện giả, gửi về trạm, giả lập thiết bị và mạng), chấm bằng eval/rq3_metrics.py. Mọi thứ ghi vào runs/sandbox/<mã>/
kèm đúng các lệnh đã chạy (commands.txt), nên số trong bảng so sánh đọc được từ runs/ và tái lập được.

Tham số giới hạn trong khoảng hợp lý (Pydantic), thiết bị chỉ chọn trong configs/devices/: giao diện không chạy được
lệnh hay đường dẫn tuỳ ý.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path("runs/sandbox")
DEVICES = Path("configs/devices")
RECALL_CURVE = Path("runs/e6_sds/eval/recall_by_pixels.csv")
LIVE_PORT = 8001
# Đặt trên mặt Hồ Tây để bản đồ nền là mặt nước (như configs/demo/hotay_quet_scenario.yaml); không phải vùng lũ thật.
LAT0, LON0 = 21.0520, 105.8150

# Chỉ số hiện trong bảng so sánh (khoá của rq3_metrics.json) và tham số có thể khác nhau giữa các lần.
METRICS = [
    "n_people", "missed_rate", "false_alarms_per_min", "merge_errors", "split_errors", "time_to_alert_s_median",
    "position_error_m_median", "within_reported_radius_95", "delivery_delay_s_max", "lost_rate", "frames_processed",
]


class SandboxRequest(BaseModel):
    """Một lần chạy sân thử; mặc định gần chuyến quét demo (configs/demo/hotay_quet*.yaml) nhưng ngắn hơn."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field("", max_length=60)
    alt_m: float = Field(50.0, ge=20, le=200)
    speed_mps: float = Field(8.0, ge=2, le=20)
    pattern: Literal["zigzag", "straight"] = "zigzag"
    leg_m: float = Field(250.0, ge=100, le=600)
    duration_s: float = Field(120.0, ge=30, le=300)
    n_people: int = Field(12, ge=1, le=60)
    gps_sigma_m: float = Field(1.0, ge=0, le=10)
    gps_sigma_late_m: float | None = Field(None, ge=0, le=10)  # GPS đổi sang σ này từ giữa chuyến (mất vệ tinh)
    gps_from_receiver: bool = False  # bán kính theo độ chính xác GPS bộ thu báo (--gps-sigma-from-telemetry)
    yaw_bias_deg: float = Field(0.0, ge=0, le=15)
    yaw_calib: bool = False  # tự hiệu chỉnh lệch la bàn trên drone (--yaw-calib, rq3_yawcalib.md)
    recall_model: Literal["E1", "E2c"] = "E2c"
    target_person_px: float | None = Field(None, ge=4, le=40)
    fps: float = Field(4.0, ge=0.5, le=8)
    device: str | None = None
    net_loss: float = Field(0.0, ge=0, le=0.8)
    outage_start_s: float = Field(0.0, ge=0, le=300)
    outage_len_s: float = Field(0.0, ge=0, le=120)
    net_burst_s: float | None = Field(None, gt=0, le=60)  # sóng yếu theo cụm: xấu và tốt trung bình bằng nhau (mất 0,5), rq3_burst.md
    link_probe: bool = True
    render: bool = True
    realtime_speed: float = Field(4.0, ge=0, le=16)  # 0: chạy nhanh hết mức, không phát theo thời gian thực
    seed: int = Field(0, ge=0, le=999)

    @model_validator(mode="after")
    def _check(self) -> SandboxRequest:
        if self.device is not None and self.device not in list_devices():
            raise ValueError(f"Thiết bị không có trong {DEVICES}: {self.device}")
        if self.outage_len_s and self.outage_start_s >= self.duration_s:
            raise ValueError("Mất sóng phải bắt đầu trước khi chuyến bay kết thúc")
        return self


def list_devices() -> list[str]:
    return sorted(p.stem for p in DEVICES.glob("*.yaml"))


def scenario_args(req: SandboxRequest, out: Path) -> list[str]:
    """Lệnh sim/make_rq3.py: ảnh 1080p 8 khung/giây, góc nhìn 82° chéo, người đứng yên, recall theo cỡ người."""
    if not RECALL_CURVE.is_file():
        raise FileNotFoundError(f"Thiếu {RECALL_CURVE} (đường recall theo cỡ người, e6_sds_pilot.md)")
    cmd = [
        sys.executable, "-m", "sim.make_rq3", "--output", str(out), "--duration-s", str(req.duration_s), "--fps", "8",
        "--alt-m", str(req.alt_m), "--speed-mps", str(req.speed_mps), "--lat0", str(LAT0), "--lon0", str(LON0),
        "--width", "1920", "--height", "1080", "--fov-deg", "82", "--fov-type", "diagonal", "--pattern", req.pattern,
        "--leg-m", str(req.leg_m), "--n-people", str(req.n_people), "--drift-mps", "0", "--gps-sigma-m", str(req.gps_sigma_m),
        "--yaw-bias-deg", str(req.yaw_bias_deg), "--recall-curve", str(RECALL_CURVE), "--recall-model", req.recall_model,
        "--fp-per-frame", "0.3", "--seed", str(req.seed),
    ]
    if req.pattern == "straight":
        cmd += ["--lateral-m", "25"]
    # Bộ thu luôn báo độ chính xác (cột gps_acc_m); pipeline chỉ dùng khi gps_from_receiver.
    cmd += ["--gps-acc-report"]
    if req.gps_sigma_late_m is not None:
        mid = req.duration_s / 2.0
        cmd += ["--gps-sigma-profile", f"0:{req.gps_sigma_m},{mid - 2.5:g}:{req.gps_sigma_m},{mid + 2.5:g}:{req.gps_sigma_late_m}"]
    if req.target_person_px:
        cmd += ["--target-person-px", str(req.target_person_px)]
    if req.render:
        cmd += ["--render"]
    return cmd


def pipeline_args(req: SandboxRequest, scenario: Path, out: Path, ground_url: str | None) -> list[str]:
    """Lệnh edge/main.py: phát lại phát hiện giả của kịch bản, gửi về trạm, giả lập thiết bị và mạng."""
    cmd = [
        sys.executable, "-m", "edge.main", "--config", "configs/edge.yaml", "--source", str(scenario / "frames.mp4"),
        "--telemetry", str(scenario / "telemetry.csv"), "--replay", str(scenario / "detections.jsonl"),
        "--simulated-flight", "--fps", str(req.fps), "--fov-deg", "82", "--fov-type", "diagonal",
        "--gps-sigma-m", str(max(req.gps_sigma_m, 0.5)),  # người vận hành đặt theo GPS của drone (rq3_geoerr.md)
        "--link-probe-s", "2" if req.link_probe else "0", "--drain-s", "30", "--seed", str(req.seed), "--output", str(out),
    ]
    if req.target_person_px:
        cmd += ["--target-person-px", str(req.target_person_px)]
    if req.yaw_calib:
        cmd += ["--yaw-calib"]
    if req.gps_from_receiver:
        cmd += ["--gps-sigma-from-telemetry"]
    if req.device:
        cmd += ["--device-profile", str(DEVICES / f"{req.device}.yaml")]
    if req.net_loss:
        cmd += ["--net-loss", str(req.net_loss)]
    if req.net_burst_s is not None:
        cmd += ["--net-burst", str(req.net_burst_s), str(req.net_burst_s)]
    if req.outage_len_s:
        cmd += ["--net-outage", str(req.outage_start_s), str(req.outage_start_s + req.outage_len_s)]
    if ground_url:
        cmd += ["--ground-url", ground_url, "--state-every-s", "1"]
    if req.realtime_speed > 0:
        cmd += ["--realtime", "--realtime-speed", str(req.realtime_speed)]
        if req.render:
            cmd += ["--live-port", str(LIVE_PORT)]
    return cmd


class SandboxManager:
    """Một lần chạy sân thử tại một thời điểm (dùng chung cổng video và trạm mặt đất); trạng thái đọc từ thư mục."""

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self._procs: dict[str, subprocess.Popen[bytes]] = {}

    def running(self) -> str | None:
        return next((rid for rid, p in self._procs.items() if p.poll() is None), None)

    def start(self, req: SandboxRequest, ground_url: str | None) -> str:
        busy = self.running()
        if busy:
            raise RuntimeError(f"Đang chạy {busy}; chờ xong rồi chạy tiếp")
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = self.root / run_id
        out.mkdir(parents=True, exist_ok=True)
        (out / "request.json").write_text(req.model_dump_json(indent=2), encoding="utf-8")
        cmd = [sys.executable, "-m", "console.sandbox_run", str(out)] + ([ground_url] if ground_url else [])
        log = (out / "sandbox.log").open("wb")
        self._procs[run_id] = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        return run_id

    def detail(self, run_id: str) -> dict[str, Any]:
        d = self.root / run_id
        status = _read_json(d / "status.json") or {"phase": "khởi động", "state": "running"}
        proc = self._procs.get(run_id)
        if status.get("state") == "running" and (proc is None or proc.poll() is not None):
            status = {**status, "state": "error", "phase": status.get("phase", "") + " (tiến trình đã dừng)"}
        log = (d / "sandbox.log").read_text(encoding="utf-8", errors="replace") if (d / "sandbox.log").is_file() else ""
        return {
            "id": run_id,
            "request": _read_json(d / "request.json"),
            "status": status,
            "metrics": _read_json(d / "edge" / "rq3_eval" / "rq3_metrics.json"),
            "commands": (d / "commands.txt").read_text(encoding="utf-8") if (d / "commands.txt").is_file() else "",
            "log_tail": "\n".join(log.splitlines()[-12:]),
        }

    def list(self) -> list[dict[str, Any]]:
        return [self.detail(p.parent.name) for p in sorted(self.root.glob("*/request.json"), reverse=True)]


def compare(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Bảng so sánh các lần chạy đã xong: chỉ giữ tham số có giá trị khác nhau giữa các lần, cộng các chỉ số."""
    done = [r for r in runs if r["metrics"]]
    keys = [k for k in SandboxRequest.model_fields if k != "label" and len({json.dumps(r["request"].get(k)) for r in done}) > 1]
    rows = [{"id": r["id"], "label": r["request"].get("label", ""), "params": {k: r["request"].get(k) for k in keys},
             "metrics": {m: r["metrics"].get(m) for m in METRICS}} for r in done]
    return {"param_keys": keys, "metric_keys": METRICS, "rows": rows}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
