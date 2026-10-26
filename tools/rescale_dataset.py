"""Thu nhỏ một tập ảnh có nhãn YOLO theo nhiều mức, cho E6 (recall theo số pixel trên người, ROADMAP mục 5.3).

Mỗi mức f ghi ra <dst>/x<f>/images/<split> (ảnh cạnh chia f, nội suy INTER_AREA) và <dst>/x<f>/labels/<split>.
Nhãn YOLO là toạ độ chuẩn hoá nên không đổi khi thu nhỏ: chỉ chép sang. Người cạnh ngắn 65 px ở mức 1 còn
65/f px ở mức f. Thu nhỏ không tái tạo nhiễu cảm biến, nhòe và nén của camera thật: kết quả là mô phỏng.

Ví dụ:
    .venv/bin/python tools/rescale_dataset.py --images data/processed/sds_det/images/val \\
        --labels data/processed/sds_det/labels/val --dst data/processed/sds_rescale --factors 1 2 3 4 6
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import cv2

from eval.splits import image_paths
from shared.config import parse_args_with_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images", type=Path, required=True, help="Thư mục ảnh gốc")
    parser.add_argument("--labels", type=Path, required=True, help="Thư mục nhãn YOLO cùng tên ảnh")
    parser.add_argument("--dst", type=Path, required=True, help="Thư mục đích, mỗi mức một thư mục con x<f>")
    parser.add_argument("--factors", type=float, nargs="+", default=[1, 1.5, 2.1, 3, 4], help="Các hệ số chia cạnh ảnh")
    parser.add_argument("--split", default="val", help="Tên phần dữ liệu trong thư mục đích")
    parser.add_argument("--jpeg-quality", type=int, default=95, help="Chất lượng JPEG khi ghi ảnh thu nhỏ")
    return parse_args_with_config(parser)


def factor_name(factor: float) -> str:
    """Tên thư mục cho một mức: 2 → x2, 2.1 → x2.1."""
    return f"x{factor:g}"


def rescale(images: Path, labels: Path, dst: Path, factor: float, split: str, quality: int) -> int:
    """Ghi một mức thu nhỏ; trả số ảnh đã ghi."""
    image_dir, label_dir = dst / factor_name(factor) / "images" / split, dst / factor_name(factor) / "labels" / split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for path in image_paths(images):
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Không đọc được ảnh {path}")
        h, w = image.shape[:2]
        size = (max(1, round(w / factor)), max(1, round(h / factor)))
        out = image if factor == 1 else cv2.resize(image, size, interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(image_dir / f"{path.stem}.jpg"), out, [cv2.IMWRITE_JPEG_QUALITY, quality])
        label = labels / f"{path.stem}.txt"
        if label.exists():
            shutil.copyfile(label, label_dir / label.name)
        n += 1
    return n


def main() -> None:
    """Ghi từng mức và in kích thước ảnh mỗi mức."""
    args = parse_args()
    for factor in args.factors:
        if factor < 1:
            raise ValueError(f"Hệ số phải ≥ 1 (chỉ thu nhỏ), nhận được {factor}")
        n = rescale(args.images, args.labels, args.dst, factor, args.split, args.jpeg_quality)
        print(f"{factor_name(factor)}: {n} ảnh -> {args.dst / factor_name(factor)}")


if __name__ == "__main__":
    main()
