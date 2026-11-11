#!/usr/bin/env python3
"""Build a user manual (DOCX and/or PDF) from manual.json.

Usage: build_manual.py manual.json --outdir output [--formats docx,pdf] [--name "File name"]

Page numbers in the table of contents come from a two-pass layout: the DOCX is
converted to PDF with LibreOffice, heading pages are read from the PDF bookmarks,
the numbers are written into the table of contents, and the result is converted
again. Format reference: references/manual-spec.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Inches, Pt, RGBColor
from PIL import Image
from pypdf import PdfReader

LABELS = {
    "en": {
        "user_manual": "User Manual",
        "toc": "Table of Contents",
        "revision_history": "Revision History",
        "version": "Version",
        "date": "Date",
        "author": "Author",
        "changes": "Description of Changes",
        "prepared_by": "Prepared by",
        "figure": "Figure",
        "page": "Page",
        "tip": "Tip",
        "note": "Note",
        "warning": "Important",
    },
    "id": {
        "user_manual": "Panduan Pengguna",
        "toc": "Daftar Isi",
        "revision_history": "Riwayat Revisi",
        "version": "Versi",
        "date": "Tanggal",
        "author": "Penulis",
        "changes": "Keterangan Perubahan",
        "prepared_by": "Disusun oleh",
        "figure": "Gambar",
        "page": "Halaman",
        "tip": "Tips",
        "note": "Catatan",
        "warning": "Penting",
    },
}

PAPER = {"A4": (Cm(21.0), Cm(29.7)), "LETTER": (Inches(8.5), Inches(11))}
MARGIN = Cm(2.5)
HEADING_SIZES = {1: 20, 2: 15, 3: 12.5}
HEADING_NUMBER_WIDTH = {1: Cm(1.3), 2: Cm(1.5), 3: Cm(1.9)}
NOTE_COLORS = {"tip": ("E8F5E9", "2E7D32"), "note": ("E8F0FA", "1F4E79"), "warning": ("FFF4E5", "C0504D")}
STEP_INDENT = Cm(0.8)
MAX_IMAGE_HEIGHT = Cm(17)


class SpecError(Exception):
    pass


@dataclass
class Heading:
    level: int
    number: str
    title: str
    bookmark: str
    blocks: list
    children: list = field(default_factory=list)

    @property
    def text(self) -> str:
        return f"{self.number}  {self.title}"


# ---------------------------------------------------------------- spec


def load_spec(path: Path) -> dict:
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SpecError(f"{path}: invalid JSON: {e}") from e
    cover = spec.get("cover") or {}
    if not cover.get("app_name"):
        raise SpecError("cover.app_name is required")
    if not spec.get("sections"):
        raise SpecError("sections must contain at least one chapter")
    lang = spec.get("language", "en")
    labels = dict(LABELS.get(lang, {}))
    labels.update(spec.get("labels") or {})
    missing = sorted(set(LABELS["en"]) - set(labels))
    if missing:
        raise SpecError(f"language '{lang}' has no built-in labels; add a 'labels' object with: {', '.join(missing)}")
    spec["_labels"] = labels
    paper = str(spec.get("paper", "A4")).upper()
    if paper not in PAPER:
        raise SpecError(f"paper must be A4 or Letter, got {spec.get('paper')!r}")
    spec["_paper"] = paper
    return spec


def number_headings(sections: list, prefix: str = "", level: int = 1, counter: list | None = None) -> list[Heading]:
    counter = counter if counter is not None else [0]
    if sections and level > 3:
        raise SpecError(f"sections nest deeper than 3 levels under '{prefix.rstrip('.')}'; flatten them")
    out = []
    for i, sec in enumerate(sections, 1):
        if not isinstance(sec, dict) or not sec.get("title"):
            raise SpecError(f"every section needs a 'title' (problem near number {prefix}{i})")
        counter[0] += 1
        number = f"{prefix}{i}"
        h = Heading(level, number, sec["title"].strip(), f"_Toc{counter[0]:04d}", sec.get("blocks") or [])
        h.children = number_headings(sec.get("subsections") or [], number + ".", level + 1, counter)
        out.append(h)
    return out


def flatten(headings: list[Heading]) -> list[Heading]:
    out = []
    for h in headings:
        out.append(h)
        out.extend(flatten(h.children))
    return out


# ---------------------------------------------------------------- low-level XML helpers


def hex_color(value: str) -> RGBColor:
    value = value.lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", value):
        raise SpecError(f"invalid color {value!r}; use a hex value like #1F4E79")
    return RGBColor.from_string(value.upper())


def set_style_font(style, name: str, size: float | None = None, bold=None, color: RGBColor | None = None):
    style.font.name = name
    rfonts = style.element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rfonts.attrib.pop(qn(attr), None)
    rfonts.set(qn("w:eastAsia"), name)
    rfonts.set(qn("w:cs"), name)
    if size is not None:
        style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color


# Child order required by the OOXML schema (Word rejects files with misordered children).
TCPR_AFTER_BORDERS = ("w:shd", "w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark",
                      "w:headers", "w:cellIns", "w:cellDel", "w:cellMerge", "w:tcPrChange")
PPR_AFTER_PBDR = ("w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct",
                  "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd", "w:snapToGrid",
                  "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
                  "w:textDirection", "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle",
                  "w:rPr", "w:sectPr", "w:pPrChange")


def shade(cell, fill: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.insert_element_before(shd, *TCPR_AFTER_BORDERS[1:])


def cell_borders(cell, **edges):
    """edges: top/left/bottom/right = (size_eighths_pt, hex) or None for no border."""
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        spec = edges.get(edge)
        if spec:
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), str(spec[0]))
            el.set(qn("w:color"), spec[1])
        else:
            el.set(qn("w:val"), "nil")
        borders.append(el)
    tcPr.insert_element_before(borders, *TCPR_AFTER_BORDERS)


def paragraph_border(paragraph, edge: str, color: str, size: int = 8, space: int = 4):
    pPr = paragraph._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    el = OxmlElement(f"w:{edge}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(size))
    el.set(qn("w:space"), str(space))
    el.set(qn("w:color"), color)
    pbdr.append(el)
    pPr.insert_element_before(pbdr, *PPR_AFTER_PBDR)


def fld_char(run, kind: str):
    el = OxmlElement("w:fldChar")
    el.set(qn("w:fldCharType"), kind)
    run._r.append(el)


def instr_text(run, text: str):
    el = OxmlElement("w:instrText")
    el.set(qn("xml:space"), "preserve")
    el.text = text
    run._r.append(el)


def add_simple_field(paragraph, instr: str, placeholder: str, size: float | None = None, color=None):
    runs = [paragraph.add_run() for _ in range(3)]
    fld_char(runs[0], "begin")
    instr_text(runs[1], f" {instr} ")
    fld_char(runs[2], "separate")
    result = paragraph.add_run(placeholder)
    end = paragraph.add_run()
    fld_char(end, "end")
    for r in runs + [result, end]:
        if size:
            r.font.size = Pt(size)
        if color is not None:
            r.font.color.rgb = color


def add_bookmark(paragraph, name: str, bm_id: int):
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bm_id))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(bm_id))
    pPr = paragraph._p.pPr
    if pPr is not None:
        pPr.addnext(start)
    else:
        paragraph._p.insert(0, start)
    paragraph._p.append(end)


def wrap_hyperlink(paragraph, runs, anchor: str):
    link = OxmlElement("w:hyperlink")
    link.set(qn("w:anchor"), anchor)
    link.set(qn("w:history"), "1")
    runs[0]._r.addprevious(link)
    for r in runs:
        link.append(r._r)


def set_page_numbering(section, fmt: str, start: int | None):
    sectPr = section._sectPr
    for old in sectPr.findall(qn("w:pgNumType")):
        sectPr.remove(old)
    el = OxmlElement("w:pgNumType")
    el.set(qn("w:fmt"), fmt)
    if start is not None:
        el.set(qn("w:start"), str(start))
    cols = sectPr.find(qn("w:cols"))
    if cols is not None:
        cols.addprevious(el)
    else:
        sectPr.append(el)


def picture_outline(inline_shape, color: str = "BFBFBF"):
    spPr = inline_shape._inline.graphic.graphicData.pic.spPr
    ln = OxmlElement("a:ln")
    ln.set("w", "9525")
    fill = OxmlElement("a:solidFill")
    clr = OxmlElement("a:srgbClr")
    clr.set("val", color)
    fill.append(clr)
    ln.append(fill)
    spPr.append(ln)


def add_rich_text(paragraph, text: str, size: float | None = None, bold_all=False, color=None):
    """Adds text where **word** is bold."""
    for part in re.split(r"(\*\*.+?\*\*)", str(text)):
        if not part:
            continue
        is_bold = part.startswith("**") and part.endswith("**") and len(part) > 4
        run = paragraph.add_run(part[2:-2] if is_bold else part)
        run.bold = True if (is_bold or bold_all) else None
        if size:
            run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color


# ---------------------------------------------------------------- builder


class ManualBuilder:
    def __init__(self, spec: dict, base_dir: Path, pages: dict[str, str]):
        self.spec = spec
        self.base = base_dir
        self.pages = pages
        self.L = spec["_labels"]
        theme = spec.get("theme") or {}
        self.font = theme.get("font", "Arial")
        self.primary_hex = theme.get("primary_color", "#1F4E79").lstrip("#").upper()
        self.primary = hex_color(self.primary_hex)
        self.grey = RGBColor(0x59, 0x59, 0x59)
        self.doc = Document()
        self.headings = number_headings(spec["sections"])
        self.flat = flatten(self.headings)
        self.figure = [0, 0]  # chapter, figure-in-chapter
        self.bm_id = 0
        width, height = PAPER[spec["_paper"]]
        self.text_width = width - 2 * MARGIN

    # -- setup
    def setup(self):
        width, height = PAPER[self.spec["_paper"]]
        sec = self.doc.sections[0]
        sec.page_width, sec.page_height = width, height
        sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = MARGIN
        sec.footer_distance = Cm(1.2)
        sec.different_first_page_header_footer = True  # cover page has no footer

        styles = self.doc.styles
        normal = styles["Normal"]
        set_style_font(normal, self.font, 11)
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.15
        for level, size in HEADING_SIZES.items():
            st = styles[f"Heading {level}"]
            set_style_font(st, self.font, size, True, self.primary)
            st.font.italic = False
            pf = st.paragraph_format
            pf.space_before = Pt(18 if level == 1 else 12)
            pf.space_after = Pt(8 if level == 1 else 6)
            pf.keep_with_next = True
            pf.left_indent = HEADING_NUMBER_WIDTH[level]
            pf.first_line_indent = -HEADING_NUMBER_WIDTH[level]
            pf.tab_stops.add_tab_stop(HEADING_NUMBER_WIDTH[level])
        set_style_font(styles["List Bullet"], self.font, 11)

        footer = sec.footer.paragraphs[0]
        tabs = footer.paragraph_format.tab_stops
        for inherited in (Inches(3.25), Inches(6.5)):  # center/right stops of the built-in Footer style
            tabs.add_tab_stop(inherited, WD_TAB_ALIGNMENT.CLEAR)
        tabs.add_tab_stop(self.text_width, WD_TAB_ALIGNMENT.RIGHT)
        paragraph_border(footer, "top", "BFBFBF", 4, 6)
        cover = self.spec["cover"]
        r = footer.add_run(f"{cover['app_name']} – {cover.get('title') or self.L['user_manual']}\t{self.L['page']} ")
        r.font.size = Pt(9)
        r.font.color.rgb = self.grey
        add_simple_field(footer, "PAGE", "1", 9, self.grey)

    # -- front matter
    def cover(self):
        c = self.spec["cover"]
        d = self.doc
        top = d.add_paragraph()
        top.paragraph_format.space_before = Pt(60)
        if c.get("logo"):
            logo = self.resolve(c["logo"])
            w, h = Image.open(logo).size
            max_w, max_h = Cm(7), Cm(4)
            scale = min(max_w / w, max_h / h)
            top.alignment = WD_ALIGN_PARAGRAPH.CENTER
            top.add_run().add_picture(str(logo), width=Emu(int(w * scale)))
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(70)
        add_rich_text(p, c["app_name"], 32, True, self.primary)
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_rich_text(p, c.get("title") or self.L["user_manual"], 22, False, self.grey)
        paragraph_border(p, "bottom", self.primary_hex, 12, 12)
        if c.get("subtitle"):
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(12)
            add_rich_text(p, c["subtitle"], 13, False, self.grey)

        lines = [
            (self.L["version"], c.get("version")),
            (self.L["date"], c.get("date")),
            (self.L["prepared_by"], c.get("author")),
        ]
        first = True
        for label, value in lines:
            if not value:
                continue
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(2)
            if first:
                p.paragraph_format.space_before = Pt(150)
                first = False
            r = p.add_run(f"{label}: ")
            r.font.color.rgb = self.grey
            r.font.size = Pt(11)
            add_rich_text(p, value, 11, True)
        if c.get("company"):
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(18 if not first else 150)
            add_rich_text(p, c["company"], 13, True, self.primary)

    def page_title(self, text: str):
        p = self.doc.add_paragraph()
        p.paragraph_format.page_break_before = True
        p.paragraph_format.space_after = Pt(14)
        add_rich_text(p, text, HEADING_SIZES[1], True, self.primary)

    def revision_history(self):
        rows = self.spec.get("revision_history")
        if not rows:
            return
        self.page_title(self.L["revision_history"])
        cols = [("version", Cm(2.4)), ("date", Cm(3.2)), ("author", Cm(3.6)), ("changes", None)]
        last = self.text_width - sum(w for _, w in cols if w)
        t = self.doc.add_table(rows=1, cols=4)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, (key, width) in enumerate(cols):
            cell = t.rows[0].cells[i]
            cell.width = width or last
            shade(cell, self.primary_hex)
            cell.paragraphs[0].text = ""
            add_rich_text(cell.paragraphs[0], self.L[key], 10, True, RGBColor(0xFF, 0xFF, 0xFF))
        for row in rows:
            cells = t.add_row().cells
            for i, (key, width) in enumerate(cols):
                cells[i].width = width or last
                add_rich_text(cells[i].paragraphs[0], row.get(key, ""), 10)

    def toc(self):
        self.page_title(self.L["toc"])
        entries = []
        for h in self.flat:
            p = self.doc.add_paragraph()
            pf = p.paragraph_format
            pf.left_indent = Cm(0.6 * (h.level - 1)) + HEADING_NUMBER_WIDTH[h.level]
            pf.first_line_indent = -HEADING_NUMBER_WIDTH[h.level]
            pf.space_before = Pt(8 if h.level == 1 else 0)
            pf.space_after = Pt(3)
            pf.tab_stops.add_tab_stop(pf.left_indent)
            pf.tab_stops.add_tab_stop(self.text_width, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
            runs = [p.add_run(f"{h.number}\t{h.title}\t{self.pages.get(h.bookmark, '0')}")]
            runs[0].bold = h.level == 1
            wrap_hyperlink(p, runs, h.bookmark)
            entries.append(p)
        # Wrap the entries in a real TOC field so Word can refresh it (right-click > Update Field).
        first, last = entries[0], entries[-1]
        lead = [OxmlElement("w:r") for _ in range(3)]
        b, i, s = lead
        el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), "begin"); b.append(el)
        el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = ' TOC \\o "1-3" \\h \\z \\u '; i.append(el)
        el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), "separate"); s.append(el)
        anchor = first._p.pPr
        for r in lead:
            anchor.addnext(r)
            anchor = r
        end = OxmlElement("w:r")
        el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), "end"); end.append(el)
        last._p.append(end)

    # -- body
    def body(self):
        body = self.doc.add_section(WD_SECTION.NEW_PAGE)
        body.different_first_page_header_footer = False
        set_page_numbering(self.doc.sections[0], "lowerRoman", 1)
        set_page_numbering(body, "decimal", 1)
        for i, h in enumerate(self.headings):
            self.render_heading(h, first=(i == 0))

    def render_heading(self, h: Heading, first=False):
        if h.level == 1:
            self.figure = [int(h.number), 0]
        p = self.doc.add_paragraph(style=f"Heading {h.level}")
        p.add_run(f"{h.number}\t{h.title}")
        if h.level == 1 and not first:
            p.paragraph_format.page_break_before = True
        self.bm_id += 1
        add_bookmark(p, h.bookmark, self.bm_id)
        for block in h.blocks:
            self.render_block(block, h)
        for child in h.children:
            self.render_heading(child)

    def render_block(self, b: dict, h: Heading):
        kind = b.get("type")
        if kind == "paragraph":
            add_rich_text(self.doc.add_paragraph(), b["text"])
        elif kind == "steps":
            for n, item in enumerate(b["items"], b.get("start", 1)):
                item = {"text": item} if isinstance(item, str) else item
                p = self.doc.add_paragraph()
                pf = p.paragraph_format
                pf.left_indent, pf.first_line_indent = STEP_INDENT, -STEP_INDENT
                pf.tab_stops.add_tab_stop(STEP_INDENT)
                pf.space_after = Pt(4)
                r = p.add_run(f"{n}.\t")
                r.bold = True
                r.font.color.rgb = self.primary
                add_rich_text(p, item["text"])
                if item.get("image"):
                    pf.keep_with_next = True
                    self.image(item["image"], item.get("caption"), item.get("width_cm"), indent=STEP_INDENT)
        elif kind == "bullets":
            for item in b["items"]:
                add_rich_text(self.doc.add_paragraph(style="List Bullet"), item)
        elif kind == "image":
            self.image(b["path"], b.get("caption"), b.get("width_cm"))
        elif kind == "note":
            self.note(b.get("kind", "note"), b["text"])
        elif kind == "table":
            self.table(b["headers"], b["rows"], b.get("widths_cm"))
        elif kind == "page_break":
            self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        else:
            raise SpecError(f"section {h.number}: unknown block type {kind!r}")

    def resolve(self, path: str) -> Path:
        p = Path(path).expanduser()
        p = p if p.is_absolute() else self.base / p
        if not p.is_file():
            raise SpecError(f"file not found: {p}")
        return p

    def image(self, path: str, caption: str | None, width_cm: float | None, indent=Cm(0)):
        src = self.resolve(path)
        w, h = Image.open(src).size
        max_w = self.text_width - indent
        width = min(Cm(width_cm), max_w) if width_cm else max_w
        if width * h / w > MAX_IMAGE_HEIGHT:
            width = int(MAX_IMAGE_HEIGHT * w / h)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.left_indent = indent
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.keep_with_next = bool(caption)
        pic = p.add_run().add_picture(str(src), width=Emu(int(width)))
        picture_outline(pic)
        if caption:
            self.figure[1] += 1
            c = self.doc.add_paragraph()
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.paragraph_format.left_indent = indent
            c.paragraph_format.space_after = Pt(12)
            r = c.add_run(f"{self.L['figure']} {self.figure[0]}.{self.figure[1]}: ")
            r.bold, r.italic = True, True
            r.font.size = Pt(9.5)
            r.font.color.rgb = self.grey
            add_rich_text(c, caption, 9.5, False, self.grey)
            for r in c.runs[1:]:
                r.italic = True

    def note(self, kind: str, text: str):
        if kind not in NOTE_COLORS:
            raise SpecError(f"note kind must be one of {', '.join(NOTE_COLORS)}, got {kind!r}")
        fill, edge = NOTE_COLORS[kind]
        t = self.doc.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = t.rows[0].cells[0]
        cell.width = self.text_width
        shade(cell, fill)
        cell_borders(cell, left=(24, edge))
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(4)
        r = p.add_run(f"{self.L[kind]}: ")
        r.bold = True
        r.font.color.rgb = hex_color(edge)
        add_rich_text(p, text)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)

    def table(self, headers: list, rows: list, widths_cm: list | None):
        t = self.doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        widths = [Cm(w) for w in widths_cm] if widths_cm else [int(self.text_width / len(headers))] * len(headers)
        for i, text in enumerate(headers):
            cell = t.rows[0].cells[i]
            cell.width = widths[i]
            shade(cell, self.primary_hex)
            add_rich_text(cell.paragraphs[0], text, 10, True, RGBColor(0xFF, 0xFF, 0xFF))
        for row in rows:
            if len(row) != len(headers):
                raise SpecError(f"table row {row!r} has {len(row)} cells, expected {len(headers)}")
            cells = t.add_row().cells
            for i, text in enumerate(row):
                cells[i].width = widths[i]
                add_rich_text(cells[i].paragraphs[0], text, 10)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)

    def build(self, out: Path):
        self.setup()
        self.cover()
        self.revision_history()
        self.toc()
        self.body()
        props = self.doc.core_properties
        props.title = f"{self.spec['cover']['app_name']} – {self.spec['cover'].get('title') or self.L['user_manual']}"
        props.author = self.spec["cover"].get("author") or ""
        props.language = self.spec.get("language", "en")
        self.doc.save(out)


# ---------------------------------------------------------------- LibreOffice / pagination


def find_soffice() -> str:
    candidates = [
        os.environ.get("SOFFICE"),
        shutil.which("soffice"),
        shutil.which("libreoffice"),
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    raise SpecError("LibreOffice not found. Install it (see scripts/setup.sh) or set SOFFICE=/path/to/soffice")


def to_pdf(soffice: str, docx: Path, outdir: Path) -> Path:
    profile = Path(tempfile.gettempdir()) / "user-manual-skill-lo-profile"
    cmd = [
        soffice, "--headless", "--norestore", "--nolockcheck",
        f"-env:UserInstallation={profile.as_uri()}",
        "--convert-to", 'pdf:writer_pdf_Export:{"ExportBookmarks":{"type":"boolean","value":"true"}}',
        "--outdir", str(outdir), str(docx),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    pdf = outdir / f"{docx.stem}.pdf"
    if res.returncode != 0 or not pdf.is_file():
        raise SpecError(f"LibreOffice PDF export failed:\n{res.stdout}\n{res.stderr}")
    return pdf


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s).casefold()


def heading_pages(pdf: Path, flat: list[Heading]) -> dict[str, str]:
    reader = PdfReader(str(pdf))
    outline = []

    def walk(items):
        for it in items:
            if isinstance(it, list):
                walk(it)
            else:
                outline.append((norm(it.title), reader.get_destination_page_number(it)))

    walk(reader.outline)
    pages, pos = {}, 0
    for h in flat:
        want = norm(f"{h.number}{h.title}")
        while pos < len(outline) and outline[pos][0] != want:
            pos += 1
        if pos == len(outline):
            raise SpecError(f"could not find heading '{h.number} {h.title}' in the PDF bookmarks")
        pages[h.bookmark] = outline[pos][1]
        pos += 1
    body_start = pages[flat[0].bookmark]
    return {k: str(v - body_start + 1) for k, v in pages.items()}


def safe_name(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "", text).strip() or "User Manual"


def render_previews(pdf: Path, outdir: Path) -> list[Path]:
    import pypdfium2 as pdfium

    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("page-*.png"):
        old.unlink()
    doc = pdfium.PdfDocument(str(pdf))
    out = []
    for i, page in enumerate(doc, 1):
        path = outdir / f"page-{i:02d}.png"
        page.render(scale=100 / 72).to_pil().save(path)
        out.append(path)
    doc.close()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path, help="manual.json")
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--formats", default="docx,pdf", help="docx, pdf, or docx,pdf (default)")
    ap.add_argument("--name", help="output file name without extension (default: '<App> - <User Manual>')")
    ap.add_argument("--preview", type=Path, help="also render every page to PNG in this folder, for checking the layout")
    args = ap.parse_args()

    formats = {f.strip().lower() for f in args.formats.split(",") if f.strip()}
    if not formats or formats - {"docx", "pdf"}:
        ap.error("--formats must be docx, pdf, or docx,pdf")
    try:
        spec = load_spec(args.spec)
        base = args.spec.resolve().parent
        name = safe_name(args.name or f"{spec['cover']['app_name']} - {spec['cover'].get('title') or spec['_labels']['user_manual']}")
        soffice = find_soffice()
        args.outdir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="user-manual-") as tmp:
            tmp = Path(tmp)
            docx = tmp / f"{name}.docx"
            pages: dict[str, str] = {}
            for attempt in range(4):
                builder = ManualBuilder(spec, base, pages)
                builder.build(docx)
                pdf = to_pdf(soffice, docx, tmp)
                found = heading_pages(pdf, builder.flat)
                if found == pages:
                    break
                pages = found
            else:
                raise SpecError("table of contents page numbers did not settle after 4 passes")

            written = []
            for fmt, src in (("docx", docx), ("pdf", pdf)):
                if fmt in formats:
                    dest = args.outdir / src.name
                    shutil.copyfile(src, dest)
                    written.append(dest)
            page_count = len(PdfReader(str(pdf)).pages)
            if args.preview:
                previews = render_previews(pdf, args.preview)
    except SpecError as e:
        sys.exit(f"error: {e}")

    print(f"Table of contents ({page_count} pages in total including cover and front matter):")
    for h in builder.flat:
        print(f"{'  ' * (h.level - 1)}{h.number}  {h.title} .... {pages[h.bookmark]}")
    for path in written:
        print(f"wrote {path}")
    if args.preview:
        print(f"page previews: {previews[0].parent}/page-01.png … page-{len(previews):02d}.png")


if __name__ == "__main__":
    main()
