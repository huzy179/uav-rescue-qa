"""Quét lưới tham số RQ3 trên kịch bản giả lập: sinh kịch bản → chạy pipeline → chấm điểm → tổng hợp (TECHNICAL mục 15.4).

Cấu hình là một file YAML (đọc bằng Pydantic, sai khoá thì báo lỗi ngay):

    output: runs/rq3/gps                  # thư mục kết quả
    seeds: [0, 1, 2]                      # mỗi tổ hợp chạy với từng seed (vị trí người, nhiễu, detector giả, mạng)
    scenario: {duration_s: 60}            # tham số mặc định của sim/make_rq3.py
    pipeline_config: configs/edge.yaml    # cấu hình gốc của edge/main.py
    pipeline: {n_confirm: 3}              # ghi đè lên pipeline_config
    grid:                                 # tích Descartes; khoá có tiền tố scenario. hoặc pipeline.
      scenario.gps_sigma_m: [0, 1, 3]
      pipeline.confirm: [geo, bytetrack, bytetrack_cmc]

Mỗi lần chạy có thư mục riêng chứa đúng file cấu hình đã dùng. Kịch bản (người, nhiễu) dùng chung giữa các tổ hợp
pipeline, nên các chiến lược được so trên cùng dữ liệu. Lần chạy đã có kết quả thì bỏ qua, nên chạy tiếp được khi bị ngắt.

Ghi ra: results.csv (mỗi lần chạy một dòng), summary.csv (trung bình, độ lệch chuẩn qua các seed của từng tổ hợp).

Ví dụ:
    .venv/bin/python -m sim.sweep_rq3 --config configs/experiments/rq3_gps.yaml --jobs 4
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

from shared.provenance import write_run_config

METRICS = [
    "n_alerts", "false_alarms_per_min", "missed_rate", "merge_errors", "split_errors",
    "time_to_alert_s_median", "position_error_m_median", "delivery_delay_s_median", "lost_rate", "kb_per_alert",
]
# Do sweep tự đặt cho từng lần chạy; không được ghi đè trong cấu hình.
RESERVED = {"scenario": {"output", "seed"}, "pipeline": {"source", "telemetry", "replay", "output", "seed", "source_fps"}}


class SweepConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: Path
    seeds: list[int] = [0]
    scenario: dict[str, Any] = {}
    pipeline_config: Path = Path("configs/edge.yaml")
    pipeline: dict[str, Any] = {}
    grid: dict[str, list[Any]] = {}
    r_eval_m: float = 10.0
    tail_s: float = 10.0

    @field_validator("grid")
    @classmethod
    def _grid_keys(cls, grid: dict[str, list[Any]]) -> dict[str, list[Any]]:
        for key, values in grid.items():
            if key.split(".", 1)[0] not in ("scenario", "pipeline") or "." not in key:
                raise ValueError(f"Khoá grid '{key}' phải có dạng scenario.<tham số> hoặc pipeline.<tham số>")
            if not values:
                raise ValueError(f"Khoá grid '{key}' không có giá trị nào")
        return grid


def known_args(module: str) -> set[str]:
    """Tên các tham số mà sim/make_rq3.py hoặc edge/main.py nhận."""
    if module == "scenario":
        from sim.make_rq3 import build_parser
    else:
        from edge.main import build_parser
    return {action.dest for action in build_parser()._actions} - {"help"}


def validate(config: SweepConfig) -> None:
    """Báo lỗi trước khi chạy nếu có tham số không tồn tại hoặc bị sweep tự quản lý."""
    pipeline_base = yaml.safe_load(config.pipeline_config.read_text(encoding="utf-8")) or {}
    for part, values in (("scenario", config.scenario), ("pipeline", {**pipeline_base, **config.pipeline})):
        names = {k.replace("-", "_") for k in values} | {k.split(".", 1)[1] for k in config.grid if k.startswith(part + ".")}
        unknown = names - known_args(part)
        if unknown:
            raise SystemExit(f"Tham số {part} không tồn tại: {sorted(unknown)}")
        reserved = names & RESERVED[part]
        if reserved:
            raise SystemExit(f"Tham số {part} do sweep tự đặt, không ghi trong cấu hình: {sorted(reserved)}")


def short_hash(values: dict[str, Any]) -> str:
    return hashlib.sha1(json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()[:10]


def run(cmd: list[str], log: Path) -> None:
    """Chạy một lệnh con, ghi stdout/stderr vào log; lỗi thì dừng và chỉ ra log."""
    with log.open("w", encoding="utf-8") as f:
        result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        raise RuntimeError(f"Lệnh lỗi (xem {log}): {' '.join(cmd)}")


def make_scenario(directory: Path, params: dict[str, Any]) -> None:
    if (directory / "ground_truth.json").is_file():
        return
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "scenario.yaml").write_text(yaml.safe_dump(params, allow_unicode=True), encoding="utf-8")
    run([sys.executable, "-m", "sim.make_rq3", "--config", str(directory / "scenario.yaml"), "--output", str(directory)], directory / "make_rq3.log")


def run_pipeline(scenario_dir: Path, run_dir: Path, params: dict[str, Any], config: SweepConfig) -> dict[str, Any]:
    metrics_path = run_dir / "rq3_eval" / "rq3_metrics.json"
    if not metrics_path.is_file():
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "pipeline.yaml").write_text(yaml.safe_dump(params, allow_unicode=True), encoding="utf-8")
        run(
            [
                sys.executable, "-m", "edge.main", "--config", str(run_dir / "pipeline.yaml"),
                "--source", str(scenario_dir / "frames.mp4"), "--telemetry", str(scenario_dir / "telemetry.csv"),
                "--replay", str(scenario_dir / "detections.jsonl"), "--output", str(run_dir),
            ],
            run_dir / "edge_main.log",
        )
        run(
            [
                sys.executable, "-m", "eval.rq3_metrics", "--run", str(run_dir), "--truth", str(scenario_dir / "ground_truth.json"),
                "--r-eval-m", str(config.r_eval_m), "--tail-s", str(config.tail_s),
            ],
            run_dir / "rq3_metrics.log",
        )
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def summarize(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    """Trung bình và độ lệch chuẩn của từng chỉ số qua các seed, cho từng tổ hợp tham số."""
    groups: dict[tuple, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(tuple(row[k] for k in keys), []).append(row)
    summary = []
    for combo, group in groups.items():
        item: dict[str, Any] = dict(zip(keys, combo)) | {"n_seeds": len(group)}
        for metric in METRICS:
            values = [r[metric] for r in group if r[metric] is not None]
            item[f"{metric}_mean"] = round(statistics.fmean(values), 4) if values else None
            item[f"{metric}_std"] = round(statistics.stdev(values), 4) if len(values) > 1 else None
            item[f"{metric}_n"] = len(values)  # số seed có giá trị (ví dụ thời gian tới cảnh báo không có khi bỏ sót hết)
        summary.append(item)
    return summary


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Đọc cấu hình, kiểm tra, sinh kịch bản, chạy pipeline, tổng hợp."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, required=True, help="File YAML của lần quét")
    parser.add_argument("--jobs", type=int, default=1, help="Số lần chạy song song")
    args = parser.parse_args()
    config = SweepConfig.model_validate(yaml.safe_load(args.config.read_text(encoding="utf-8")) or {})
    validate(config)
    config.output.mkdir(parents=True, exist_ok=True)
    write_run_config(config.output, "sim/sweep_rq3.py", None, None, {**vars(args), "sweep": config.model_dump(mode="json")})

    keys = list(config.grid)
    pipeline_base = yaml.safe_load(config.pipeline_config.read_text(encoding="utf-8")) or {}
    plans = []  # (row, thư mục kịch bản, tham số kịch bản, thư mục chạy, tham số pipeline)
    for combo in itertools.product(*config.grid.values()):
        chosen = dict(zip(keys, combo))
        for seed in config.seeds:
            scenario = {**config.scenario, **{k[9:]: v for k, v in chosen.items() if k.startswith("scenario.")}, "seed": seed}
            pipeline = {**pipeline_base, **config.pipeline, **{k[9:]: v for k, v in chosen.items() if k.startswith("pipeline.")}, "seed": seed}
            scenario_dir = config.output / "scenarios" / f"s_{short_hash(scenario)}"
            run_dir = scenario_dir / f"p_{short_hash(pipeline)}"
            plans.append(({**chosen, "seed": seed}, scenario_dir, scenario, run_dir, pipeline))

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        unique = {str(p[1]): p for p in plans}
        list(pool.map(lambda p: make_scenario(p[1], p[2]), unique.values()))
        results = list(pool.map(lambda p: run_pipeline(p[1], p[3], p[4], config), plans))

    rows = [{**row, "run_dir": str(run_dir), **{m: metrics.get(m) for m in METRICS}} for (row, _, _, run_dir, _), metrics in zip(plans, results)]
    write_csv(config.output / "results.csv", rows)
    summary = summarize(rows, keys)
    write_csv(config.output / "summary.csv", summary)
    print(f"{len(rows)} lần chạy, {len(summary)} tổ hợp. Kết quả: {config.output}/summary.csv")
    for item in summary:
        label = ", ".join(f"{k.split('.', 1)[1]}={item[k]}" for k in keys)
        print(f"  {label}: bỏ sót {item['missed_rate_mean']} ± {item['missed_rate_std']}, báo giả/phút {item['false_alarms_per_min_mean']}")


if __name__ == "__main__":
    main()
