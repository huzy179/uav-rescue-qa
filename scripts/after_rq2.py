"""Xử lý trên máy cá nhân sau khi tải runs/rq2/ từ Kaggle về: so cặp, hiệu chỉnh hồ sơ thiết bị, in bảng kết quả.

Không cần GPU: chỉ đọc boxes.csv và timings.jsonl đã có. Cần ảnh và nhãn của các tập trong rq2_config.yaml ở đúng
đường dẫn như trên Kaggle (data/processed/sds_det, data/processed/visdrone; README mục dữ liệu).

1. So cặp (eval/compare_runs.py, bootstrap cặp theo video) mọi cặp của eval.rq2_report.comparison_pairs: TensorRT với
   PyTorch, thu nhỏ theo độ cao với không thu nhỏ, cắt ô với toàn ảnh; IoU 0,5 và 0,3. Cặp đã có kết quả thì bỏ qua.
2. Hiệu chỉnh configs/devices/*.yaml bằng tools/fit_device_profile.py từ thời gian đo của fp16_tiled và fp16_full1280
   (và thời gian thu nhỏ khung từ fp16_tiled_px10) trên T4, nhân tỉ lệ thiết bị/T4 trong DEVICES (benchmark công bố, xem TECHNICAL 14.6). Kết quả Jetson vẫn là ước
   lượng; chỉ hồ sơ T4 là số đo.
3. eval/rq2_report.py: speed.csv, accuracy_diff.csv và bảng Markdown để chép vào docs/results/rq2_t4.md.

Ví dụ:
    .venv/bin/python scripts/after_rq2.py --rq2 runs/rq2
    .venv/bin/python scripts/after_rq2.py --rq2 runs/rq2 --skip-devices
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

from eval.rq2_report import compare_dir, comparison_pairs
from shared.config import parse_args_with_config

ULTRALYTICS_SOURCE = "Ultralytics, bảng YOLO26 TensorRT FP16 trên Jetson (docs.ultralytics.com/guides/nvidia-jetson, xem 4/11/2026) chia cho YOLO26n trên T4 (1,7 ms; docs.ultralytics.com/models/yolo26); giả định tỉ lệ của bản n áp được cho bản s"

# (file hồ sơ, tên hiển thị, tỉ lệ thời gian thiết bị/T4, nguồn của tỉ lệ)
DEVICES: list[tuple[str, str, float, str]] = [
    ("configs/devices/t4.yaml", "Tesla T4 (Kaggle, đo)", 1.0, "chính T4, không nhân"),
    ("configs/devices/orin_nano_super.yaml", "Jetson Orin Nano Super (ước lượng)", 2.688, f"4,57 / 1,7 = 2,688; {ULTRALYTICS_SOURCE}"),
    ("configs/devices/orin_nx_16gb.yaml", "Jetson Orin NX 16GB (ước lượng)", 2.429, f"4,13 / 1,7 = 2,429; {ULTRALYTICS_SOURCE}"),
    ("configs/devices/agx_orin_64gb.yaml", "Jetson AGX Orin 64GB (ước lượng)", 1.541, f"2,62 / 1,7 = 1,541; {ULTRALYTICS_SOURCE}"),
]


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rq2", type=Path, default=Path("runs/rq2"), help="Thư mục kết quả RQ2 đã tải về")
    parser.add_argument("--bootstrap", type=int, default=1000, help="Số lần bootstrap của so cặp")
    parser.add_argument("--skip-compare", action="store_true", help="Không so cặp")
    parser.add_argument("--skip-devices", action="store_true", help="Không ghi đè configs/devices/*.yaml")
    parser.add_argument("--tiled-variant", default="fp16_tiled", help="Biến thể cắt ô dùng để hiệu chỉnh hồ sơ")
    parser.add_argument("--full-variant", default="fp16_full1280", help="Biến thể toàn ảnh dùng để hiệu chỉnh hồ sơ")
    parser.add_argument("--resized-variant", default="fp16_tiled_px10",
                        help="Biến thể có thu nhỏ theo độ cao dùng để đo thời gian thu nhỏ khung")
    return parse_args_with_config(parser)


def run(cmd: list[str]) -> None:
    """Chạy một lệnh con bằng cùng trình thông dịch, in lệnh, dừng nếu lỗi."""
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def compare_step(rq2: Path, config: dict, bootstrap: int) -> None:
    """Bootstrap cặp cho mọi cặp có đủ boxes.csv ở cả hai phía."""
    pairs = comparison_pairs(config["variants"])
    for data in config["accuracy"]:
        images, labels = Path(data["images"]), Path(data["labels"])
        if not images.is_dir() or not labels.is_dir():
            print(f"[bỏ qua] {data['name']}: không có {images} hoặc {labels} trên máy này")
            continue
        for a, b, kind in pairs:
            run_a, run_b = rq2 / data["name"] / a, rq2 / data["name"] / b
            if not (run_a / "boxes.csv").exists() or not (run_b / "boxes.csv").exists():
                continue
            for iou in ("0.5", "0.3"):
                out = compare_dir(rq2, data["name"], a, b, iou)
                if (out / "compare.csv").exists():
                    continue
                print(f"[{kind}] {data['name']}: {b} − {a}, IoU {iou}")
                cmd = [sys.executable, "eval/compare_runs.py", "--a", str(run_a), "--b", str(run_b), "--images", str(images),
                       "--labels", str(labels), "--iou", iou, "--bootstrap", str(bootstrap), "--output", str(out)]
                if data.get("ignore"):
                    cmd += ["--ignore", str(data["ignore"])]
                if data.get("cluster_pattern"):
                    cmd += ["--cluster-pattern", data["cluster_pattern"]]
                run(cmd)


def frame_mpx(config: dict, root: Path = Path(".")) -> float | None:
    """Megapixel khung gốc của video đo tốc độ, đọc từ info.json cạnh thư mục frames; không có thì None."""
    info = root / Path(config.get("speed", {}).get("source", "")).parent / "info.json"
    if not info.is_file():
        return None
    data = json.loads(info.read_text(encoding="utf-8"))
    return data["width"] * data["height"] / 1e6


def devices_step(rq2: Path, config: dict, tiled_variant: str, full_variant: str, resized_variant: str) -> None:
    """Ghi lại mọi hồ sơ thiết bị từ thời gian đo trên T4."""
    tiled = rq2 / "speed" / tiled_variant / "timings.jsonl"
    full = rq2 / "speed" / full_variant / "timings.jsonl"
    resized = rq2 / "speed" / resized_variant / "timings.jsonl"
    mpx = frame_mpx(config)
    if not tiled.exists():
        print(f"[bỏ qua] hiệu chỉnh hồ sơ: không có {tiled}")
        return
    for output, name, ratio, source in DEVICES:
        cmd = [sys.executable, "tools/fit_device_profile.py", "--tiled", str(tiled), "--ratio", str(ratio),
               "--ratio-source", source, "--name", name, "--output", output]
        if full.exists():
            cmd += ["--full", str(full)]
        if resized.exists() and mpx:
            cmd += ["--resized", str(resized), "--resized-mpx", f"{mpx:g}"]
        if ratio == 1.0:
            cmd += ["--power-mode", "không áp dụng"]
        run(cmd)


def main() -> None:
    """Chạy ba bước theo thứ tự."""
    args = parse_args()
    config_path = args.rq2 / "rq2_config.yaml"
    if not config_path.exists():
        raise SystemExit(f"Không thấy {config_path}: tải nguyên thư mục runs/rq2/ từ Output của Kaggle")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not args.skip_compare:
        compare_step(args.rq2, config, args.bootstrap)
    if not args.skip_devices:
        devices_step(args.rq2, config, args.tiled_variant, args.full_variant, args.resized_variant)
    run([sys.executable, "eval/rq2_report.py", "--rq2", str(args.rq2)])


if __name__ == "__main__":
    main()
