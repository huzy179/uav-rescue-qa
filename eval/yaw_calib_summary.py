"""Tổng hợp lệch la bàn ước lượng (--yaw-calib) của một lần quét RQ3 (sim/sweep_rq3.py).

Mỗi lần chạy pipeline ghi yaw_calib.json (lệch cuối chuyến, số mẫu bay thẳng, lệch theo từng giây); kịch bản ghi
scenario.yaml (lệch thật yaw_bias_deg). Ghi:
- estimates.csv: mỗi lần chạy một dòng (tham số kịch bản, lệch ước lượng cuối chuyến, sai số, số mẫu, giây đầu tiên
  bắt đầu hiệu chỉnh);
- summary.csv: theo nhiễu GPS, lệch thật, kiểu đường bay: lệch ước lượng trung bình, sai số tuyệt đối lớn nhất, số mẫu
  trung bình, giây bắt đầu hiệu chỉnh muộn nhất.

    .venv/bin/python eval/yaw_calib_summary.py --runs runs/rq3/yawcalib --output runs/rq3/yawcalib/yaw_calib
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from shared.config import parse_args_with_config


def collect(root: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(root.rglob("yaw_calib.json")):
        scenario = yaml.safe_load((path.parent.parent / "scenario.yaml").read_text(encoding="utf-8"))
        calib = json.loads(path.read_text(encoding="utf-8"))
        first = next((s for s, bias in calib["bias_by_s"] if bias != 0.0), None)
        rows.append({
            "alt_m": scenario.get("alt_m"), "gps_sigma_m": scenario.get("gps_sigma_m"),
            "yaw_bias_deg": scenario.get("yaw_bias_deg", 0.0), "pattern": scenario.get("pattern", "straight"),
            "seed": scenario.get("seed"), "estimated_bias_deg": calib["final_bias_deg"],
            "error_deg": calib["final_bias_deg"] - scenario.get("yaw_bias_deg", 0.0),
            "n_samples": calib["n_samples"], "first_corrected_s": first,
        })
    if not rows:
        raise SystemExit(f"Không có yaw_calib.json nào trong {root} (pipeline chạy với --yaw-calib chưa?)")
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=Path, required=True, help="Thư mục kết quả của sim/sweep_rq3.py")
    parser.add_argument("--output", type=Path, required=True, help="Thư mục ghi estimates.csv, summary.csv")
    args = parse_args_with_config(parser)
    args.output.mkdir(parents=True, exist_ok=True)
    estimates = collect(args.runs)
    estimates.to_csv(args.output / "estimates.csv", index=False)
    summary = (
        estimates.assign(abs_error_deg=estimates.error_deg.abs())
        .groupby(["gps_sigma_m", "yaw_bias_deg", "pattern"])
        .agg(n_runs=("seed", "size"), estimated_bias_deg_mean=("estimated_bias_deg", "mean"),
             abs_error_deg_max=("abs_error_deg", "max"), n_samples_mean=("n_samples", "mean"),
             first_corrected_s_max=("first_corrected_s", "max"))
        .round(3).reset_index()
    )
    summary.to_csv(args.output / "summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
