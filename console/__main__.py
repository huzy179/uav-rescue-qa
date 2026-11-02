"""Mở giao diện thử nghiệm: .venv/bin/python -m console [--port 8501] [--no-ground].

Mặc định bật kèm trạm mặt đất (ground/app.py) ở cổng 8000 với cơ sở dữ liệu runs/ground/console.sqlite, để tab
"Trạm mặt đất" hiện bản đồ và lần chạy thử gửi được cảnh báo tới. Cổng 8000 đã có trạm chạy thì dùng luôn trạm đó.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys

import uvicorn

from console.app import create_app


def port_in_use(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8501, help="Cổng của giao diện")
    parser.add_argument("--ground-port", type=int, default=8000, help="Cổng của trạm mặt đất")
    parser.add_argument("--no-ground", action="store_true", help="Không bật trạm mặt đất")
    args = parser.parse_args()

    ground = None
    ground_url = None if args.no_ground else f"http://localhost:{args.ground_port}"
    if ground_url and not port_in_use(args.ground_port):
        os.makedirs("runs/ground", exist_ok=True)
        ground = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "--factory", "ground.app:default_app", "--port", str(args.ground_port),
             "--log-level", "warning"],
            env={**os.environ, "FLOODEYE_GROUND_DB": "runs/ground/console.sqlite"},
        )
    print(f"Giao diện: http://localhost:{args.port}" + (f"  ·  trạm mặt đất: {ground_url}" if ground_url else ""))
    try:
        uvicorn.run(create_app(ground_url), host="127.0.0.1", port=args.port, log_level="warning")
    finally:
        if ground is not None:
            ground.terminate()


if __name__ == "__main__":
    main()
