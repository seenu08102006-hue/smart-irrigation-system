"""
report_lib.py - small helper layer on top of python-docx for an IEEE-style report.
(headings with Roman numerals, numbered figures/tables, captions, code blocks, page-number footer)
"""
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import config  # noqa: E402

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV"]
GREEN = RGBColor(0x14, 0x53, 0x2D)


def _field(run, instr):
    """Insert a Word field (PAGE, TOC...) into a run."""
    for kind, text in (("begin", None), (None, instr), ("separate", None), (None, "1"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        elif text == instr:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = instr
        else:
            el = OxmlElement("w:t")
            el.text = text
        run._r.append(el)


class Report:
    def __init__(self):
        self.doc = Document()
        self.sec_no = 0
        self.fig_no = 0
        self.tab_no = 0
        s = self.doc.sections[0]
        s.page_width, s.page_height = Cm(21.0), Cm(29.7)
        s.left_margin = s.right_margin = Cm(2.2)
        s.top_margin, s.bottom_margin = Cm(2.2), Cm(2.0)
        st = self.doc.styles["Normal"]
        st.font.name = "Times New Roman"
        st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        st.font.size = Pt(11.5)
        st.paragraph_format.line_spacing = 1.25
        st.paragraph_format.space_after = Pt(6)
        for name, size in (("Heading 1", 14), ("Heading 2", 12.5), ("Heading 3", 11.5)):
            h = self.doc.styles[name]
            h.font.name = "Times New Roman"
            h.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.color.rgb = GREEN
            h.paragraph_format.space_before = Pt(14 if name == "Heading 1" else 10)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.keep_with_next = True
        # footer with page number
        fp = s.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run()
        r.font.size = Pt(10)
        _field(r, "PAGE")

    # ---------------- text ----------------
    def h1(self, title, numbered=True):
        if numbered:
            self.sec_no += 1
            self.sub_no = 0
            title = f"{ROMAN[self.sec_no - 1]}. {title.upper()}"
        self.doc.add_heading(title, level=1)

    def h2(self, title):
        self.sub_no += 1
        letter = chr(64 + self.sub_no)
        self.doc.add_heading(f"{letter}. {title}", level=2)

    def h3(self, title):
        self.doc.add_heading(title, level=3)

    def p(self, text, bold_lead=None, italic=False, align="justify", size=None):
        para = self.doc.add_paragraph()
        para.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER,
                          "left": WD_ALIGN_PARAGRAPH.LEFT}[align]
        if bold_lead:
            para.add_run(bold_lead + " ").bold = True
        run = para.add_run(text)
        run.italic = italic
        if size:
            run.font.size = Pt(size)
        return para

    def bullets(self, items, style="List Bullet"):
        for it in items:
            para = self.doc.add_paragraph(style=style)
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            if isinstance(it, tuple):
                para.add_run(it[0] + " ").bold = True
                para.add_run(it[1])
            else:
                para.add_run(it)

    def numbered(self, items):
        self.bullets(items, "List Number")

    def equation(self, text, number):
        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = para.add_run(f"{text}        ({number})")
        r.italic = True
        r.font.name = "Cambria Math"

    def code(self, text, size=7.5):
        for line in text.rstrip("\n").split("\n"):
            para = self.doc.add_paragraph()
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.line_spacing = 1.0
            para.paragraph_format.left_indent = Cm(0.3)
            run = para.add_run(line if line else " ")
            run.font.name = "Consolas"
            run.element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
            run.font.size = Pt(size)

    # ---------------- figures / tables ----------------
    def figure(self, filename, caption, width=14.5):
        path = os.path.join(config.FIG_DIR, filename)
        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.keep_with_next = True
        para.add_run().add_picture(path, width=Cm(width))
        self.fig_no += 1
        cap = self.doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cap.add_run(f"Fig. {self.fig_no}. {caption}")
        r.font.size = Pt(10)
        r.italic = True
        return self.fig_no

    def table(self, headers, rows, caption, widths=None, size=9.5):
        self.tab_no += 1
        cap = self.doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.keep_with_next = True
        r = cap.add_run(f"TABLE {ROMAN[self.tab_no - 1]}\n{caption.upper()}")
        r.font.size = Pt(9.5)
        t = self.doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(headers):
            cell = t.rows[0].cells[i]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(h))
            run.bold = True
            run.font.size = Pt(size)
            run.font.color.rgb = RGBColor(255, 255, 255)
            tcPr = cell._tc.get_or_add_tcPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:fill"), "166534")
            tcPr.append(shd)
        for row in rows:
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = ""
                run = cells[i].paragraphs[0].add_run(str(v))
                run.font.size = Pt(size)
        for row in t.rows:
            for c in row.cells:
                for para in c.paragraphs:
                    para.paragraph_format.space_after = Pt(2)
                    para.paragraph_format.line_spacing = 1.0
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def toc(self):
        para = self.doc.add_paragraph()
        _field(para.add_run(), 'TOC \\o "1-2" \\h \\z \\u')

    def save(self, path):
        self.doc.save(path)
