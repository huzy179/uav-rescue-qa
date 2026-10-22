"""Kiểm tra dựng lại bố cục AFO: ảnh rải ở nhiều PART, nhãn và danh sách chia tập ở PART_1."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def make_afo(src: Path) -> None:
    part1 = src / "PART_1" / "PART_1"
    (part1 / "images").mkdir(parents=True)
    (part1 / "6categories").mkdir()
    (src / "PART_2" / "PART_2" / "images").mkdir(parents=True)
    for name, part in (("a_1.jpg", part1), ("a_2.jpg", part1), ("k_1.jpg", src / "PART_2" / "PART_2"), ("x_9.jpg", part1)):
        (part / "images" / name).write_bytes(b"jpg")
    (part1 / "6categories" / "a_1.txt").write_text("0 0.5 0.5 0.1 0.1\n2 0.2 0.2 0.1 0.1\n")
    (part1 / "6categories" / "k_1.txt").write_text("0 0.4 0.4 0.1 0.1\n")
    (part1 / "6categories.names").write_text("human\nwind/sup-board\nboat\n")
    (part1 / "train.txt").write_text("a_1.jpg\na_2.jpg\n")
    (part1 / "validation.txt").write_text("")
    (part1 / "test.txt").write_text("k_1.jpg")  # dòng cuối không có ký tự xuống dòng, như bản gốc


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)


def test_dung_bo_cuc_va_chuyen_nhan(tmp_path: Path) -> None:
    src, out, dst = tmp_path / "afo", tmp_path / "afo_yolo", tmp_path / "processed"
    make_afo(src)
    result = run("tools/prepare_afo.py", "--src", str(src), "--out", str(out))
    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in (out / "images" / "train").iterdir()) == ["a_1.jpg", "a_2.jpg"]
    assert [p.name for p in (out / "images" / "test").iterdir()] == ["k_1.jpg"]  # ảnh từ PART_2
    assert (out / "labels" / "train" / "a_2.txt").read_text() == ""  # ảnh không có file nhãn
    assert "Ảnh không thuộc tập nào (bỏ qua): 1" in result.stdout  # x_9.jpg

    result = run("tools/convert_yolo_subset.py", "--src", str(out), "--dst", str(dst),
                 "--names-file", str(out / "classes.txt"), "--keep", "human", "--splits", "train", "val", "test")
    assert result.returncode == 0, result.stderr
    assert (dst / "labels" / "train" / "a_1.txt").read_text() == "0 0.5 0.5 0.1 0.1\n"  # thuyền (lớp 2) bị bỏ


def test_anh_trong_danh_sach_nhung_thieu_file(tmp_path: Path) -> None:
    src = tmp_path / "afo"
    make_afo(src)
    (src / "PART_1" / "PART_1" / "test.txt").write_text("k_1.jpg\nkhong_co.jpg\n")
    result = run("tools/prepare_afo.py", "--src", str(src), "--out", str(tmp_path / "out"))
    assert result.returncode != 0
    assert "khong_co.jpg" in result.stderr


def test_thu_nho_anh_lon(tmp_path: Path) -> None:
    import cv2
    import numpy as np

    src, out = tmp_path / "afo", tmp_path / "afo_yolo"
    make_afo(src)
    big = src / "PART_1" / "PART_1" / "images" / "a_1.jpg"
    cv2.imwrite(str(big), np.full((300, 400, 3), 128, dtype=np.uint8))
    small_src = src / "PART_1" / "PART_1" / "images" / "a_2.jpg"
    cv2.imwrite(str(small_src), np.full((50, 80, 3), 128, dtype=np.uint8))
    for other in (src / "PART_2" / "PART_2" / "images" / "k_1.jpg", src / "PART_1" / "PART_1" / "images" / "x_9.jpg"):
        cv2.imwrite(str(other), np.full((40, 40, 3), 128, dtype=np.uint8))
    result = run("tools/prepare_afo.py", "--src", str(src), "--out", str(out), "--max-side", "100")
    assert result.returncode == 0, result.stderr
    assert cv2.imread(str(out / "images" / "train" / "a_1.jpg")).shape[:2] == (75, 100)  # cạnh dài 400 → 100
    assert cv2.imread(str(out / "images" / "train" / "a_2.jpg")).shape[:2] == (50, 80)  # đã nhỏ hơn: giữ nguyên
