"""Chọn khung từ video để gán nhãn: lấy mẫu theo thời gian, bỏ khung gần trùng bằng dHash, rải đều (docs/LABELING.md mục 1).

Phần dòng lệnh ở `tools/extract_frames.py`.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from eval.splits import dhash

ID_INVALID = re.compile(r"[^A-Za-z0-9.-]+")


@dataclass(frozen=True)
class Candidate:
    frame: int
    t_s: float
    hash: int


def make_video_id(name: str) -> str:
    """Mã video từ tên file: bỏ dấu tiếng Việt, chỉ giữ chữ, số, dấu chấm và gạch nối; dấu gạch dưới dành cho số khung."""
    ascii_name = unicodedata.normalize("NFKD", name.replace("đ", "d").replace("Đ", "D"))
    ascii_name = "".join(ch for ch in ascii_name if not unicodedata.combining(ch))
    video_id = ID_INVALID.sub("-", ascii_name).strip("-.")
    if not video_id:
        raise ValueError(f"Không tạo được mã video từ tên: {name!r}")
    return video_id


def select_frames(candidates: list[Candidate], max_frames: int, min_hamming: int) -> list[Candidate]:
    """Chọn khung: bỏ khung gần trùng mọi khung đã giữ (theo thứ tự thời gian), rồi rải đều nếu còn quá nhiều."""
    if max_frames < 1:
        raise ValueError(f"max_frames phải ≥ 1, nhận được {max_frames}")
    kept: list[Candidate] = []
    for cand in candidates:
        if all(bin(cand.hash ^ k.hash).count("1") >= min_hamming for k in kept):
            kept.append(cand)
    if len(kept) <= max_frames:
        return kept
    picks = np.unique(np.linspace(0, len(kept) - 1, max_frames).round().astype(int))
    return [kept[i] for i in picks]


def scan_video(path: Path, min_gap_s: float, min_std: float) -> tuple[list[Candidate], float]:
    """Lượt 1: đọc tuần tự, tính dHash ở mỗi khung cách nhau `min_gap_s` giây. Trả về ứng viên và FPS."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise OSError(f"Không mở được video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        cap.release()
        raise OSError(f"Video không có thông tin FPS: {path}")
    stride = max(1, round(fps * min_gap_s))
    candidates: list[Candidate] = []
    index = 0
    try:
        while True:
            if index % stride == 0:
                ok, frame = cap.read()
                if not ok:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if float(gray.std()) >= min_std:
                    candidates.append(Candidate(frame=index, t_s=index / fps, hash=dhash(gray)))
            elif not cap.grab():
                break
            index += 1
    finally:
        cap.release()
    return candidates, fps


def save_frames(path: Path, chosen: list[Candidate], out_dir: Path, video_id: str, jpeg_quality: int) -> list[Path]:
    """Lượt 2: đọc tuần tự lại và lưu đúng các khung đã chọn (đọc tuần tự chính xác hơn nhảy tới khung)."""
    wanted = {c.frame for c in chosen}
    last = max(wanted)
    files: list[Path] = []
    cap = cv2.VideoCapture(str(path))
    try:
        for index in range(last + 1):
            if index in wanted:
                ok, frame = cap.read()
                if not ok:
                    raise OSError(f"{path}: không đọc lại được khung {index}")
                file = out_dir / f"{video_id}_{index:06d}.jpg"
                if not cv2.imwrite(str(file), frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]):
                    raise OSError(f"Không ghi được {file}")
                files.append(file)
            elif not cap.grab():
                raise OSError(f"{path}: video kết thúc trước khung {index}")
    finally:
        cap.release()
    return files
