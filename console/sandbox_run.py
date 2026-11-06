"""Chạy trọn một lần sân thử (console/sandbox.py): kịch bản → lớp đáp án → trạm mặt đất → pipeline → chấm điểm.

    .venv/bin/python -m console.sandbox_run runs/sandbox/<mã> [http://localhost:8000]

Đọc <thư mục>/request.json; ghi status.json (giai đoạn hiện tại), commands.txt (các lệnh đã chạy), scenario/, edge/
(log của pipeline, rq3_eval/rq3_metrics.json). Không có địa chỉ trạm thì pipeline chạy không gửi đi.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

from console.sandbox import SandboxRequest, pipeline_args, scenario_args


def set_status(out: Path, phase: str, state: str = "running") -> None:
    (out / "status.json").write_text(json.dumps({"phase": phase, "state": state}, ensure_ascii=False), encoding="utf-8")
    print(f"[{state}] {phase}", flush=True)


def run(out: Path, cmd: list[str]) -> None:
    with (out / "commands.txt").open("a", encoding="utf-8") as f:
        f.write(" ".join(cmd) + "\n")
    subprocess.run(cmd, check=True)


def post(url: str, body: bytes | None = None) -> None:
    request = urllib.request.Request(url, data=body or b"", method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10):
        pass


def main() -> None:
    out = Path(sys.argv[1])
    ground_url = sys.argv[2].rstrip("/") if len(sys.argv) > 2 else None
    req = SandboxRequest.model_validate_json((out / "request.json").read_text(encoding="utf-8"))
    scenario, edge = out / "scenario", out / "edge"
    try:
        set_status(out, "sinh kịch bản" + (" và ảnh tổng hợp" if req.render else ""))
        run(out, scenario_args(req, scenario))
        run(out, [sys.executable, "tools/make_truth_layer.py", "--rq3", str(scenario / "ground_truth.json"),
                  "--output", str(scenario / "truth_layer.json")])
        if ground_url:
            set_status(out, "xoá trạm mặt đất, nạp đáp án")
            post(ground_url + "/api/reset?confirm=true")
            post(ground_url + "/api/truth", (scenario / "truth_layer.json").read_bytes())
        set_status(out, "đang bay" + (f" (nhanh {req.realtime_speed:g}×)" if req.realtime_speed else ""))
        run(out, pipeline_args(req, scenario, edge, ground_url))
        set_status(out, "chấm điểm")
        run(out, [sys.executable, "-m", "eval.rq3_metrics", "--run", str(edge), "--truth", str(scenario / "ground_truth.json")])
        set_status(out, "xong", "done")
    except Exception as error:  # noqa: BLE001 (ghi lỗi cho giao diện rồi thoát mã khác 0)
        set_status(out, f"lỗi: {error}", "error")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
