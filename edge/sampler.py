"""Đọc khung hình từ thư mục ảnh hoặc file video."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".wmv"}


def iter_frames(
    source: Path, vid_stride: int = 1, max_frames: int | None = None
) -> Iterator[tuple[str, np.ndarray]]:
    """Sinh lần lượt (tên, ảnh BGR) từ thư mục ảnh, một file ảnh hoặc một file video."""
    if source.is_dir():
        paths = sorted(p for p in source.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        if not paths:
            raise FileNotFoundError(f"Không tìm thấy ảnh nào trong thư mục: {source}")
        yield from _iter_images(paths, max_frames)
    elif source.is_file() and source.suffix.lower() in IMAGE_EXTS:
        yield from _iter_images([source], max_frames)
    elif source.is_file() and source.suffix.lower() in VIDEO_EXTS:
        yield from _iter_video(source, vid_stride, max_frames)
    else:
        raise FileNotFoundError(f"--source phải là thư mục ảnh, file ảnh hoặc file video: {source}")


def _iter_images(paths: list[Path], max_frames: int | None) -> Iterator[tuple[str, np.ndarray]]:
    """Đọc danh sách file ảnh, bỏ qua (kèm cảnh báo) file không đọc được."""
    count = 0
    for path in paths:
        if max_frames is not None and count >= max_frames:
            return
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            print(f"[cảnh báo] Không đọc được ảnh, bỏ qua: {path}")
            continue
        count += 1
        yield path.name, image


def _iter_video(
    path: Path, vid_stride: int, max_frames: int | None
) -> Iterator[tuple[str, np.ndarray]]:
    """Đọc video, lấy một khung hình sau mỗi `vid_stride` khung; tên có dạng <video>_f000123.jpg."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise OSError(f"Không mở được video: {path}")
    try:
        index = 0
        count = 0
        while True:
            if max_frames is not None and count >= max_frames:
                return
            ok, frame = cap.read()
            if not ok:
                return
            if index % vid_stride == 0:
                count += 1
                yield f"{path.stem}_f{index:06d}.jpg", frame
            index += 1
    finally:
        cap.release()
