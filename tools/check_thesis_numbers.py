"""Kiểm số của quyển tiếng Anh (docs/thesis/): mọi số thập phân phải có trong một nguồn đã đo (docs/KE_HOACH_QUYEN.md mục 3).

Quyển dùng dấu chấm (0.497), tài liệu kết quả dùng dấu phẩy (0,497). Script lấy mọi số thập phân trong các chương,
đổi sang dạng dấu phẩy rồi tìm trong các nguồn (mặc định `docs/results/`, `configs/`, `runs/gsd`, `runs/qa`, `data/processed/*/stats*.json`,
`docs/TECHNICAL.md` và danh mục tài liệu tham khảo; không lấy nháp tiếng Việt vì nó cũng là bản chép). Số không tìm thấy được liệt kê kèm file và dòng để kiểm tay: có thể là số chép sai,
số tính tay (phải thay bằng số trong file), hoặc số lấy từ bài báo khác (giữ, đã có trích dẫn). Cũng báo các từ
tiếng Việt còn sót trong quyển (chữ có dấu tiếng Việt ngoài ghi chú bản nháp).

Ví dụ:
    .venv/bin/python tools/check_thesis_numbers.py
    .venv/bin/python tools/check_thesis_numbers.py --thesis docs/thesis/ch4_methods.md
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from shared.config import parse_args_with_config

NUMBER = re.compile(r"(?<![\w.,])[−-]?\d+\.\d+(?![\w.]*\d)")
VIETNAMESE = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", re.IGNORECASE)
# Không lấy nháp tiếng Việt làm nguồn (nó cũng là bản chép); chỉ số đo, cấu hình, thống kê dữ liệu, TECHNICAL (công thức)
# và danh mục tài liệu tham khảo (số của bài báo khác).
DEFAULT_SOURCES = ["docs/results", "configs", "runs/gsd", "runs/qa", "docs/TECHNICAL.md", "pyproject.toml",
                   "docs/luan_van/tai_lieu_tham_khao.md", *map(str, sorted(Path("data/processed").glob("*/stats*.json")))]
# Không lấy cả runs/ (hàng triệu toạ độ box làm số nào cũng "tìm thấy") và không lấy nháp tiếng Việt (cũng là bản chép).


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--thesis", type=Path, nargs="+", default=None, help="Các file của quyển (mặc định docs/thesis/*.md: chương, phần mở đầu, phụ lục)")
    parser.add_argument("--sources", type=Path, nargs="+", default=[Path(p) for p in DEFAULT_SOURCES],
                        help="Thư mục hoặc file chứa số đã đo")
    return parser


def numbers_in(line: str) -> list[str]:
    """Số thập phân dấu chấm trong một dòng, bỏ dấu trừ (nguồn có thể ghi − hoặc -)."""
    return [m.group(0).lstrip("−-") for m in NUMBER.finditer(line)]


def to_comma(number: str) -> str:
    return number.replace(".", ",")


def source_text(paths: list[Path]) -> str:
    """Gộp nội dung mọi file văn bản trong các nguồn; CSV, YAML giữ dấu chấm nên thêm cả bản dấu phẩy."""
    parts = []
    for root in paths:
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.suffix in {".md", ".csv", ".yaml", ".json", ".txt"})
        for f in files:
            text = f.read_text(encoding="utf-8", errors="ignore")
            parts.append(text)
            if f.suffix != ".md":
                parts.append(text.replace(".", ","))
    return "\n".join(parts)


def in_draft_note(line: str) -> bool:
    return line.lstrip().startswith(">")


LABEL = re.compile(r"^\*\*(?:Table|Figure) (\d+\.\d+)\.\*\*|^#+ (\d+\.\d+) ")


def labels_in(chapters: list[Path]) -> set[str]:
    """Số bảng, số hình và số mục hai cấp được định nghĩa trong quyển ("**Table 7.11.**", "## 7.3 …").

    Khi nhắc tới chúng ("Table 7.11", "Tables 7.13–7.16") chúng trông như số thập phân; bỏ qua để danh sách cần kiểm
    tay chỉ còn số đo thật. Một số đo trùng đúng một số bảng sẽ bị bỏ qua theo; chấp nhận vì hiếm.
    """
    found = set()
    for path in chapters:
        for line in path.read_text(encoding="utf-8").splitlines():
            m = LABEL.match(line)
            if m:
                found.add(m.group(1) or m.group(2))
    return found


def check(chapters: list[Path], sources: str, labels: set[str] | None = None,
          ) -> tuple[list[tuple[Path, int, str]], list[tuple[Path, int, str]]]:
    """Trả (số không tìm thấy, dòng còn tiếng Việt), mỗi mục là (file, số dòng, nội dung); bỏ qua số trong labels."""
    labels = labels or set()
    missing, vietnamese = [], []
    for path in chapters:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if in_draft_note(line):
                continue
            for number in numbers_in(line):
                if number not in labels and to_comma(number) not in sources and number not in sources:
                    missing.append((path, i, number))
            if VIETNAMESE.search(line):
                vietnamese.append((path, i, line.strip()[:100]))
    return missing, vietnamese


def main() -> None:
    args = parse_args_with_config(build_parser())
    chapters = args.thesis or sorted(Path("docs/thesis").glob("*.md"))
    missing, vietnamese = check(chapters, source_text(args.sources), labels_in(sorted(Path("docs/thesis").glob("*.md"))))
    for path, line, number in missing:
        print(f"{path}:{line}: {number} không có trong nguồn")
    for path, line, text in vietnamese:
        print(f"{path}:{line}: còn tiếng Việt: {text}")
    print(f"{len(chapters)} file; {len(missing)} số cần kiểm tay; {len(vietnamese)} dòng còn tiếng Việt")


if __name__ == "__main__":
    main()
