"""Chạy suy luận cắt lát SAHI với cùng mô hình, xuất kết quả cùng định dạng với run_baseline.py."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uavdet.cli import parse_args_with_config  # noqa: E402
from uavdet.device import pick_device  # noqa: E402
from uavdet.draw import draw_boxes  # noqa: E402
from uavdet.report import (  # noqa: E402
    PERSON_CLASS_ID,
    box_rows,
    plot_size_histogram,
    print_and_save_summary,
    summarize,
    write_csvs,
    write_run_config,
)
from uavdet.sources import iter_frames  # noqa: E402

METHOD = "sahi"


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Thư mục ảnh hoặc file video")
    parser.add_argument("--model", default="yolo26s.pt", help="Tên hoặc đường dẫn trọng số")
    parser.add_argument("--slice-size", type=int, default=640, help="Cạnh của mỗi lát cắt vuông (px)")
    parser.add_argument("--overlap", type=float, default=0.2, help="Tỉ lệ chồng lấn giữa các lát")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng độ tin cậy")
    parser.add_argument("--device", default=None, help="Ví dụ: cuda:0, mps, cpu (mặc định: tự chọn)")
    parser.add_argument("--output", type=Path, default=Path("runs/baseline/sahi"), help="Thư mục kết quả")
    parser.add_argument(
        "--no-standard-pred",
        action="store_true",
        help="Bỏ lượt suy luận trên toàn ảnh mà SAHI mặc định gộp thêm vào kết quả các lát",
    )
    parser.add_argument("--vid-stride", type=int, default=1, help="Với video: lấy 1 khung hình mỗi N khung")
    parser.add_argument("--max-frames", type=int, default=None, help="Giới hạn số ảnh/khung hình xử lý")
    parser.add_argument("--no-images", action="store_true", help="Không lưu ảnh có vẽ box (nên dùng khi conf rất thấp)")
    return parse_args_with_config(parser)


def main() -> None:
    """Chạy SAHI trên toàn bộ nguồn rồi xuất CSV, bảng tóm tắt, histogram và run_config.json."""
    args = parse_args()
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    from ultralytics import YOLO

    device = pick_device(args.device)
    image_dir = args.output / "images"
    (args.output if args.no_images else image_dir).mkdir(parents=True, exist_ok=True)
    # Để ultralytics tự tải trọng số nếu chưa có, rồi đưa đúng file đó cho SAHI.
    model_path = str(YOLO(args.model).ckpt_path or args.model)
    detector = AutoDetectionModel.from_pretrained(
        model_type="ultralytics",
        model_path=model_path,
        confidence_threshold=args.conf,
        device=device,
    )
    write_run_config(args.output, Path(__file__).name, model_path, device, vars(args))
    print(f"Model: {args.model} | thiết bị: {device} | nguồn: {args.source}")

    slice_kwargs = dict(
        slice_height=args.slice_size,
        slice_width=args.slice_size,
        overlap_height_ratio=args.overlap,
        overlap_width_ratio=args.overlap,
        perform_standard_pred=not args.no_standard_pred,
        verbose=0,
    )
    box_records: list[dict[str, Any]] = []
    image_records: list[dict[str, Any]] = []
    warmed_up = False

    for name, frame in iter_frames(args.source, args.vid_stride, args.max_frames):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if not warmed_up:
            # Lần gọi đầu tiên chậm bất thường, không tính vào thời gian đo.
            get_sliced_prediction(rgb, detector, **slice_kwargs)
            warmed_up = True
        start = time.perf_counter()
        prediction = get_sliced_prediction(rgb, detector, **slice_kwargs)
        infer_ms = (time.perf_counter() - start) * 1000.0

        persons = [p for p in prediction.object_prediction_list if p.category.id == PERSON_CLASS_ID]
        boxes_xyxy = [p.bbox.to_xyxy() for p in persons]
        confs = [p.score.value for p in persons]
        box_records.extend(box_rows(name, METHOD, args.slice_size, boxes_xyxy, confs))
        image_records.append(
            {
                "image": name,
                "method": METHOD,
                "imgsz": args.slice_size,
                "n_persons": len(confs),
                "infer_ms": round(infer_ms, 2),
            }
        )
        if not args.no_images:
            cv2.imwrite(str((image_dir / name).with_suffix(".jpg")), draw_boxes(frame, boxes_xyxy, confs))

    print(f"SAHI: đã xử lý {len(image_records)} ảnh")
    boxes, images = write_csvs(args.output, box_records, image_records)
    print_and_save_summary(args.output, summarize(boxes, images))
    plot_size_histogram(boxes, args.output / "box_size_hist.png")
    print(f"\nKết quả lưu tại: {args.output}")


if __name__ == "__main__":
    main()
