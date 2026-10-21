"""Ghi thông tin tái lập của một lần chạy (run_config.json); chỉ dùng thư viện chuẩn để chạy được cả trên edge."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any


def _git_state() -> dict[str, Any] | None:
    """Commit hiện tại và mã có đang sửa dở (chưa commit) hay không; None nếu không ở trong kho git."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return {"commit": commit, "dirty": bool(status.strip())}


def _package_version(name: str) -> str | None:
    """Phiên bản của gói đã cài, hoặc None nếu chưa cài."""
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _sha256(path: Path) -> str | None:
    """Mã băm SHA-256 của file trọng số, để biết chính xác đã dùng file nào."""
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_run_config(
    out_dir: Path, script: str, model: str | None, device: str | None, args: dict[str, Any]
) -> Path:
    """Ghi run_config.json: phiên bản thư viện, tên model, thiết bị, máy, commit git và toàn bộ tham số của lần chạy.

    Trường machine/platform để không lẫn số đo thời gian trên Mac với số cho Jetson.
    """
    config = {
        "script": script,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": " ".join(sys.argv),
        "model": model,
        "model_sha256": _sha256(Path(model)) if model else None,
        "device": device,
        "args": args,
        "versions": {
            "python": platform.python_version(),
            "ultralytics": _package_version("ultralytics"),
            "torch": _package_version("torch"),
            "sahi": _package_version("sahi"),
            "opencv-python": _package_version("opencv-python"),
            "numpy": _package_version("numpy"),
        },
        "platform": platform.platform(),
        "machine": platform.machine(),
        "git": _git_state(),
    }
    path = out_dir / "run_config.json"
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path
