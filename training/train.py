"""Fine-tune YOLO một lớp person trên một hoặc nhiều bộ dữ liệu đã chuyển về định dạng YOLO."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

from edge.device import pick_device
from eval.report import write_run_config
from shared.config import parse_args_with_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, nargs="+", required=True, help="Các thư mục ảnh huấn luyện (.../images/train) hoặc file .txt danh sách ảnh (tools/split_by_video.py)")
    parser.add_argument("--val", type=Path, nargs="+", required=True, help="Các thư mục ảnh kiểm định (.../images/val) hoặc file .txt danh sách ảnh")
    parser.add_argument("--model", default="yolo26s.pt", help="Trọng số khởi đầu, hoặc yaml mô hình (E3)")
    parser.add_argument(
        "--transfer-from", default=None,
        help="Với --model yolo26?-p2.yaml: nạp trọng số của bản 3 đầu (ví dụ yolo26s.pt) theo ánh xạ lớp của P2, thay vì học từ đầu",
    )
    parser.add_argument("--imgsz", type=int, default=1280, help="Kích thước ảnh huấn luyện")
    parser.add_argument("--epochs", type=int, default=100, help="Số epoch tối đa")
    parser.add_argument("--patience", type=int, default=20, help="Dừng sớm sau N epoch không cải thiện")
    parser.add_argument("--batch", type=int, default=8, help="Kích thước lô")
    parser.add_argument("--seed", type=int, default=0, help="Seed; mỗi cấu hình cuối chạy 3 seed")
    parser.add_argument("--flipud", type=float, default=0.5, help="Xác suất lật dọc (ảnh nhìn từ trên xuống không có chiều đứng)")
    parser.add_argument("--close-mosaic", type=int, default=10, help="Tắt mosaic ở N epoch cuối")
    parser.add_argument(
        "--scale", type=float, default=0.5,
        help="Phóng to/thu nhỏ ngẫu nhiên hệ số [1 − scale, 1 + scale]; box dưới 2 px sau đó bị xoá nhãn (xem tools/label_size_stats.py)",
    )
    parser.add_argument("--fraction", type=float, default=1.0, help="Tỉ lệ tập huấn luyện được dùng (nhỏ hơn 1 để chạy thử)")
    parser.add_argument("--workers", type=int, default=8, help="Số tiến trình đọc dữ liệu")
    parser.add_argument("--device", default=None, help="Ví dụ: 0, mps, cpu (mặc định: tự chọn)")
    parser.add_argument("--output", type=Path, default=Path("runs/train/E2_s0"), help="Thư mục kết quả")
    parser.add_argument("--resume", action="store_true", help="Chạy tiếp từ <output>/weights/last.pt khi phiên bị ngắt")
    return parse_args_with_config(parser)


def write_data_yaml(train: list[Path], val: list[Path], out_dir: Path) -> Path:
    """Ghi data.yaml với đường dẫn tuyệt đối, để cùng một cấu hình chạy được trên Mac lẫn Kaggle.

    Mỗi mục là thư mục ảnh hoặc file .txt liệt kê đường dẫn ảnh; ultralytics nhận cả hai.
    """
    missing = [str(p) for p in train + val if not (p.is_dir() or (p.is_file() and p.suffix == ".txt"))]
    if missing:
        raise FileNotFoundError(f"Không tìm thấy thư mục ảnh hoặc file .txt: {', '.join(missing)}")
    data = {
        "train": [str(p.resolve()) for p in train],
        "val": [str(p.resolve()) for p in val],
        "names": {0: "person"},
    }
    path = out_dir / "data.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


# yolo26-p2.yaml chèn 6 lớp (nhánh lên P2 và xuống lại P3) vào head: lớp 0–16 giữ chỗ, nhánh xuống P3→P4→P5
# (17–22 của bản 3 đầu) dời thành 23–28, Detect 23 thành 29 với một đầu P2 thêm ở vị trí 0.
P2_SHIFT_FROM, P2_SHIFT, BASE_DETECT, P2_DETECT = 17, 6, 23, 29
DETECT_BRANCH = re.compile(r"^(cv2|cv3|one2one_cv2|one2one_cv3)\.(\d+)\.")


def remap_to_p2(key: str) -> str | None:
    """Tên tham số của YOLO26 3 đầu → tên tương ứng trong YOLO26-P2; None nếu không có chỗ tương ứng."""
    match = re.match(r"model\.(\d+)\.(.+)", key)
    if not match:
        return None
    index, rest = int(match.group(1)), match.group(2)
    if index < P2_SHIFT_FROM:
        return key
    if index < BASE_DETECT:
        return f"model.{index + P2_SHIFT}.{rest}"
    if index == BASE_DETECT:
        rest = DETECT_BRANCH.sub(lambda m: f"{m.group(1)}.{int(m.group(2)) + 1}.", rest)
        return f"model.{P2_DETECT}.{rest}"
    return None


def build_p2_init(p2_yaml: str, source: str, out_path: Path) -> tuple[int, int]:
    """Dựng checkpoint P2 mang trọng số của bản 3 đầu (theo remap_to_p2, chỉ nhận tham số cùng hình dạng).

    Gọi YOLO(p2_yaml).load(source) chỉ ghép theo tên nên mất cả neck và head (360/902 tham số với bản s).
    Giữ tên lớp của nguồn để ultralytics còn nhận ra lớp person khi thu đầu phân loại về một lớp.
    """
    from ultralytics import YOLO

    src = YOLO(source).model
    target = YOLO(p2_yaml)
    target_sd = target.model.state_dict()
    moved = {}
    for key, value in src.state_dict().items():
        new_key = remap_to_p2(key)
        if new_key in target_sd and target_sd[new_key].shape == value.shape:
            moved[new_key] = value
    target.model.load_state_dict(moved, strict=False)
    target.model.names = dict(src.names)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    target.save(str(out_path))
    return len(moved), len(target_sd)


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
        model_path = args.model
        if args.transfer_from:
            model_path = str(output / "p2_init.pt")
            n, total = build_p2_init(args.model, args.transfer_from, Path(model_path))
            print(f"Khởi tạo P2 từ {args.transfer_from}: {n}/{total} tham số, lưu {model_path}")
        YOLO(model_path).train(
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
            scale=args.scale,
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
