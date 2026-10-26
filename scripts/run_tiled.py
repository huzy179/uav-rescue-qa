"""Chạy bộ cắt ô riêng (edge/detector.py) trên thư mục ảnh, xuất cùng định dạng với run_baseline/run_sahi để đối chiếu với SAHI."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import cv2
import pandas as pd

from edge.detector import YoloDetector, person_scale
from edge.georef import Camera, expected_person_px
from edge.sampler import iter_frames
from eval.draw import draw_boxes
from eval.report import box_rows, plot_size_histogram, print_and_save_summary, summarize, write_csvs, write_run_config
from shared.config import parse_args_with_config
from shared.schema import Telemetry

METHOD = "tiled"


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Thư mục ảnh hoặc file video")
    parser.add_argument("--model", default="yolo26s.pt", help="Tên hoặc đường dẫn trọng số")
    parser.add_argument("--tile", type=int, default=640, help="Cạnh ô (px)")
    parser.add_argument("--overlap", type=float, default=0.2, help="Tỉ lệ chồng giữa các ô")
    parser.add_argument("--full-pass", action="store_true", help="Thêm lượt toàn ảnh ở --imgsz (như perform_standard_pred của SAHI)")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước của lượt toàn ảnh")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng độ tin cậy")
    parser.add_argument("--max-det", type=int, default=1000, help="Số box tối đa mỗi lần suy luận")
    parser.add_argument("--device", default=None, help="Ví dụ: cuda:0, mps, cpu (mặc định: tự chọn)")
    parser.add_argument("--output", type=Path, default=Path("runs/baseline/tiled"), help="Thư mục kết quả")
    parser.add_argument("--max-frames", type=int, default=None, help="Giới hạn số ảnh xử lý")
    parser.add_argument("--no-images", action="store_true", help="Không lưu ảnh có vẽ box (nên dùng khi conf rất thấp)")
    parser.add_argument("--altitude-csv", type=Path, default=None, help="CSV image, alt_agl_m (tools/make_sds_det.py) để thu nhỏ theo độ cao")
    parser.add_argument("--target-person-px", type=float, default=None, help="Như edge/main.py: thu nhỏ để người dự kiến còn khoảng số px này")
    parser.add_argument("--person-m", type=float, default=0.5, help="Cỡ người nhìn từ trên xuống (m)")
    parser.add_argument("--fov-deg", type=float, default=82.0, help="Góc nhìn camera, để tính số px dự kiến")
    parser.add_argument("--fov-type", choices=["diagonal", "horizontal"], default="diagonal", help="Kiểu góc nhìn")
    return parse_args_with_config(parser)


def main() -> None:
    """Chạy bộ cắt ô trên toàn bộ nguồn rồi xuất CSV, bảng tóm tắt, histogram và run_config.json."""
    args = parse_args()
    detector = YoloDetector(
        args.model, "tiled", args.imgsz, args.tile, args.overlap, args.conf, args.max_det, args.device, args.full_pass
    )
    image_dir = args.output / "images"
    (args.output if args.no_images else image_dir).mkdir(parents=True, exist_ok=True)
    write_run_config(args.output, Path(__file__).name, str(detector.model.ckpt_path or args.model), detector.device, vars(args))
    print(f"Model: {args.model} | thiết bị: {detector.device} | nguồn: {args.source}")

    altitude = {}
    if args.target_person_px is not None:
        if args.altitude_csv is None:
            raise SystemExit("--target-person-px cần --altitude-csv")
        altitude = dict(pd.read_csv(args.altitude_csv)[["image", "alt_agl_m"]].itertuples(index=False))
    box_records: list[dict[str, Any]] = []
    image_records: list[dict[str, Any]] = []
    for index, (name, frame) in enumerate(iter_frames(args.source, max_frames=args.max_frames)):
        scale = 1.0
        if args.target_person_px is not None:
            cam = Camera.from_fov(args.fov_deg, args.fov_type, frame.shape[1], frame.shape[0])
            tel = Telemetry(t=0.0, lat=0.0, lon=0.0, alt_agl_m=altitude[name], yaw_deg=0.0, pitch_deg=-90.0)
            scale = person_scale(expected_person_px(tel, cam, args.person_m), args.target_person_px)
        dets, timings = detector.detect(frame, index, 0.0, scale)
        boxes_xyxy = [d.box_px for d in dets]
        confs = [d.conf for d in dets]
        box_records.extend(box_rows(name, METHOD, args.tile, boxes_xyxy, confs))
        infer_ms = timings["tile_ms"] + timings["infer_ms"] + timings["merge_ms"]
        image_records.append(
            {"image": name, "method": METHOD, "imgsz": args.tile, "n_persons": len(confs), "infer_ms": round(infer_ms, 2), "scale": scale}
        )
        if not args.no_images:
            cv2.imwrite(str((image_dir / name).with_suffix(".jpg")), draw_boxes(frame, boxes_xyxy, confs))

    print(f"Cắt ô: đã xử lý {len(image_records)} ảnh")
    boxes, images = write_csvs(args.output, box_records, image_records)
    print_and_save_summary(args.output, summarize(boxes, images))
    plot_size_histogram(boxes, args.output / "box_size_hist.png")
    print(f"\nKết quả lưu tại: {args.output}")


if __name__ == "__main__":
    main()
