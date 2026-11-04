"""Ghép hai video demo cạnh nhau, mỗi bên một tiêu đề, để so hai thiết bị giả lập (hay hai cấu hình) trên cùng chuyến bay.

Video ra dài bằng video ngắn hơn, cùng fps với video trái; mỗi bên thu về cùng chiều cao. Dùng cho video demo dự phòng
và slide bảo vệ (scripts/demo_bao_ve.sh so-sanh).

Ví dụ:
    .venv/bin/python scripts/ghep_video.py --left runs/edge/a/annotated.mp4 --right runs/edge/b/annotated.mp4 \\
        --left-title "Jetson AGX Orin (uoc luong)" --right-title "Jetson Orin Nano Super (uoc luong)" --output so_sanh.mp4
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from shared.config import parse_args_with_config


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh (có thể lấy mặc định từ --config)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--left", type=Path, required=True, help="Video bên trái")
    parser.add_argument("--right", type=Path, required=True, help="Video bên phải")
    parser.add_argument("--left-title", default="", help="Tiêu đề bên trái (không dấu: cv2.putText không vẽ được dấu)")
    parser.add_argument("--right-title", default="", help="Tiêu đề bên phải")
    parser.add_argument("--height", type=int, default=720, help="Chiều cao mỗi bên (px)")
    parser.add_argument("--output", type=Path, required=True, help="File .mp4 ra")
    return parse_args_with_config(parser)


def with_title(frame: np.ndarray, title: str, height: int) -> np.ndarray:
    """Thu khung về chiều cao height rồi thêm dải tiêu đề đen phía trên."""
    frame = cv2.resize(frame, (round(frame.shape[1] * height / frame.shape[0]), height), interpolation=cv2.INTER_AREA)
    bar = np.zeros((48, frame.shape[1], 3), dtype=np.uint8)
    cv2.putText(bar, title, (12, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    return np.vstack([bar, frame])


def main() -> None:
    """Đọc song song hai video, ghép từng cặp khung."""
    args = parse_args()
    left, right = cv2.VideoCapture(str(args.left)), cv2.VideoCapture(str(args.right))
    if not left.isOpened() or not right.isOpened():
        raise SystemExit(f"Không mở được video: {args.left if not left.isOpened() else args.right}")
    fps = left.get(cv2.CAP_PROP_FPS) or 8.0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    writer: cv2.VideoWriter | None = None
    n = 0
    while True:
        ok_left, frame_left = left.read()
        ok_right, frame_right = right.read()
        if not (ok_left and ok_right):
            break
        pair = np.hstack([with_title(frame_left, args.left_title, args.height),
                          np.full((args.height + 48, 8, 3), 255, dtype=np.uint8),
                          with_title(frame_right, args.right_title, args.height)])
        if writer is None:
            writer = cv2.VideoWriter(str(args.output), cv2.VideoWriter.fourcc(*"mp4v"), fps, (pair.shape[1], pair.shape[0]))
        writer.write(pair)
        n += 1
    if writer is not None:
        writer.release()
    print(f"Ghép {n} khung, {fps:g} khung/giây: {args.output}")


if __name__ == "__main__":
    main()
