"""Fine-tune YOLO một lớp person trên một hoặc nhiều bộ dữ liệu đã chuyển về định dạng YOLO."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from edge.device import pick_device
from eval.report import write_run_config
from shared.config import parse_args_with_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, nargs="+", required=True, help="Các thư mục ảnh huấn luyện (.../images/train)")
    parser.add_argument("--val", type=Path, nargs="+", required=True, help="Các thư mục ảnh kiểm định (.../images/val)")
    parser.add_argument("--model", default="yolo26s.pt", help="Trọng số khởi đầu, hoặc yaml mô hình (E3)")
    parser.add_argument("--imgsz", type=int, default=1280, help="Kích thước ảnh huấn luyện")
    parser.add_argument("--epochs", type=int, default=100, help="Số epoch tối đa")
    parser.add_argument("--patience", type=int, default=20, help="Dừng sớm sau N epoch không cải thiện")
    parser.add_argument("--batch", type=int, default=8, help="Kích thước lô")
    parser.add_argument("--seed", type=int, default=0, help="Seed; mỗi cấu hình cuối chạy 3 seed")
    parser.add_argument("--flipud", type=float, default=0.5, help="Xác suất lật dọc (ảnh nhìn từ trên xuống không có chiều đứng)")
    parser.add_argument("--close-mosaic", type=int, default=10, help="Tắt mosaic ở N epoch cuối")
    parser.add_argument("--fraction", type=float, default=1.0, help="Tỉ lệ tập huấn luyện được dùng (nhỏ hơn 1 để chạy thử)")
    parser.add_argument("--workers", type=int, default=8, help="Số tiến trình đọc dữ liệu")
    parser.add_argument("--device", default=None, help="Ví dụ: 0, mps, cpu (mặc định: tự chọn)")
    parser.add_argument("--output", type=Path, default=Path("runs/train/E2_s0"), help="Thư mục kết quả")
    parser.add_argument("--resume", action="store_true", help="Chạy tiếp từ <output>/weights/last.pt khi phiên bị ngắt")
    return parse_args_with_config(parser)


def write_data_yaml(train: list[Path], val: list[Path], out_dir: Path) -> Path:
    """Ghi data.yaml với đường dẫn tuyệt đối, để cùng một cấu hình chạy được trên Mac lẫn Kaggle."""
    missing = [str(p) for p in train + val if not p.is_dir()]
    if missing:
        raise FileNotFoundError(f"Không tìm thấy thư mục ảnh: {', '.join(missing)}")
    data = {
        "train": [str(p.resolve()) for p in train],
        "val": [str(p.resolve()) for p in val],
        "names": {0: "person"},
    }
    path = out_dir / "data.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def main() -> None:
    """Huấn luyện rồi ghi run_config.json cạnh trọng số."""
    args = parse_args()
    from ultralytics import YOLO

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    device = pick_device(args.device)
    last = output / "weights" / "last.pt"
    if args.resume:
        if not last.is_file():
            raise FileNotFoundError(f"--resume cần checkpoint, không thấy {last}")
        from ultralytics.utils.patches import torch_load

        # Checkpoint của lần chạy đã xong không còn trạng thái optimizer; ultralytics khi đó không báo lỗi mà
        # lặng lẽ huấn luyện bộ mặc định coco8 vào thư mục runs chung.
        if torch_load(last, map_location="cpu").get("optimizer") is None:
            raise RuntimeError(f"{last} là checkpoint của lần chạy đã xong, không còn gì để chạy tiếp")
        # Ultralytics đọc lại toàn bộ tham số từ checkpoint, nên các tham số khác trên dòng lệnh bị bỏ qua.
        YOLO(str(last)).train(resume=True)
    else:
        YOLO(args.model).train(
            data=str(write_data_yaml([Path(p) for p in args.train], [Path(p) for p in args.val], output)),
            imgsz=args.imgsz,
            epochs=args.epochs,
            patience=args.patience,
            batch=args.batch,
            seed=args.seed,
            deterministic=True,
            cos_lr=True,
            close_mosaic=args.close_mosaic,
            flipud=args.flipud,
            fraction=args.fraction,
            workers=args.workers,
            device=device,
            project=str(output.parent),
            name=output.name,
            exist_ok=True,
        )
    model = args.model if Path(args.model).is_file() else None
    write_run_config(output, Path(__file__).name, model, device, vars(args))
    print(f"Kết quả lưu tại: {output}")


if __name__ == "__main__":
    main()
