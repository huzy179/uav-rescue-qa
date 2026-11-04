"""Hiệu chỉnh hồ sơ thiết bị (configs/devices/*.yaml) từ thời gian đo của chính pipeline trên T4 (bước speed của RQ2).

Từ timings.jsonl của edge/main.py (mỗi khung: tile_ms, infer_ms, merge_ms, georef_ms, confirm_ms, n_tiles):
    tile_ms     = trung vị của infer_ms / n_tiles trên lần chạy cắt ô
    full_ms     = trung vị của infer_ms trên lần chạy toàn ảnh (không có thì 4 × tile_ms)
    overhead_ms = trung vị của tile_ms + merge_ms + georef_ms + confirm_ms (phần không phải suy luận)
rồi nhân với tỉ lệ thiết bị/T4 (--ratio, lấy từ benchmark công bố trên cùng mô hình; xem TECHNICAL mục 14.6) và tỉ lệ
CPU (--cpu-ratio, phần không phải suy luận chạy trên CPU ARM của Jetson; mặc định bằng --ratio). Kết quả vẫn là ước
lượng: chỉ phần T4 là số đo.

Ví dụ:
    .venv/bin/python tools/fit_device_profile.py --tiled runs/rq2/speed/fp16_tiled/timings.jsonl \\
        --full runs/rq2/speed/fp16_full1280/timings.jsonl --ratio 2.688 --name "Jetson Orin Nano Super (uoc luong)" \\
        --ratio-source "Ultralytics: YOLO26 TensorRT FP16, Orin Nano Super 4,57 ms / T4 1,7 ms" \\
        --output configs/devices/orin_nano_super.yaml
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import yaml

from edge.device_sim import DeviceProfile
from shared.config import parse_args_with_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tiled", type=Path, required=True, help="timings.jsonl của lần chạy cắt ô trên T4")
    parser.add_argument("--full", type=Path, default=None, help="timings.jsonl của lần chạy toàn ảnh trên T4")
    parser.add_argument("--ratio", type=float, required=True, help="Thời gian suy luận thiết bị / T4 (1 cho chính T4)")
    parser.add_argument("--cpu-ratio", type=float, default=None, help="Tỉ lệ cho phần không phải suy luận (mặc định = --ratio)")
    parser.add_argument("--ratio-source", required=True, help="Nguồn của --ratio, ghi vào hồ sơ")
    parser.add_argument("--name", required=True, help="Tên hiển thị, không dấu")
    parser.add_argument("--power-mode", default="MAXN (giả định)", help="Chế độ công suất giả định")
    parser.add_argument("--output", type=Path, required=True, help="File hồ sơ .yaml ra")
    return parse_args_with_config(parser)


def read_timings(path: Path) -> list[dict[str, float]]:
    """Các dòng của timings.jsonl có thời gian suy luận (bỏ dòng của detector phát lại)."""
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [r for r in rows if "infer_ms" in r and r.get("n_tiles", 0) > 0]
    if not rows:
        raise SystemExit(f"Không có dòng nào có infer_ms trong {path}")
    return rows


def fit(tiled: list[dict[str, float]], full: list[dict[str, float]] | None) -> tuple[float, float, float]:
    """(overhead_ms, tile_ms, full_ms) đo trên máy đã chạy, bằng trung vị qua các khung."""
    tile_ms = statistics.median(r["infer_ms"] / r["n_tiles"] for r in tiled)
    overhead_ms = statistics.median(
        r.get("tile_ms", 0.0) + r.get("merge_ms", 0.0) + r.get("georef_ms", 0.0) + r.get("confirm_ms", 0.0) for r in tiled
    )
    full_ms = statistics.median(r["infer_ms"] for r in full) if full else 4.0 * tile_ms
    return overhead_ms, tile_ms, full_ms


def main() -> None:
    """Đo, nhân tỉ lệ, kiểm hồ sơ bằng DeviceProfile rồi ghi YAML."""
    args = parse_args()
    overhead, tile, full = fit(read_timings(args.tiled), read_timings(args.full) if args.full else None)
    cpu_ratio = args.ratio if args.cpu_ratio is None else args.cpu_ratio
    source = (
        f"Đo trên T4 bằng tools/fit_device_profile.py: overhead {overhead:.2f} ms, một ô {tile:.2f} ms, toàn ảnh "
        f"{full:.2f} ms (trung vị; {args.tiled}{', ' + str(args.full) if args.full else ', toàn ảnh = 4 × ô'}). "
        f"Nhân tỉ lệ suy luận {args.ratio:g} và tỉ lệ CPU {cpu_ratio:g}: {args.ratio_source}."
    )
    profile = DeviceProfile(
        name=args.name, calibrated=True, source=source, power_mode=args.power_mode,
        overhead_ms=round(overhead * cpu_ratio, 2), tile_ms=round(tile * args.ratio, 2), full_ms=round(full * args.ratio, 2),
    )
    header = "# Hồ sơ thời gian thiết bị cho edge/device_sim.py: ước lượng, không phải số đo (TECHNICAL mục 14.6).\n"
    args.output.write_text(header + yaml.safe_dump(profile.model_dump(), allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"{args.output}: overhead {profile.overhead_ms} ms, ô {profile.tile_ms} ms, toàn ảnh {profile.full_ms} ms")


if __name__ == "__main__":
    main()
