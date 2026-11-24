"""Kiểm tra các bước dựng quyển Word (tools/build_thesis.py) không cần pandoc: ghép Markdown và sửa XML."""

from __future__ import annotations

import pytest

from tools.build_thesis import (BREAK_MARK, captions_to_pandoc, enable_update_fields, patch_styles, sections,
                                split_sections, strip_draft_notes)


def test_bo_ghi_chu_ban_nhap_giu_trich_dan_khac() -> None:
    text = "# Ch\n\n> **Draft note.** remove\n> second line\n\nBody.\n\n> A real quote.\n"
    assert strip_draft_notes(text) == "# Ch\n\n\nBody.\n\n> A real quote.\n"


def test_chu_thich_bang_chi_khi_dung_truoc_bang() -> None:
    text = "**Table 7.1.** Caption.\n\n| a |\n|---|\n\n**Table A.2.** Also.\n| b |\n\n**Table 7.2.** No table.\n\nText.\n"
    out = captions_to_pandoc(text).splitlines()
    assert out[0] == ": **Table 7.1.** Caption."
    assert out[5] == ": **Table A.2.** Also."
    assert out[8] == "**Table 7.2.** No table."


def test_tach_muc_cap_hai() -> None:
    text = "# Front\n\n> note\n\n## Abstract\n\nShort.\n\n## List of Abbreviations\n\n| a |\n"
    assert sections(text) == {"Abstract": "Short.\n", "List of Abbreviations": "| a |\n"}


DOC = ('<w:document><w:body><w:p><w:r><w:t>cover</w:t></w:r></w:p>'
       f'<w:p><w:r><w:t>{BREAK_MARK.format("cover")}</w:t></w:r></w:p><w:p><w:r><w:t>abstract</w:t></w:r></w:p>'
       f'<w:p><w:r><w:t>{BREAK_MARK.format("front")}</w:t></w:r></w:p><w:p><w:r><w:t>chapter</w:t></w:r></w:p>'
       '<w:sectPr><w:footerReference r:id="rId9" w:type="default"/><w:pgSz w:w="11906" w:h="16838"/>'
       '<w:pgMar w:top="1440"/><w:pgNumType w:fmt="decimal" w:start="1"/></w:sectPr></w:body></w:document>')


def test_chia_ba_phan_trang() -> None:
    out = split_sections(DOC)
    assert "FLOODEYE" not in out
    cover, front, body = out.split("<w:sectPr>")[1:]
    assert "footerReference" not in cover and "<w:titlePg/>" in cover and "pgSz" in cover
    assert 'w:fmt="lowerRoman"' in front and "footerReference" in front
    assert 'w:fmt="decimal"' in body
    assert out.index("abstract") < out.index('w:fmt="lowerRoman"') < out.index("chapter")


def test_thieu_dau_ngat_phan_thi_bao_loi() -> None:
    with pytest.raises(ValueError):
        split_sections(DOC.replace(BREAK_MARK.format("front"), "x"))


def test_update_fields_dung_thu_tu() -> None:
    settings = '<w:settings x="1"><w:zoom/><w:savePreviewPicture/><w:rsids></w:rsids><w:themeFontLang/></w:settings>'
    out = enable_update_fields(settings)
    assert out.index("<w:savePreviewPicture/>") < out.index("w:updateFields") < out.index("<w:rsids>")
    assert enable_update_fields(out) == out


def test_sua_kieu_chu_giu_cap_de_muc() -> None:
    styles = ('<w:styles><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>'
              '<w:pPr><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:sz w:val="40"/></w:rPr></w:style></w:styles>')
    out = patch_styles(styles)
    heading = out[out.index('w:styleId="Heading1"'):out.index("</w:style>")]
    assert "<w:pageBreakBefore/>" in heading and '<w:outlineLvl w:val="0"/>' in heading and 'w:val="40"' not in heading
    assert 'w:styleId="Compact"' in out and 'w:styleId="FrontHeading"' in out
