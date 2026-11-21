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
