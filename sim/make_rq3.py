"""Sinh một kịch bản RQ3 hoàn toàn giả lập để chạy qua edge/main.py rồi chấm bằng eval/rq3_metrics.py.

Ghi vào --output:
    frames.mp4          khung đen đúng kích thước camera, fps = --fps (để pipeline chạy không đổi; không có nội dung ảnh)
    telemetry.csv       telemetry UAV THẤY (đường bay thật + nhiễu GPS)
    detections.jsonl    phát hiện giả theo recall và báo nhầm, dùng với --replay
    ground_truth.json   người thật (vị trí, trôi) và ai hiện ở khung nào, theo đường bay THẬT
    run_config.json

Ví dụ:
    .venv/bin/python -m sim.make_rq3 --output runs/rq3/demo --gps-sigma-m 3
    .venv/bin/python -m edge.main --config configs/edge.yaml --source runs/rq3/demo/frames.mp4 \\
        --telemetry runs/rq3/demo/telemetry.csv --replay runs/rq3/demo/detections.jsonl --output runs/rq3/demo/geo
    .venv/bin/python eval/rq3_metrics.py --run runs/rq3/demo/geo --truth runs/rq3/demo/ground_truth.json
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

import cv2
import numpy as np

from edge.georef import Camera
from shared.config import parse_args_with_config
from shared.provenance import write_run_config
from sim.flight import StraightFlight
from sim.scenario import (
    GaussMarkovGps, RecallCurve, noisy_telemetry, place_people, simulate_detections, tilted_view, visible_boxes,
)


def build_parser() -> argparse.ArgumentParser:
    """Khai báo tham số dòng lệnh; tách riêng để sim/sweep_rq3.py kiểm tra tên khoá trước khi chạy."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True, help="Thư mục kịch bản")
    parser.add_argument("--duration-s", type=float, default=60.0, help="Thời lượng chuyến bay (giây)")
    parser.add_argument("--fps", type=float, default=2.0, help="Số khung mỗi giây (cũng là fps của frames.mp4)")
    parser.add_argument("--alt-m", type=float, default=50.0, help="Độ cao bay so với mặt nước (m)")
    parser.add_argument("--speed-mps", type=float, default=10.0, help="Vận tốc (m/s)")
    parser.add_argument("--yaw-deg", type=float, default=0.0, help="Hướng bay (0 = Bắc)")
    parser.add_argument("--lat0", type=float, default=21.0285, help="Vĩ độ điểm xuất phát")
    parser.add_argument("--lon0", type=float, default=105.8542, help="Kinh độ điểm xuất phát")
    parser.add_argument("--width", type=int, default=3840, help="Bề rộng ảnh (px)")
    parser.add_argument("--height", type=int, default=2160, help="Chiều cao ảnh (px)")
    parser.add_argument("--fov-deg", type=float, default=82.0, help="Góc nhìn camera (độ)")
    parser.add_argument("--fov-type", choices=["horizontal", "diagonal"], default="diagonal", help="--fov-deg là góc ngang hay chéo")
    parser.add_argument("--n-people", type=int, default=10, help="Số người thật")
    parser.add_argument("--lateral-m", type=float, default=25.0, help="Người lệch ngang khỏi đường bay tối đa (m)")
    parser.add_argument("--drift-mps", type=float, default=0.0, help="Vận tốc trôi theo dòng nước (m/s), hướng ngẫu nhiên")
    parser.add_argument("--gps-sigma-m", type=float, default=0.0, help="Độ lệch chuẩn nhiễu GPS mỗi trục (m)")
    parser.add_argument("--gps-tau-s", type=float, default=30.0, help="Thời gian tương quan của nhiễu GPS (giây)")
    parser.add_argument("--yaw-bias-deg", type=float, default=0.0, help="Sai số cố định của hướng trong telemetry (độ)")
    parser.add_argument("--tilt-deg", type=float, default=0.0, help="Camera thật nghiêng về phía trước (độ); pipeline vẫn giả định nhìn thẳng xuống")
    parser.add_argument("--recall", type=float, default=0.7, help="Xác suất phát hiện một người có trong khung")
    parser.add_argument("--recall-curve", type=Path, default=None,
                        help="recall_by_pixels.csv (eval/recall_by_pixels.py): recall theo cỡ người thay cho --recall")
    parser.add_argument("--recall-model", default=None, help="Cột model cần lấy trong --recall-curve")
    parser.add_argument("--fp-per-frame", type=float, default=0.5, help="Số báo nhầm trung bình mỗi khung")
    parser.add_argument("--seed", type=int, default=0, help="Seed cho vị trí người, nhiễu GPS và detector giả")
    return parser


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    return parse_args_with_config(build_parser())


def main() -> None:
    """Sinh đủ các file của kịch bản."""
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cam = Camera.from_fov(args.fov_deg, args.fov_type, args.width, args.height)
    flight = StraightFlight(args.lat0, args.lon0, args.alt_m, args.speed_mps, args.yaw_deg)
    # Người nằm trong quãng bay, chừa nửa khung ở hai đầu để ai cũng có cơ hội đi qua trọn khung.
    half_footprint_m = cam.height / 2.0 * args.alt_m / cam.f_px
    path_m = args.speed_mps * args.duration_s
    people = place_people(flight, args.n_people, (half_footprint_m, path_m - half_footprint_m), args.lateral_m, args.drift_mps, args.seed)
    gps = GaussMarkovGps(args.gps_sigma_m, args.gps_tau_s, args.seed + 1)
    rng = random.Random(args.seed + 2)
    recall = RecallCurve.from_csv(args.recall_curve, args.recall_model) if args.recall_curve else args.recall

    n_frames = int(args.duration_s * args.fps)
    black = np.zeros((cam.height, cam.width, 3), dtype=np.uint8)
    video = cv2.VideoWriter(str(args.output / "frames.mp4"), cv2.VideoWriter.fourcc(*"mp4v"), args.fps, (cam.width, cam.height))
    frames_truth = []
    with (
        (args.output / "telemetry.csv").open("w", newline="", encoding="utf-8") as tel_file,
        (args.output / "detections.jsonl").open("w", encoding="utf-8") as det_file,
    ):
        tel_writer = csv.writer(tel_file)
        tel_writer.writerow(["t", "lat", "lon", "alt_agl_m", "yaw_deg"])
        for frame_id in range(n_frames):
            t = frame_id / args.fps
            true_tel = flight.at(t)
            seen = noisy_telemetry(true_tel, gps, args.yaw_bias_deg)
            tel_writer.writerow([t, f"{seen.lat:.9f}", f"{seen.lon:.9f}", seen.alt_agl_m, seen.yaw_deg])
            boxes = visible_boxes(people, tilted_view(true_tel, args.tilt_deg), cam, t)
            frames_truth.append({"frame_id": frame_id, "t": t, "visible": [{"person_id": pid, "box_px": box} for pid, box in boxes]})
            for det in simulate_detections(frame_id, t, boxes, cam, recall, args.fp_per_frame, rng):
                det_file.write(det.model_dump_json() + "\n")
            video.write(black)
    video.release()

    truth = {
        "fps": args.fps,
        "duration_s": n_frames / args.fps,
        "people": [vars(p) for p in people],
        "frames": frames_truth,
    }
    (args.output / "ground_truth.json").write_text(json.dumps(truth, ensure_ascii=False), encoding="utf-8")
    write_run_config(args.output, "sim/make_rq3.py", None, None, vars(args))
    seen_people = {v["person_id"] for f in frames_truth for v in f["visible"]}
    print(f"{n_frames} khung, {len(people)} người ({len(seen_people)} có xuất hiện trong khung). Lưu tại: {args.output}")


if __name__ == "__main__":
    main()
