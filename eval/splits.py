"""Chia tập theo video và phát hiện rò rỉ dữ liệu giữa các tập (TECHNICAL mục 15.6).

Khung liền nhau của cùng một video gần như giống hệt nhau. Chia ngẫu nhiên theo khung thì tập test chứa "bản sao"
của ảnh huấn luyện, và số đo bị thổi phồng. Hai lớp phòng vệ:
1. Chia theo nhóm (video): mọi khung của một video nằm trọn trong một tập.
2. Kiểm tra ảnh gần trùng bằng dHash: bắt cả trường hợp cùng cảnh nhưng khác tên video (tải lại, cắt lại).
"""

from __future__ import annotations

import random
import re
from pathlib import Path

import numpy as np

# Quy ước tên khung của tập lũ: <video_id>_<số khung 6 chữ số> (docs/LABELING.md).
DEFAULT_GROUP_PATTERN = r"^(.+)_\d{6}$"


def group_of(stem: str, pattern: str = DEFAULT_GROUP_PATTERN) -> str:
    """Mã nhóm (video) từ tên file không đuôi: nhóm bắt đầu tiên của pattern; không khớp thì mỗi ảnh là một nhóm."""
    match = re.match(pattern, stem)
    return match.group(1) if match else stem


def assign_groups(group_sizes: dict[str, int], ratios: list[float], seed: int = 0) -> dict[str, int]:
    """Gán mỗi nhóm vào một tập (chỉ số trong ratios) sao cho số ảnh mỗi tập gần với tỉ lệ yêu cầu.

    Xáo các nhóm theo seed rồi lần lượt cho vào tập đang thiếu nhiều nhất so với chỉ tiêu. Cùng seed và cùng danh
    sách nhóm thì cùng kết quả, không phụ thuộc thứ tự đọc file.
    """
    if not ratios or any(r < 0 for r in ratios) or sum(ratios) <= 0:
        raise ValueError(f"ratios không hợp lệ: {ratios}")
    groups = sorted(group_sizes)
    random.Random(seed).shuffle(groups)
    total = sum(group_sizes.values())
    targets = [r / sum(ratios) * total for r in ratios]
    filled = [0] * len(ratios)
    assignment: dict[str, int] = {}
    for group in groups:
        split = max(range(len(ratios)), key=lambda i: targets[i] - filled[i])
        assignment[group] = split
        filled[split] += group_sizes[group]
    return assignment


def dhash(image_bgr: np.ndarray) -> int:
    """Difference hash 64 bit: so độ sáng hai điểm kề nhau trên ảnh xám thu về 9×8. Bền với nén, đổi kích thước nhẹ."""
    import cv2

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if image_bgr.ndim == 3 else image_bgr
    small = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int(sum(1 << i for i, bit in enumerate(bits) if bit))


def hamming_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Số bit khác nhau giữa từng cặp hash (mảng uint64), kích thước (len(a), len(b))."""
    xor = (a[:, None] ^ b[None, :]).astype(np.uint64)
    return np.unpackbits(xor.view(np.uint8).reshape(*xor.shape, 8), axis=-1).sum(axis=-1)


def near_duplicates(
    hashes_a: dict[str, int], hashes_b: dict[str, int] | None = None, max_distance: int = 5
) -> list[tuple[str, str, int]]:
    """Các cặp ảnh có hash cách nhau ≤ max_distance bit; hashes_b=None thì tìm trong cùng một tập (bỏ cặp với chính nó)."""
    names_a = list(hashes_a)
    names_b = names_a if hashes_b is None else list(hashes_b)
    if not names_a or not names_b:
        return []
    a = np.array([hashes_a[n] for n in names_a], dtype=np.uint64)
    b = a if hashes_b is None else np.array([hashes_b[n] for n in names_b], dtype=np.uint64)
    pairs: list[tuple[str, str, int]] = []
    for start in range(0, len(a), 512):  # chia khối để ma trận không quá lớn với tập vài chục nghìn ảnh
        dist = hamming_matrix(a[start : start + 512], b)
        for i, j in zip(*np.nonzero(dist <= max_distance)):
            i = int(i) + start
            if hashes_b is None and j <= i:
                continue
            pairs.append((names_a[i], names_b[j], int(dist[i - start, j])))
    return pairs


def image_paths(folder: Path) -> list[Path]:
    """Ảnh trong thư mục, sắp theo tên."""
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in exts)
