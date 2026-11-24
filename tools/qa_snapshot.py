"""Chụp số liệu kiểm thử và cỡ mã cho chương 5 và phụ lục D của quyển (chạy lúc khoá mã).

Ghi vào thư mục đích (mặc định `runs/qa/`):
- `pytest.xml`, `pytest.txt`: kết quả chạy toàn bộ test;
- `commit.txt`: commit hiện tại, thêm ` dirty` nếu cây làm việc có thay đổi chưa commit;
- `code_lines.csv`: số file Python và số dòng (mọi dòng, kể cả dòng trống) của từng gói;
- `test_files.csv`: số test của từng file test, đọc từ `pytest.xml`.

`--only-test-files` chỉ dựng lại `test_files.csv` từ `pytest.xml` đã có (không chạy test, không đếm lại mã), để
phụ lục D khớp đúng bản chụp mà chương 5 đang dẫn.

Ví dụ:
    .venv/bin/python tools/qa_snapshot.py
    .venv/bin/python tools/qa_snapshot.py --only-test-files
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from shared.config import parse_args_with_config

PACKAGES = ["edge", "ground", "shared", "sim", "eval", "tools", "scripts", "console", "training", "tests"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=Path("runs/qa"), help="Thư mục ghi kết quả")
    parser.add_argument("--only-test-files", action="store_true", help="Chỉ dựng test_files.csv từ pytest.xml đã có")
    return parser


def code_lines(root: Path, packages: list[str]) -> list[dict[str, object]]:
    """Số file .py và tổng số dòng của mỗi gói (bỏ qua __pycache__)."""
    rows = []
    for package in packages:
        files = sorted(p for p in (root / package).rglob("*.py") if "__pycache__" not in p.parts)
        lines = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in files)
        rows.append({"package": package, "python_files": len(files), "lines": lines})
    return rows


def count_tests_per_file(junit_xml: Path) -> list[dict[str, object]]:
    """Số test của từng file, theo `classname` của JUnit (`tests.test_ground` → `test_ground.py`), xếp theo tên."""
    counts: Counter[str] = Counter()
    for case in ET.parse(junit_xml).getroot().iter("testcase"):
        module = case.get("classname", "").split(".")
        name = next((part for part in module if part.startswith("test_")), None)
        if name is None:
            raise ValueError(f"Không nhận ra file test của testcase {case.get('name')!r} (classname {case.get('classname')!r})")
        counts[f"{name}.py"] += 1
    return [{"file": f, "tests": n} for f, n in sorted(counts.items())]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args_with_config(build_parser())
    out: Path = args.output
    out.mkdir(parents=True, exist_ok=True)
    if not args.only_test_files:
        result = subprocess.run([sys.executable, "-m", "pytest", f"--junitxml={out / 'pytest.xml'}"],
                                capture_output=True, text=True)
        (out / "pytest.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True,
                               check=True).stdout.strip()
        (out / "commit.txt").write_text(commit + (" dirty" if dirty else "") + "\n", encoding="utf-8")
        write_csv(out / "code_lines.csv", code_lines(Path("."), PACKAGES))
        if result.returncode != 0:
            print(f"pytest thoát mã {result.returncode}; xem {out / 'pytest.txt'}", file=sys.stderr)
    rows = count_tests_per_file(out / "pytest.xml")
    write_csv(out / "test_files.csv", rows)
    print(f"{sum(int(r['tests']) for r in rows)} test trong {len(rows)} file -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
