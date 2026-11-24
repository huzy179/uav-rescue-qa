"""Dựng quyển tiếng Anh (`docs/thesis/*.md`) thành một file Word theo mẫu MSE của FPT University.

Các bước:
1. Dựng file tham chiếu (reference.docx) từ file mặc định của pandoc: khổ A4, lề trên dưới 2,54 cm, trái 3,0 cm,
   phải 2,8 cm; Times New Roman 12, giãn dòng 1,5, không lùi đầu dòng, cách 12 pt trước đoạn; chương sang trang mới;
   chân trang có số trang. Bảng và mã lệnh dùng chữ nhỏ hơn, giãn dòng đơn để vừa trang.
2. Ghép Markdown theo thứ tự của mẫu: hai trang bìa, trang tên đề tài và tóm tắt, lời cảm ơn, mục lục, danh mục
   bảng, danh mục hình, bảng viết tắt, chương 1–8, tài liệu tham khảo, phụ lục. Bỏ ghi chú bản nháp (đoạn trích dẫn
   mở đầu bằng "Draft note"); dòng "**Table N.M.** …" đứng trước một bảng thành chú thích bảng, để danh mục bảng
   tự sinh được. Các dấu [PENDING …], [FIGURE] vẫn giữ để người đọc bản nháp thấy.
3. Chạy pandoc với trích dẫn APA (citeproc, `references.bib`, `apa.csl`).
4. Chia ba phần trang: bìa không số trang, phần đầu số La Mã (i, ii…), từ chương 1 số Ả Rập (1, 2…); bật cập nhật
   trường khi mở để Word điền mục lục và danh mục bảng (Word hỏi một lần khi mở file).

Ví dụ:
    .venv/bin/python tools/build_thesis.py --config configs/thesis.yaml
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from shared.config import parse_args_with_config

THESIS = Path("docs/thesis")
CHAPTERS = ["ch1_introduction.md", "ch2_background.md", "ch3_requirements_architecture.md", "ch4_methods.md",
            "ch5_implementation_qa.md", "ch6_data_setup.md", "ch7_results.md", "ch8_conclusion.md"]
APPENDICES = ["appendix_a_labeling.md", "appendix_b_reproduction.md", "appendix_d_tests.md"]
BREAK_MARK = "FLOODEYE-SECTION-BREAK-{}"
TABLE_CAPTION = re.compile(r"^\*\*Table [A-Z\d]+\.\d+\.\*\*")

# Lề theo hướng dẫn trình bày (twip: 1 cm = 567 twip); khổ A4.
PAGE = '<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1587" w:bottom="1440" w:left="1701" ' \
       'w:header="709" w:footer="709" w:gutter="0"/>'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--title", required=True, help="Tên đề tài tiếng Anh (trang bìa)")
    parser.add_argument("--author", required=True)
    parser.add_argument("--supervisor", required=True)
    parser.add_argument("--year", required=True, help="Năm bảo vệ (trang bìa)")
    parser.add_argument("--degree", default="Master of Software Engineering")
    parser.add_argument("--output", type=Path, default=Path("runs/thesis/FloodEye_thesis.docx"))
    parser.add_argument("--pandoc", default=None, help="Đường dẫn pandoc (mặc định tìm trong PATH rồi ~/.local/bin)")
    parser.add_argument("--keep-draft-notes", action="store_true", help="Giữ ghi chú bản nháp trong file Word")
    parser.add_argument("--keep-markdown", action="store_true", help="Ghi thêm bản Markdown đã ghép cạnh file Word")
    return parser


# ---------- Ghép Markdown ----------

def strip_draft_notes(text: str) -> str:
    """Bỏ các đoạn trích dẫn (dòng bắt đầu bằng ">") có chữ "Draft note"; đoạn trích dẫn khác giữ nguyên."""
    out, block = [], []
    for line in text.splitlines() + [""]:
        if line.lstrip().startswith(">"):
            block.append(line)
            continue
        if block:
            if "Draft note" not in "\n".join(block):
                out.extend(block)
            block = []
        out.append(line)
    return "\n".join(out[:-1]).lstrip("\n") + "\n"


def captions_to_pandoc(text: str) -> str:
    """Dòng "**Table N.M.** …" mà dòng không trống kế tiếp là bảng thì thành chú thích bảng của pandoc (": …")."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if TABLE_CAPTION.match(line):
            nxt = next((later for later in lines[i + 1:] if later.strip()), "")
            if nxt.lstrip().startswith("|"):
                lines[i] = ": " + line
    return "\n".join(lines) + "\n"


def sections(text: str) -> dict[str, str]:
    """Tách một file theo tiêu đề cấp 2 ("## Abstract") → {tên mục: nội dung không kèm tiêu đề}."""
    found: dict[str, str] = {}
    for part in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
        name, _, body = part.partition("\n")
        found[name.strip()] = body.strip() + "\n"
    return found


def raw(xml: str) -> str:
    return f"\n```{{=openxml}}\n{xml}\n```\n"


def styled(style: str, text: str) -> str:
    return f'\n::: {{custom-style="{style}"}}\n{text}\n:::\n'


def page_break() -> str:
    return raw('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')


def field_block(title: str, instruction: str) -> str:
    """Tiêu đề phần đầu cùng một trường TOC rỗng; Word điền khi cập nhật trường."""
    return styled("Front Heading", title) + raw(
        '<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve">{instruction}</w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        '<w:r><w:t>Right-click and choose Update Field.</w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')


def cover(args: argparse.Namespace, with_supervisor: bool) -> str:
    lines = ["MINISTRY OF EDUCATION AND TRAINING", "FPT UNIVERSITY", "", "", args.title, "", "by", "", args.author, "", "",
             "A thesis submitted in conformity with the requirements", f"for the degree of {args.degree}"]
    if with_supervisor:
        lines += ["", f"Supervisor: {args.supervisor}"]
    lines += ["", "", f"© Copyright by {args.author} {args.year}"]
    paragraphs = [styled("Cover Title" if text == args.title else "Cover", text if text else " ") for text in lines]
    return "".join(paragraphs)


def assemble(args: argparse.Namespace, thesis_dir: Path = THESIS) -> str:
    def load(name: str) -> str:
        text = (thesis_dir / name).read_text(encoding="utf-8")
        text = text if args.keep_draft_notes else strip_draft_notes(text)
        return captions_to_pandoc(text)

    front = sections(load("front_matter.md"))
    parts = [cover(args, with_supervisor=False), page_break(), cover(args, with_supervisor=True),
             raw(f'<w:p><w:r><w:t>{BREAK_MARK.format("cover")}</w:t></w:r></w:p>')]
    parts.append(styled("Cover Title", args.title) + styled("Cover", f"{args.author}") +
                 styled("Cover", f"{args.degree}") + styled("Cover", "FPT University") + styled("Cover", args.year))
    parts.append(styled("Abstract Title", "Abstract") + styled("Abstract Text", front["Abstract"]))
    parts.append(styled("Front Heading", "Acknowledgments") + "\n" + front["Acknowledgments"])
    parts.append(field_block("Table of Contents", 'TOC \\o "1-3" \\h \\z \\u'))
    parts.append(field_block("List of Tables", 'TOC \\h \\z \\t "Table Caption,1"'))
    parts.append(field_block("List of Figures", 'TOC \\h \\z \\t "Image Caption,1"'))
    parts.append(styled("Front Heading", "List of Abbreviations") + "\n" + front["List of Abbreviations"])
    parts.append(raw(f'<w:p><w:r><w:t>{BREAK_MARK.format("front")}</w:t></w:r></w:p>'))
    parts += [load(name) for name in CHAPTERS]
    parts.append("\n# References\n\n::: {#refs}\n:::\n")
    parts += [load(name) for name in APPENDICES]
    return "\n".join(parts)


# ---------- File tham chiếu ----------

STYLE_PATCHES = {
    # styleId: (pPr thêm vào, rPr thêm vào)
    "Normal": ('<w:spacing w:before="240" w:after="0" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/>',
               '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Times New Roman" '
               'w:cs="Times New Roman"/><w:sz w:val="24"/><w:szCs w:val="24"/>'),
    "BodyText": ('<w:spacing w:before="240" w:after="0" w:line="360" w:lineRule="auto"/>', ""),
    "FirstParagraph": ('<w:spacing w:before="240" w:after="0" w:line="360" w:lineRule="auto"/>', ""),
    "Compact": ('<w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/><w:jc w:val="left"/>',
                '<w:sz w:val="20"/><w:szCs w:val="20"/>'),
    "SourceCode": ('<w:spacing w:before="120" w:after="120" w:line="240" w:lineRule="auto"/>', ""),
    "VerbatimChar": ("", '<w:sz w:val="17"/><w:szCs w:val="17"/>'),
    "Heading1": ('<w:keepNext/><w:pageBreakBefore/><w:spacing w:before="0" w:after="240"/><w:outlineLvl w:val="0"/>',
                 '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>'
                 '<w:b/><w:color w:val="000000"/><w:sz w:val="32"/><w:szCs w:val="32"/>'),
    "Heading2": ('<w:keepNext/><w:spacing w:before="360" w:after="120"/><w:outlineLvl w:val="1"/>',
                 '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>'
                 '<w:b/><w:color w:val="000000"/><w:sz w:val="28"/><w:szCs w:val="28"/>'),
    "Heading3": ('<w:keepNext/><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="2"/>',
                 '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>'
                 '<w:b/><w:i w:val="0"/><w:color w:val="000000"/><w:sz w:val="24"/><w:szCs w:val="24"/>'),
    "TableCaption": ('<w:keepNext/><w:spacing w:before="240" w:after="120" w:line="240" w:lineRule="auto"/>'
                     '<w:jc w:val="left"/>', '<w:i w:val="0"/><w:sz w:val="22"/><w:szCs w:val="22"/>'),
    "Bibliography": ('<w:spacing w:before="120" w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="567" '
                     'w:hanging="567"/><w:jc w:val="left"/>', ""),
}

NEW_STYLES = [
    # (styleId, tên, pPr, rPr)
    ("Cover", "Cover", '<w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/><w:jc w:val="center"/>',
     '<w:b/><w:sz w:val="26"/><w:szCs w:val="26"/>'),
    ("CoverTitle", "Cover Title", '<w:spacing w:before="240" w:after="240"/><w:jc w:val="center"/>',
     '<w:b/><w:sz w:val="36"/><w:szCs w:val="36"/>'),
    ("FrontHeading", "Front Heading", '<w:keepNext/><w:pageBreakBefore/><w:spacing w:before="0" w:after="240"/>'
     '<w:jc w:val="center"/>', '<w:b/><w:sz w:val="32"/><w:szCs w:val="32"/>'),
    ("AbstractTitle", "Abstract Title", '<w:keepNext/><w:spacing w:before="480" w:after="240"/><w:jc w:val="center"/>',
     '<w:b/><w:sz w:val="32"/><w:szCs w:val="32"/>'),
    ("AbstractText", "Abstract Text", '<w:spacing w:before="240" w:after="0" w:line="480" w:lineRule="auto"/>', ""),
]


def patch_styles(xml: str) -> str:
    """Sửa kiểu chữ trong styles.xml của file tham chiếu mặc định của pandoc."""
    for style_id, (ppr, rpr) in STYLE_PATCHES.items():
        m = re.search(rf'<w:style [^>]*w:styleId="{style_id}"[^>]*>.*?</w:style>', xml, flags=re.DOTALL)
        if m is None:
            body = f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{style_id}"><w:name w:val="{style_id}"/>' \
                   f'<w:basedOn w:val="Normal"/><w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>'
            xml = xml.replace("</w:styles>", body + "</w:styles>")
            continue
        style = m.group(0)
        style = re.sub(r"<w:pPr>.*?</w:pPr>|<w:pPr/>", "", style, flags=re.DOTALL)
        style = re.sub(r"<w:rPr>.*?</w:rPr>|<w:rPr/>", "", style, flags=re.DOTALL)
        style = style.replace("</w:style>", f"<w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>")
        xml = xml.replace(m.group(0), style)
    for style_id, name, ppr, rpr in NEW_STYLES:
        xml = xml.replace("</w:styles>", f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{style_id}">'
                          f'<w:name w:val="{name}"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr>{ppr}</w:pPr>'
                          f'<w:rPr>{rpr}</w:rPr></w:style></w:styles>')
    return xml


FOOTER = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
          '<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
          '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>'
          '<w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')
FOOTER_REL = ('<Relationship Id="rIdFloodEyeFooter" '
              'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>')
FOOTER_TYPE = ('<Override PartName="/word/footer1.xml" '
               'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>')
BODY_SECT = (f'<w:sectPr><w:footerReference w:type="default" r:id="rIdFloodEyeFooter"/>{PAGE}'
             '<w:pgNumType w:fmt="decimal" w:start="1"/><w:cols w:space="720"/></w:sectPr>')


def rewrite_zip(src: Path, dst: Path, edits: dict[str, str]) -> None:
    """Chép một file docx (zip), thay hoặc thêm các phần trong edits."""
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename not in edits:
                zout.writestr(item, zin.read(item.filename))
        for name, text in edits.items():
            zout.writestr(name, text)


def make_reference(pandoc: str, dst: Path) -> None:
    default = dst.with_name("pandoc_default.docx")
    subprocess.run([pandoc, "-o", str(default), "--print-default-data-file", "reference.docx"], check=True)
    with zipfile.ZipFile(default) as z:
        styles = z.read("word/styles.xml").decode("utf-8")
        document = z.read("word/document.xml").decode("utf-8")
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
        types = z.read("[Content_Types].xml").decode("utf-8")
    document = re.sub(r"<w:sectPr\b.*?</w:sectPr>", BODY_SECT, document, flags=re.DOTALL)
    if 'xmlns:r=' not in document:
        document = document.replace("<w:document ", '<w:document xmlns:r="http://schemas.openxmlformats.org/'
                                    'officeDocument/2006/relationships" ', 1)
    rewrite_zip(default, dst, {
        "word/styles.xml": patch_styles(styles),
        "word/document.xml": document,
        "word/footer1.xml": FOOTER,
        "word/_rels/document.xml.rels": rels.replace("</Relationships>", FOOTER_REL + "</Relationships>"),
        "[Content_Types].xml": types.replace("</Types>", FOOTER_TYPE + "</Types>"),
    })
    default.unlink()


# ---------- Hậu xử lý file Word ----------

def split_sections(document: str) -> str:
    """Thay hai đoạn đánh dấu bằng ngắt phần: bìa không số trang, phần đầu số La Mã; phần chính giữ sectPr cuối."""
    last = re.findall(r"<w:sectPr\b.*?</w:sectPr>", document, flags=re.DOTALL)
    if not last:
        raise ValueError("Không thấy sectPr cuối trong document.xml (file tham chiếu sai?)")
    body = last[-1]
    page = "".join(re.findall(r"<w:pgSz[^>]*/>|<w:pgMar[^>]*/>", body))
    front = re.sub(r"<w:pgNumType[^>]*/>", '<w:pgNumType w:fmt="lowerRoman" w:start="1"/>', body)
    sections_xml = {"cover": f'<w:sectPr>{page}<w:titlePg/></w:sectPr>', "front": front}
    for name, sect in sections_xml.items():
        mark = re.compile(rf"<w:p>(?:(?!</w:p>).)*?{BREAK_MARK.format(name)}.*?</w:p>", flags=re.DOTALL)
        if not mark.search(document):
            raise ValueError(f"Không thấy đoạn đánh dấu {BREAK_MARK.format(name)}")
        document = mark.sub(f"<w:p><w:pPr>{sect}</w:pPr></w:p>", document, count=1)
    return document


# Phần tử đứng sau updateFields trong CT_Settings; Word báo file hỏng nếu sai thứ tự.
AFTER_UPDATE_FIELDS = re.compile(r"<(?:w:hdrShapeDefaults|w:footnotePr|w:endnotePr|w:compat|w:docVars|w:rsids|m:mathPr|"
                                 r"w:attachedSchema|w:themeFontLang|w:clrSchemeMapping|w:doNotIncludeSubdocsInStats|"
                                 r"w:doNotAutoCompressPictures|w:forceUpgrade|w:captions|w:readModeInkLockDown|"
                                 r"w:smartTagType|sl:schemaLibrary|w:shapeDefaults|w:doNotEmbedSmartTags|"
                                 r"w:decimalSymbol|w:listSeparator)\b")


def enable_update_fields(settings: str) -> str:
    """Thêm updateFields đúng chỗ trong thứ tự của CT_Settings để Word điền mục lục khi mở file."""
    if "w:updateFields" in settings:
        return settings
    tag = '<w:updateFields w:val="true"/>'
    m = AFTER_UPDATE_FIELDS.search(settings)
    if m:
        return settings[:m.start()] + tag + settings[m.start():]
    return settings.replace("</w:settings>", tag + "</w:settings>")


def postprocess(docx: Path) -> None:
    tmp = docx.with_suffix(".tmp.docx")
    with zipfile.ZipFile(docx) as z:
        document = z.read("word/document.xml").decode("utf-8")
        settings = z.read("word/settings.xml").decode("utf-8")
    rewrite_zip(docx, tmp, {"word/document.xml": split_sections(document),
                            "word/settings.xml": enable_update_fields(settings)})
    tmp.replace(docx)


def find_pandoc(explicit: str | None) -> str:
    candidates = [explicit] if explicit else [shutil.which("pandoc"), str(Path.home() / ".local/bin/pandoc")]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise SystemExit("Không tìm thấy pandoc (cài vào ~/.local/bin hoặc truyền --pandoc)")


def main() -> int:
    args = parse_args_with_config(build_parser())
    pandoc = find_pandoc(args.pandoc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    markdown = assemble(args)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        reference = tmp / "reference.docx"
        make_reference(pandoc, reference)
        source = tmp / "thesis.md"
        source.write_text(markdown, encoding="utf-8")
        if args.keep_markdown:
            shutil.copy(source, args.output.with_suffix(".md"))
        subprocess.run([pandoc, str(source), "-f", "markdown", "-o", str(args.output), "--reference-doc", str(reference),
                        "--citeproc", "--bibliography", str(THESIS / "references.bib"), "--csl", str(THESIS / "apa.csl"),
                        "--resource-path", str(THESIS)], check=True)
    postprocess(args.output)
    print(f"Đã dựng {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
