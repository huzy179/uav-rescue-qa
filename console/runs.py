"""Chạy pipeline UAV (edge/main.py) từ giao diện và đọc lại kết quả: khung đã vẽ, cảnh báo, ảnh cắt, thời gian.

Mỗi lần chạy là một tiến trình con riêng, ghi vào runs/console/<mã>/ như một lần chạy edge/main.py bình thường
(run_config.json, log JSONL), nên kết quả từ giao diện tái lập được bằng đúng lệnh ghi trong console_command.txt.
"""

from __future__ import annotations

import base64
import glob
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from eval.timing_summary import summarize_timings

ROOT = Path("runs/console")
CONFIG = Path("configs/console.yaml")


class RunRequest(BaseModel):
    """Tham số một lần chạy thử; tên khoá như tham số của edge/main.py."""

    model_config = ConfigDict(extra="forbid")

    source: str
    model: str = "yolo26s.pt"
    mode: str = "tiled"
    imgsz: int = 1280
    conf: float = 0.1
    fps: float = 2.0
    max_frames: int | None = 60
    confirm: str = "geo"
    n_confirm: int = 3
    radius_m: float = 3.0
    target_person_px: float | None = None
    min_views: float | None = None
    alt_m: float = 50.0
    label: str = ""
    send_to_ground: bool = False


def list_sources(config_path: Path = CONFIG) -> dict[str, list[dict[str, Any]]]:
    """Video demo, chuỗi khung có telemetry thật (SeaDronesSee-MOT) và trọng số có trên máy."""
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    videos = [
        {"path": str(p), "kind": "video", "telemetry": None, "fps": None}
        for folder in cfg.get("videos", []) for p in sorted(Path(folder).glob("*.mp4"))
    ]
    seq_root = Path(cfg.get("sequences", ""))
    sequences = [
        {"path": str(d / "frames"), "kind": "sequence", "telemetry": str(d / "telemetry.csv"), "fps": 30}
        for d in sorted(seq_root.iterdir()) if (d / "frames").is_dir() and (d / "telemetry.csv").is_file()
    ] if seq_root.is_dir() else []
    weights = []
    for pattern in cfg.get("weights", []):
        hits = sorted(glob.glob(pattern))
        weights += hits if hits else ([pattern] if "*" not in pattern else [])  # yolo26s.pt: ultralytics tự tải
    return {"sources": videos + sequences, "weights": weights}


def build_command(req: RunRequest, out: Path, sources: list[dict[str, Any]], ground_url: str | None) -> list[str]:
    """Lệnh edge/main.py cho một yêu cầu; nguồn phải nằm trong danh sách được phép (không chạy đường dẫn tuỳ ý)."""
    source = next((s for s in sources if s["path"] == req.source), None)
    if source is None:
        raise ValueError(f"Nguồn không có trong configs/console.yaml: {req.source}")
    cmd = [
        sys.executable, "-m", "edge.main", "--config", "configs/edge.yaml", "--source", source["path"],
        "--model", req.model, "--mode", req.mode, "--imgsz", str(req.imgsz), "--conf", str(req.conf),
        "--fps", str(req.fps), "--confirm", req.confirm, "--n-confirm", str(req.n_confirm),
        "--radius-m", str(req.radius_m), "--save-frames", "--drain-s", "5", "--output", str(out),
    ]
    if source["fps"]:
        cmd += ["--source-fps", str(source["fps"])]
    if source["telemetry"]:
        cmd += ["--telemetry", source["telemetry"]]
    else:
        cmd += ["--alt-m", str(req.alt_m)]
    if req.max_frames:
        cmd += ["--max-frames", str(req.max_frames)]
    if req.target_person_px:
        cmd += ["--target-person-px", str(req.target_person_px)]
    if req.min_views:
        cmd += ["--min-views", str(req.min_views)]
    if req.send_to_ground and ground_url:
        cmd += ["--ground-url", ground_url, "--uav-id", f"uav-{out.name[-4:]}"]
    return cmd


class RunManager:
    """Giữ các tiến trình đang chạy; trạng thái lần chạy đọc từ thư mục nên còn sau khi tắt giao diện."""

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self._procs: dict[str, subprocess.Popen[bytes]] = {}

    def start(self, req: RunRequest, ground_url: str | None) -> str:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = self.root / run_id
        out.mkdir(parents=True, exist_ok=True)
        cmd = build_command(req, out, list_sources()["sources"], ground_url)
        (out / "console_request.json").write_text(req.model_dump_json(indent=2), encoding="utf-8")
        (out / "console_command.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")
        log = (out / "console.log").open("wb")
        self._procs[run_id] = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        return run_id

    def status(self, run_id: str) -> str:
        proc = self._procs.get(run_id)
        if proc is not None and proc.poll() is None:
            return "running"
        if proc is not None and proc.returncode != 0:
            return "error"
        return "done" if (self.root / run_id / "timings.jsonl").is_file() else "error"

    def list(self) -> list[dict[str, Any]]:
        out = []
        for d in sorted(self.root.glob("*/console_request.json"), reverse=True):
            req = json.loads(d.read_text(encoding="utf-8"))
            out.append({"id": d.parent.name, "status": self.status(d.parent.name), "request": req})
        return out

    def detail(self, run_id: str) -> dict[str, Any]:
        """Khung đã ghi, cảnh báo, thời gian từng chặng, đuôi log."""
        d = self.root / run_id
        frames = sorted(p.stem for p in (d / "frames").glob("*.jpg")) if (d / "frames").is_dir() else []
        alerts = _read_jsonl(d / "alerts.jsonl")
        timings = _read_jsonl(d / "timings.jsonl")
        log = (d / "console.log").read_text(encoding="utf-8", errors="replace") if (d / "console.log").is_file() else ""
        return {
            "id": run_id,
            "status": self.status(run_id),
            "request": json.loads((d / "console_request.json").read_text(encoding="utf-8")),
            "command": (d / "console_command.txt").read_text(encoding="utf-8").strip(),
            "frames": frames,
            "alerts": alerts,
            "timing": summarize_timings(timings) if timings else None,
            "n_detections": sum(r.get("n_dets", 0) for r in timings),
            "log_tail": "\n".join(log.splitlines()[-15:]),
        }

    def crop(self, run_id: str, alert_id: str) -> bytes | None:
        """Ảnh cắt của một cảnh báo, đọc từ outbox SQLite của lần chạy."""
        db_path = self.root / run_id / "outbox.sqlite"
        if not db_path.is_file():
            return None
        with sqlite3.connect(db_path) as db:
            row = db.execute("SELECT payload FROM outbox WHERE alert_id = ? AND kind = 'crop'", (alert_id,)).fetchone()
        return base64.b64decode(json.loads(row[0])["jpeg_base64"]) if row else None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
