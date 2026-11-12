"""RQ2 trọn một lệnh: xuất mô hình (FP16, INT8) → chấm độ chính xác → đo thời gian cả pipeline → bảng recall theo FPS.

Cấu hình là một file YAML (đọc bằng Pydantic, sai khoá thì báo lỗi ngay), ví dụ configs/experiments/rq2_t4.yaml:

    output: runs/rq2
    weights: runs/train/E2c_s0/weights/best.pt
    max_tiles: 32                 # batch tối đa của engine cắt ô = số ô của một khung 4K (8 × 4)
    calib: {images: [...], labels: [...], max_per_image: 1}   # ô 640 cho hiệu chỉnh INT8 (tools/make_tiles.py)
    speed: {source: .../frames, source_fps: 30, telemetry: .../telemetry.csv, max_frames: 120}
    accuracy:                     # mỗi tập một mục; altitude_csv để chạy được biến thể thu nhỏ theo độ cao
      - {name: sds_det, images: ..., labels: ..., altitude_csv: ..., cluster_pattern: '^(v\\d+)_'}
    variants:                     # precision: pt (PyTorch), fp32, fp16, int8 (TensorRT)
      - {name: fp16_tiled_px10, precision: fp16, mode: tiled, target_person_px: 10}   # gpu_resize: true để đổi cỡ trên GPU

Các bước, bước nào đã có kết quả thì bỏ qua (chạy tiếp được khi phiên Kaggle bị ngắt):
1. Xuất engine: cắt ô thì imgsz = tile, batch động tới max_tiles; toàn ảnh thì imgsz, batch 1. INT8 hiệu chỉnh trên ô
   640 cắt từ ảnh val (không phải tập test).
2. Độ chính xác: scripts/run_tiled.py hoặc run_baseline.py ở conf 0,001 trên từng tập, rồi eval/eval_by_size.py ở IoU
   0,5 và 0,3. Biến thể có target_person_px chỉ chạy trên tập có altitude_csv.
3. Thời gian: edge/main.py trên một chuỗi khung có telemetry thật (cắt ô, suy luận, gộp, georef, confirm từng khung),
   rồi eval/timing_summary.py.
4. eval/rq2_tradeoff.py ghép hai phần thành rq2.csv và hình recall theo FPS.

Số đo trên Kaggle T4 chỉ cho thứ hạng tương đối giữa các cấu hình, không quy đổi ra FPS trên Jetson (TECHNICAL 14.4).

Ví dụ:
    .venv/bin/python scripts/run_rq2.py --config configs/experiments/rq2_t4.yaml
    .venv/bin/python scripts/run_rq2.py --config configs/experiments/rq2_t4.yaml --only fp16_tiled pt_tiled --steps accuracy
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from shared.provenance import write_run_config

STEPS = ["export", "accuracy", "speed", "tradeoff"]


class CalibConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    images: list[Path]
    labels: list[Path]
    max_per_image: int = 1
    fraction: float = 1.0


class SpeedConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Path
    source_fps: float | None = None
    telemetry: Path | None = None
    fps: float = 2.0
    max_frames: int = 120


class AccuracySet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    images: Path
    labels: Path
    ignore: Path | None = None
    altitude_csv: Path | None = None
    cluster_pattern: str | None = None


class Variant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    precision: Literal["pt", "fp32", "fp16", "int8"]
    mode: Literal["full", "tiled"] = "tiled"
    imgsz: int = 1280
    tile: int = 640
    target_person_px: float | None = None
    # Đổi cỡ khung trên GPU. Ghi rõ cho mọi biến thể vì configs/edge.yaml bật từ 10/11 (quyết định #20): tắt thì truyền
    # --no-gpu-resize, để rq2_t4.yaml chạy lại vẫn đo cv2.resize như bản 8/11.
    gpu_resize: bool = False

    @model_validator(mode="after")
    def _check(self) -> Variant:
        if self.target_person_px is not None and self.mode != "tiled":
            raise ValueError(f"{self.name}: target_person_px chỉ dùng với mode tiled")
        return self

    def engine_key(self) -> str:
        """Tên engine dùng chung giữa các biến thể cùng độ chính xác và cùng kích thước vào."""
        return f"{self.precision}_tile{self.tile}" if self.mode == "tiled" else f"{self.precision}_full{self.imgsz}"


class Rq2Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: Path
    weights: Path
    max_tiles: int = 32
    conf: float = 0.001
    max_det: int = 1000
    pipeline_config: Path = Path("configs/edge.yaml")
    calib: CalibConfig | None = None
    speed: SpeedConfig
    accuracy: list[AccuracySet]
    variants: list[Variant]

    @model_validator(mode="after")
    def _check(self) -> Rq2Config:
        names = [v.name for v in self.variants]
        if len(names) != len(set(names)):
            raise ValueError("Tên biến thể bị trùng")
        if any(v.precision == "int8" for v in self.variants) and self.calib is None:
            raise ValueError("Có biến thể int8 thì phải khai báo calib")
        return self


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, required=True, help="File YAML cấu hình RQ2")
    parser.add_argument("--only", nargs="+", default=None, help="Chỉ chạy các biến thể này")
    parser.add_argument("--steps", nargs="+", choices=STEPS, default=STEPS, help="Chỉ chạy các bước này")
    parser.add_argument("--device", default="0", help="GPU dùng để xuất và chạy")
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    """Chạy một lệnh con bằng cùng trình thông dịch, in lệnh, dừng nếu lỗi."""
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def calib_data_yaml(config: Rq2Config, tiled: bool) -> Path:
    """data.yaml cho ảnh hiệu chỉnh INT8, cùng kiểu đầu vào với lúc chạy.

    Cắt ô: ô 640 cắt từ ảnh val ở độ phân giải gốc (cắt một lần, tools/make_tiles.py). Toàn ảnh: chính ảnh val, để
    ultralytics thu về imgsz như lúc chạy; dùng ô thì ảnh bị phóng to, người to hơn thực tế.
    """
    assert config.calib is not None
    if tiled:
        root = config.output / "calib_tiles"
        if not (root / "images" / "val").is_dir():
            run([
                sys.executable, "tools/make_tiles.py", "--images", *map(str, config.calib.images),
                "--labels", *map(str, config.calib.labels), "--dst", str(root), "--split", "val",
                "--max-per-image", str(config.calib.max_per_image),
            ])
        content = {"path": str(root.resolve()), "train": "images/val", "val": "images/val", "names": {0: "person"}}
    else:
        root = config.output / "calib_full"
        root.mkdir(parents=True, exist_ok=True)
        images = [str(p.resolve()) for p in config.calib.images]
        content = {"train": images, "val": images, "names": {0: "person"}}
    path = root / "data.yaml"
    path.write_text(yaml.safe_dump(content), encoding="utf-8")
    return path


def model_path(config: Rq2Config, variant: Variant) -> Path:
    """Trọng số dùng để chạy một biến thể: .pt gốc, hoặc engine đã xuất."""
    if variant.precision == "pt":
        return config.weights
    return config.output / "models" / f"{variant.engine_key()}.engine"


def export_step(config: Rq2Config, variants: list[Variant], device: str) -> None:
    """Xuất mỗi engine một lần; engine đã có thì bỏ qua."""
    from edge.detector import export_model  # import trễ: chỉ bước này cần ultralytics trong tiến trình chính

    done: set[str] = set()
    failed: dict[str, str] = {}
    for v in variants:
        if v.precision == "pt" or v.engine_key() in done:
            continue
        done.add(v.engine_key())
        out = model_path(config, v)
        if out.exists():
            print(f"[đã có] {out}")
            continue
        tiled = v.mode == "tiled"
        try:
            export_model(
                str(config.weights), out, "engine", {"fp32": 32, "fp16": 16, "int8": 8}[v.precision],
                imgsz=v.tile if tiled else v.imgsz, batch=config.max_tiles if tiled else 1, dynamic=tiled,
                data=calib_data_yaml(config, tiled) if v.precision == "int8" else None,
                fraction=config.calib.fraction if config.calib and v.precision == "int8" else 1.0,
                max_det=config.max_det, device=device,
            )
        except Exception as e:  # một engine hỏng (ví dụ INT8 trên GPU cũ) không được làm mất cả lần chạy nhiều giờ
            failed[v.engine_key()] = f"{type(e).__name__}: {e}"
            print(f"[lỗi xuất] {out}: {failed[v.engine_key()]}; bỏ qua các biến thể dùng engine này", flush=True)
            continue
        print(f"Đã xuất {out}")
    if not done:
        return
    (config.output / "models").mkdir(parents=True, exist_ok=True)
    write_run_config(config.output / "models", "scripts/run_rq2.py", str(config.weights), device,
                     {"step": "export", "engines": sorted(done - set(failed)), "failed": failed})


def runnable(config: Rq2Config, variants: list[Variant]) -> list[Variant]:
    """Biến thể có mô hình để chạy: .pt luôn có; engine thiếu (xuất lỗi hoặc chưa xuất) thì báo và bỏ."""
    keep = []
    for v in variants:
        if v.precision != "pt" and not model_path(config, v).exists():
            print(f"[bỏ qua] {v.name}: không có {model_path(config, v)}")
            continue
        keep.append(v)
    return keep


def accuracy_step(config: Rq2Config, variants: list[Variant], device: str) -> None:
    """Dự đoán ở conf thấp trên từng tập rồi chấm theo kích thước ở IoU 0,5 và 0,3."""
    variants = runnable(config, variants)
    for data in config.accuracy:
        for v in variants:
            if v.target_person_px is not None and data.altitude_csv is None:
                print(f"[bỏ qua] {v.name} trên {data.name}: tập không có độ cao")
                continue
            out = config.output / data.name / v.name
            common = ["--source", str(data.images), "--model", str(model_path(config, v)), "--conf", str(config.conf),
                      "--max-det", str(config.max_det), "--device", device, "--no-images", "--output", str(out)]
            if not (out / "boxes.csv").exists():
                if v.mode == "tiled":
                    cmd = [sys.executable, "scripts/run_tiled.py", *common, "--tile", str(v.tile), "--imgsz", str(v.tile)]
                    if v.target_person_px is not None:
                        cmd += ["--altitude-csv", str(data.altitude_csv), "--target-person-px", str(v.target_person_px)]
                    cmd += ["--gpu-resize" if v.gpu_resize else "--no-gpu-resize"]
                else:
                    cmd = [sys.executable, "scripts/run_baseline.py", *common, "--imgsz", str(v.imgsz)]
                run(cmd)
            for iou in ("0.5", "0.3"):
                ev = config.output / data.name / f"eval_{v.name}_iou{iou}"
                if (ev / "eval_by_size.csv").exists():
                    continue
                cmd = [sys.executable, "eval/eval_by_size.py", "--runs", str(out), "--images", str(data.images),
                       "--labels", str(data.labels), "--iou", iou, "--output", str(ev)]
                if data.ignore is not None:
                    cmd += ["--ignore", str(data.ignore)]
                if data.cluster_pattern is not None:
                    cmd += ["--cluster-pattern", data.cluster_pattern]
                run(cmd)


def speed_step(config: Rq2Config, variants: list[Variant], device: str) -> None:
    """Chạy cả pipeline trên chuỗi khung có telemetry, ghi timings.jsonl; rồi tổng hợp thời gian mọi biến thể."""
    s = config.speed
    runs = []
    for v in runnable(config, variants):
        out = config.output / "speed" / v.name
        runs.append(out)
        if (out / "timings.jsonl").exists():
            continue
        cmd = [
            sys.executable, "-m", "edge.main", "--config", str(config.pipeline_config), "--source", str(s.source),
            "--fps", str(s.fps), "--max-frames", str(s.max_frames), "--model", str(model_path(config, v)),
            "--mode", v.mode, "--imgsz", str(v.imgsz), "--tile", str(v.tile), "--device", device,
            "--drain-s", "0", "--output", str(out),
        ]
        if s.source_fps is not None:
            cmd += ["--source-fps", str(s.source_fps)]
        if s.telemetry is not None:
            cmd += ["--telemetry", str(s.telemetry)]
        if v.target_person_px is not None:
            cmd += ["--target-person-px", str(v.target_person_px)]
        cmd += ["--gpu-resize" if v.gpu_resize else "--no-gpu-resize"]
        run(cmd)
    run([sys.executable, "eval/timing_summary.py", "--runs", *map(str, runs), "--output", str(config.output / "timing.csv")])


def main() -> None:
    """Đọc cấu hình, chạy các bước được chọn theo thứ tự."""
    args = parse_args()
    config = Rq2Config.model_validate(yaml.safe_load(args.config.read_text(encoding="utf-8")))
    variants = [v for v in config.variants if args.only is None or v.name in args.only]
    unknown = set(args.only or []) - {v.name for v in config.variants}
    if unknown:
        raise SystemExit(f"Không có biến thể: {', '.join(sorted(unknown))}")
    config.output.mkdir(parents=True, exist_ok=True)
    (config.output / "rq2_config.yaml").write_text(args.config.read_text(encoding="utf-8"), encoding="utf-8")
    if "export" in args.steps:
        export_step(config, variants, args.device)
    if "accuracy" in args.steps:
        accuracy_step(config, variants, args.device)
    if "speed" in args.steps:
        speed_step(config, variants, args.device)
    if "tradeoff" in args.steps:
        run([sys.executable, "eval/rq2_tradeoff.py", "--rq2", str(config.output), "--rq2-config", str(args.config)])


if __name__ == "__main__":
    main()
