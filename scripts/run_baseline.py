"""Chạy baseline: phát hiện lớp person trên ảnh/video ở nhiều imgsz và thống kê kích thước box."""

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

METHOD = "full"


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Thư mục ảnh hoặc file video")
    parser.add_argument("--model", default="yolo26s.pt", help="Tên hoặc đường dẫn trọng số")
    parser.add_argument("--imgsz", type=int, nargs="+", default=[640, 1280], help="Danh sách kích thước suy luận")
    parser.add_argument("--conf", type=float, default=0.25, help="Ngưỡng độ tin cậy")
    parser.add_argument("--device", default=None, help="Ví dụ: cuda:0, mps, cpu (mặc định: tự chọn)")
    parser.add_argument("--output", type=Path, default=Path("runs/baseline"), help="Thư mục kết quả")
    parser.add_argument("--vid-stride", type=int, default=1, help="Với video: lấy 1 khung hình mỗi N khung")
    parser.add_argument("--max-frames", type=int, default=None, help="Giới hạn số ảnh/khung hình xử lý")
    parser.add_argument("--no-images", action="store_true", help="Không lưu ảnh có vẽ box (nên dùng khi conf rất thấp)")
    return parse_args_with_config(parser)


def run_one_imgsz(
    model: Any, args: argparse.Namespace, imgsz: int, device: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Suy luận toàn bộ nguồn ở một imgsz; lưu ảnh có vẽ box và trả về (dòng theo box, dòng theo ảnh)."""
    image_dir = args.output / f"imgsz_{imgsz}"
    if not args.no_images:
        image_dir.mkdir(parents=True, exist_ok=True)
    predict_kwargs = dict(imgsz=imgsz, conf=args.conf, classes=[PERSON_CLASS_ID], device=device, verbose=False)
    box_records: list[dict[str, Any]] = []
    image_records: list[dict[str, Any]] = []
    warmed_up = False

    for name, frame in iter_frames(args.source, args.vid_stride, args.max_frames):
        if not warmed_up:
            # Lần gọi đầu tiên ở mỗi imgsz chậm bất thường, không tính vào thời gian đo.
            model.predict(frame, **predict_kwargs)
            warmed_up = True
        start = time.perf_counter()
        result = model.predict(frame, **predict_kwargs)[0]
        infer_ms = (time.perf_counter() - start) * 1000.0

        # Ultralytics đã quy đổi box về toạ độ pixel của ảnh gốc.
        boxes_xyxy = result.boxes.xyxy.cpu().numpy()
        confs = result.boxes.conf.cpu().numpy()
        box_records.extend(box_rows(name, METHOD, imgsz, boxes_xyxy, confs))
        image_records.append(
            {"image": name, "method": METHOD, "imgsz": imgsz, "n_persons": len(confs), "infer_ms": round(infer_ms, 2)}
        )
        if not args.no_images:
            cv2.imwrite(str((image_dir / name).with_suffix(".jpg")), draw_boxes(frame, boxes_xyxy, confs))

    print(f"imgsz={imgsz}: đã xử lý {len(image_records)} ảnh")
    return box_records, image_records


def main() -> None:
    """Chạy baseline ở từng imgsz rồi xuất CSV, bảng tóm tắt, histogram và run_config.json."""
    args = parse_args()
    from ultralytics import YOLO

    device = pick_device(args.device)
    args.output.mkdir(parents=True, exist_ok=True)
    model = YOLO(args.model)
    write_run_config(args.output, Path(__file__).name, args.model, device, vars(args))
    print(f"Model: {args.model} | thiết bị: {device} | nguồn: {args.source}")

    box_records: list[dict[str, Any]] = []
    image_records: list[dict[str, Any]] = []
    for imgsz in args.imgsz:
        new_boxes, new_images = run_one_imgsz(model, args, imgsz, device)
        box_records.extend(new_boxes)
        image_records.extend(new_images)

    boxes, images = write_csvs(args.output, box_records, image_records)
    print_and_save_summary(args.output, summarize(boxes, images))
    plot_size_histogram(boxes, args.output / "box_size_hist.png")
    print(f"\nKết quả lưu tại: {args.output}")


if __name__ == "__main__":
    main()
