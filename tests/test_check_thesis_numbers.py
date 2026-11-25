"""Kiểm số của quyển tiếng Anh (tools/check_thesis_numbers.py)."""

from __future__ import annotations

from pathlib import Path

from tools.check_thesis_numbers import check, numbers_in, source_text


def test_numbers_in_bo_dau_tru_va_so_nguyen() -> None:
    assert numbers_in("AP50 rises from 0.235 to 0.531 (−0.011 to −0.003), 32 tiles, Table 4.2.") == [
        "0.235", "0.531", "0.011", "0.003", "4.2"]


def test_tim_so_dau_phay_va_bao_tieng_viet(tmp_path: Path) -> None:
    (tmp_path / "kq.md").write_text("AP50 0,531 và 0,235\n", encoding="utf-8")
    (tmp_path / "bang.csv").write_text("a,b\n5.574,1\n", encoding="utf-8")
    ch = tmp_path / "ch.md"
    ch.write_text("> Draft note 9.99 bỏ qua\nAP50 0.531, t_resize 5.574, wrong 0.999\ncòn sót chữ\n", encoding="utf-8")
    missing, vn = check([ch], source_text([tmp_path / "kq.md", tmp_path / "bang.csv"]))
    assert [(line, n) for _, line, n in missing] == [(2, "0.999")]
    assert [line for _, line, _ in vn] == [3]


def test_bo_qua_so_bang_va_so_muc(tmp_path: Path) -> None:
    from tools.check_thesis_numbers import labels_in

    ch = tmp_path / "ch7.md"
    ch.write_text("## 7.3 Results\n\n**Table 7.11.** Recall by tag.\n\n![**Figure 7.12.** Plot.](f.png)\n\n"
                  "As Tables 7.11 and 7.3 and Figure 7.12 show, AP50 0.999.\n",
                  encoding="utf-8")
    labels = labels_in([ch])
    assert labels == {"7.3", "7.11", "7.12"}
    missing, _ = check([ch], "", labels)
    assert [n for _, _, n in missing] == ["0.999"]


def test_bao_tham_chieu_hong(tmp_path: Path) -> None:
    from tools.check_thesis_numbers import broken_references

    ch = tmp_path / "ch7.md"
    ch.write_text("# Chapter 7. Results\n\n## 7.1 First\n\n**Table 7.1.** A.\n\n![**Figure 7.1.** B.](f.png)\n\n"
                  "As Tables 7.1 and 7.2 show (Section 7.1, Figure 7.1, Chapter 8, Appendix B).\n"
                  "> Draft note: Table 9.9 ignored.\n", encoding="utf-8")
    refs = [r for _, _, r in broken_references([ch], [ch])]
    assert refs == ["Table 7.2", "Chapter 8", "Chapter B"]
