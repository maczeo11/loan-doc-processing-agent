"""
FinScan AI - REDESIGN (Swiss / International Typographic Style)
Drastic departure: one type family (Bahnschrift/DIN), strict 12-col grid, asymmetric
flush-left layout, ONE accent colour, no cards, no rounded corners, no decoration.
Diagrams rebuilt as scientific figures: panel labels, message-titles, accent only on signal.

Outputs to: <repo>/scratch/FinScan_Redesign_Swiss.pptx
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn
import os

REPO = r"C:\Users\bhanu\mycodes\cognizant-hackathon"
OUT_DIR = os.path.join(REPO, "scratch")
OUT = os.path.join(OUT_DIR, "FinScan_Redesign_Swiss.pptx")
SRC_DECK = os.path.join(REPO, "FinScan_AI_Hackathon_Deck.pptx")
C = os.path.join(REPO, "presentation_assets", "crops")
A = os.path.join(REPO, "presentation_assets")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------- palette: black / paper / ONE accent ----------------
PAPER = RGBColor(0xF2, 0xF1, 0xEC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK   = RGBColor(0x14, 0x13, 0x11)
GREY  = RGBColor(0x8C, 0x89, 0x82)
GREY_L= RGBColor(0xC9, 0xC6, 0xBE)
RULE  = RGBColor(0x14, 0x13, 0x11)
HAIR  = RGBColor(0xBE, 0xBB, 0xB3)
ACC   = RGBColor(0x99, 0x1B, 0x1B)      # the ONE accent - product oxblood

# ---------------- type: one family, many weights ----------------
F_LT  = "Bahnschrift Light"
F_SL  = "Bahnschrift SemiLight"
F_RG  = "Bahnschrift"
F_SB  = "Bahnschrift SemiBold"
F_CN  = "Bahnschrift Condensed"
F_MN  = "Consolas"

SW, SH = Inches(13.333), Inches(7.5)
M = Inches(0.75)                      # margin
CW = SW - 2 * M
GUT = Inches(0.18)
COLW = (CW - 11 * GUT) / 12

TOTAL = 18


def E(v): return int(round(v))


def col(i, span=1):
    """x position and width for grid columns (1-indexed)."""
    x = M + (i - 1) * (COLW + GUT)
    w = span * COLW + (span - 1) * GUT
    return E(x), E(w)


class Box:
    __slots__ = ("x", "y", "w", "h")
    def __init__(self, x, y, w, h): self.x, self.y, self.w, self.h = E(x), E(y), E(w), E(h)
    @property
    def right(self): return self.x + self.w
    @property
    def bottom(self): return self.y + self.h
    @property
    def cx(self): return E(self.x + self.w / 2)
    @property
    def cy(self): return E(self.y + self.h / 2)


def gbox(i, span, y, h):
    x, w = col(i, span)
    return Box(x, y, w, h)


prs = Presentation()
prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]


def slide(bg=PAPER):
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
    r.fill.solid(); r.fill.fore_color.rgb = bg
    r.line.fill.background(); r.shadow.inherit = False
    s.shapes._spTree.remove(r._element); s.shapes._spTree.insert(2, r._element)
    return s


def T(s, box, txt, size=12, color=INK, font=F_RG, align=PP_ALIGN.LEFT,
      anchor=MSO_ANCHOR.TOP, spacing=1.15, caps=False, space_after=0):
    tb = s.shapes.add_textbox(box.x, box.y, box.w, box.h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, ln in enumerate(txt.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        if space_after: p.space_after = Pt(space_after)
        r = p.add_run(); r.text = ln.upper() if caps else ln
        r.font.size = Pt(size); r.font.color.rgb = color; r.font.name = font
        r.font.bold = False
    return tb


def block(s, box, fill=INK):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, box.x, box.y, box.w, box.h)
    r.fill.solid(); r.fill.fore_color.rgb = fill
    r.line.fill.background(); r.shadow.inherit = False
    return r


def frame(s, box, color=HAIR, w=0.75):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, box.x, box.y, box.w, box.h)
    r.fill.background()
    r.line.color.rgb = color; r.line.width = Pt(w)
    r.shadow.inherit = False
    return r


def hrule(s, x1, y, x2, color=RULE, w=1.0):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(x1), E(y), E(x2), E(y))
    c.line.color.rgb = color; c.line.width = Pt(w); c.shadow.inherit = False
    return c


def vrule(s, x, y1, y2, color=RULE, w=1.0):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(x), E(y1), E(x), E(y2))
    c.line.color.rgb = color; c.line.width = Pt(w); c.shadow.inherit = False
    return c


def arrow(s, x1, y1, x2, y2, color=INK, w=1.0):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(x1), E(y1), E(x2), E(y2))
    c.line.color.rgb = color; c.line.width = Pt(w)
    ln = c.line._get_or_add_ln()
    ln.append(ln.makeelement(qn('a:tailEnd'), {'type': 'triangle', 'w': 'sm', 'len': 'sm'}))
    c.shadow.inherit = False
    return c


def pic(s, path, box):
    return s.shapes.add_picture(path, box.x, box.y, width=box.w, height=box.h)


def fit(aspect, box):
    w, h = box.w, E(box.w / aspect)
    if h > box.h: h, w = box.h, E(box.h * aspect)
    return Box(box.x, box.y, w, h)


# ---------------- master furniture ----------------
EYE_Y = Inches(0.62)
TITLE_Y = Inches(1.06)
RULE_Y = Inches(2.16)
BODY = Inches(2.52)
FOLIO_Y = Inches(6.82)


def head(s, eyebrow, title, panel=None, sub=None):
    """Swiss two-zone header: label column left, message-title in the wide column."""
    x, w = col(1, 3)
    T(s, Box(x, EYE_Y, w, Inches(0.24)), eyebrow, size=8.5, color=ACC, font=F_SB, caps=True)
    x, w = col(1, 2)
    if panel:
        T(s, Box(x, Inches(1.06), w, Inches(0.6)), panel, size=40, color=GREY_L, font=F_LT)
    tx, tw = col(3, 10)
    T(s, Box(tx, TITLE_Y, tw, Inches(0.9)), title, size=33, color=INK, font=F_LT, spacing=1.06)
    if sub:
        T(s, Box(tx, Inches(1.74), tw, Inches(0.32)), sub, size=12.5, color=GREY, font=F_RG)
    hrule(s, M, RULE_Y, SW - M, color=RULE, w=1.25)


def folio(s, n):
    x, w = col(1, 2)
    T(s, Box(x, FOLIO_Y, w, Inches(0.4)), f"{n:02d}", size=26, color=GREY_L, font=F_LT)
    tx, tw = col(3, 10)
    T(s, Box(tx, Inches(6.98), tw, Inches(0.24)),
      "FinScan AI   /   Loan Document Processing & Verification Agent", size=8,
      color=GREY, font=F_MN)


def caption(s, box, txt, size=10):
    T(s, box, txt, size=size, color=GREY, font=F_RG, spacing=1.25)


NOTE_SRC = Presentation(SRC_DECK)
NOTES = [sl.notes_slide.notes_text_frame.text if sl.has_notes_slide else "" for sl in NOTE_SRC.slides]


def carry_notes(s, idx):
    if idx - 1 < len(NOTES) and NOTES[idx - 1]:
        s.notes_slide.notes_text_frame.text = NOTES[idx - 1]


# =====================================================================
# 01 TITLE
# =====================================================================
s = slide(INK)
x, w = col(1, 2)
T(s, Box(col(1, 4)[0], Inches(0.62), col(1, 4)[1], Inches(0.24)),
  "Cognizant GenAI + Cloud-Tools Buildathon", size=8.5, color=ACC, font=F_SB, caps=True)
tx, tw = col(3, 9)
T(s, Box(tx, Inches(1.9), tw, Inches(1.5)), "FinScan AI", size=88, color=PAPER, font=F_LT)
hrule(s, tx, Inches(3.52), SW - M, color=RGBColor(0x3A, 0x38, 0x34), w=1)
T(s, Box(tx, Inches(3.74), E(COLW * 6), Inches(0.9)),
  "Loan Document\nProcessing & Verification Agent", size=21, color=PAPER, font=F_SL, spacing=1.2)
vx, vw = col(9, 4)
T(s, Box(vx, Inches(3.74), vw, Inches(1.2)),
  "Turns a fragmented loan dossier\ninto an evidence-backed,\nreview-ready credit appraisal.",
  size=13, color=GREY, font=F_RG, spacing=1.35)
hrule(s, tx, Inches(5.5), SW - M, color=RGBColor(0x3A, 0x38, 0x34), w=1)
T(s, Box(x, Inches(5.72), w, Inches(0.24)), "Team", size=8.5, color=GREY, font=F_SB, caps=True)
T(s, Box(tx, Inches(5.68), tw, Inches(0.8)),
  "Bhanu Teja   Manjunath   Jeevan   Sravanthi\nKarthik   Balaji   Akshaya   Sai Mokshith",
  size=13.5, color=PAPER, font=F_LT, spacing=1.45)
T(s, Box(x, FOLIO_Y, w, Inches(0.4)), "01", size=26, color=RGBColor(0x45, 0x43, 0x3E), font=F_LT)
carry_notes(s, 1)

# =====================================================================
# 02 PROBLEM  — figure: five document ticks on a spine
# =====================================================================
s = slide()
head(s, "The problem", "Five documents.\nOne story that has to match.", panel="A")
docs = ["Application\nform", "Payslips\n3 months", "Bank\nstatements", "ITR-V\nacknowledgement", "KYC\nID proof"]
y0 = Inches(2.9)
for i, d in enumerate(docs):
    b = gbox(3 + i * 2, 2, y0, Inches(1.5))
    vrule(s, b.x, y0, y0 + Inches(1.5), color=HAIR, w=1)
    T(s, Box(b.x + Inches(0.14), y0 + Inches(0.06), b.w - Inches(0.2), Inches(0.3)),
      f"{i+1:02d}", size=11, color=GREY_L, font=F_RG)
    T(s, Box(b.x + Inches(0.14), y0 + Inches(0.42), b.w - Inches(0.2), Inches(0.9)),
      d, size=13, color=INK, font=F_SL, spacing=1.2)
hrule(s, col(3, 10)[0], Inches(4.62), SW - M, color=RULE, w=1)

pains = [("Cross-document", "The payslip, the bank statement\nand the ITR must agree."),
         ("Traceability", "Every figure has to be\nfindable on a page."),
         ("Time", "24-72 hours of manual\nreconciliation per dossier.")]
for i, (t, d) in enumerate(pains):
    b = gbox(3 + i * 3, 3, Inches(4.92), Inches(1.3))
    T(s, Box(b.x, b.y, b.w, Inches(0.3)), t, size=14, color=ACC, font=F_SB)
    T(s, Box(b.x, b.y + Inches(0.38), b.w, Inches(0.9)), d, size=11.5, color=GREY, font=F_RG, spacing=1.3)
folio(s, 2)
carry_notes(s, 2)

# =====================================================================
# 03 CORE IDEA — three vertical zones, accent only on Human
# =====================================================================
s = slide()
head(s, "The core idea", "Deterministic code decides.\nAI explains. A human approves.", panel="B")
zones = [("01", "Deterministic", "Computes every number,\nratio and verdict.", "Rules / arithmetic / evidence", INK),
         ("02", "AI-assisted", "Reads, retrieves\nand explains.", "Classification / RAG / narrative", INK),
         ("03", "Human", "Owns the lending\ndecision.", "Review / correction / sign-off", ACC)]
for i, (num, name, big, small, c) in enumerate(zones):
    b = gbox(3 + i * 3 + (1 if i else 0), 3, Inches(2.9), Inches(2.6))
    vrule(s, b.x, b.y, b.bottom, color=c, w=2.25 if c == ACC else 1.25)
    T(s, Box(b.x + Inches(0.18), b.y, b.w - Inches(0.2), Inches(0.3)), num, size=10, color=GREY_L, font=F_RG)
    T(s, Box(b.x + Inches(0.18), b.y + Inches(0.34), b.w - Inches(0.2), Inches(0.36)),
      name, size=17, color=c, font=F_SB)
    T(s, Box(b.x + Inches(0.18), b.y + Inches(0.9), b.w - Inches(0.2), Inches(0.9)),
      big, size=14.5, color=INK, font=F_LT, spacing=1.28)
    T(s, Box(b.x + Inches(0.18), b.y + Inches(2.1), b.w - Inches(0.2), Inches(0.4)),
      small, size=10, color=GREY, font=F_MN)
T(s, gbox(3, 10, Inches(5.86), Inches(0.4)),
  "Arithmetic must be provable. Explanations must be readable. "
  "Lending decisions must stay accountable to a person.",
  size=11.5, color=GREY, font=F_RG)
folio(s, 3)
carry_notes(s, 3)

# =====================================================================
# 04 PIPELINE — measured spine with ticks (the anchor figure)
# =====================================================================
s = slide()
head(s, "What we built", "One pipeline. Seven stages.\nIt stops before the last one.", panel="C")
stages = ["Upload\ndossier", "Understand\ndocuments", "Extract\nverified facts", "Run financial\nchecks",
          "Retrieve\npolicy", "Draft grounded\nmemo", "Human\nreview"]
spine_y = Inches(3.55)
x0, _ = col(3, 1)
x1 = SW - M - Inches(1.55)          # reserve room for the last tick's label
hrule(s, x0, spine_y, x1, color=RULE, w=1.5)
step = (x1 - x0) / 6
for i, st in enumerate(stages):
    cxp = x0 + i * step
    last = (i == 6)
    c = ACC if last else INK
    vrule(s, cxp, spine_y - Inches(0.16), spine_y + Inches(0.16), color=c, w=2.5 if last else 1.5)
    off = Inches(0.16) if last else Inches(-0.1)   # stage 07 lives beyond the wall
    T(s, Box(cxp + off, spine_y - Inches(0.92), Inches(1.6), Inches(0.4)),
      f"{i+1:02d}", size=20, color=c, font=F_LT)
    T(s, Box(cxp + off, spine_y + Inches(0.32), Inches(1.5), Inches(0.8)),
      st, size=11.5, color=INK if not last else ACC, font=F_SL, spacing=1.22)
# the stop bar — DOMINANT: Prime Invariant visual anchor
vrule(s, x1, spine_y - Inches(1.2), spine_y + Inches(1.8), color=ACC, w=3)
T(s, Box(x1 + Inches(0.16), spine_y + Inches(1.12), Inches(2.0), Inches(0.7)),
  "pipeline\nhalts here", size=14, color=ACC, font=F_MN, spacing=1.5)
T(s, gbox(3, 7, Inches(5.5), Inches(0.36)),
  "Every stage is a real LangGraph node.", size=11.5, color=GREY, font=F_RG)
blk = gbox(3, 10, Inches(6.0), Inches(0.5))
block(s, blk, INK)
T(s, Box(blk.x + Inches(0.24), blk.y, blk.w - Inches(0.4), blk.h),
  "Deterministic code decides.   AI explains.   A human approves.   "
  "Every number traces back to a page in a document.",
  size=11.5, color=PAPER, font=F_RG, anchor=MSO_ANCHOR.MIDDLE)
folio(s, 4)
carry_notes(s, 4)

# =====================================================================
# 05 ARCHITECTURE — 4 bands + vertical port boundary
# =====================================================================
s = slide()
head(s, "System architecture", "Pure core. Pluggable edges.", panel="D")
layers = [("User", "React 18 + Vite reviewer SPA / pdf.js evidence viewer"),
          ("Application", "FastAPI / LangGraph orchestration / async worker"),
          ("Intelligence", "OCR routing / classifier / rules engine / hybrid RAG"),
          ("Data & infra", "PostgreSQL / Redis / storage + queue ports")]
ly = Inches(2.78)
lh = Inches(0.86)
for i, (name, items) in enumerate(layers):
    y = ly + i * (lh + Inches(0.12))
    lx, lw = col(3, 2)
    bx, bw = col(5, 8)
    hrule(s, lx, y, SW - M, color=HAIR, w=0.75)
    T(s, Box(lx, y + Inches(0.22), lw, Inches(0.36)), name, size=14, color=INK, font=F_SB)
    T(s, Box(bx, y + Inches(0.24), bw, Inches(0.4)), items, size=12, color=GREY, font=F_RG)
hrule(s, col(3, 1)[0], ly + 4 * (lh + Inches(0.12)), SW - M, color=HAIR, w=0.75)
# port boundary
pb = col(5, 1)[0] - E(GUT / 2)
vrule(s, pb, ly - Inches(0.1), ly + 4 * (lh + Inches(0.12)) + Inches(0.1), color=ACC, w=2)
T(s, Box(pb + Inches(0.08), ly - Inches(0.44), Inches(4), Inches(0.28)),
  "typed port boundary", size=10, color=ACC, font=F_MN)
T(s, gbox(3, 10, Inches(6.28), Inches(0.36)),
  "core/ never imports boto3 or any provider SDK.", size=11.5, color=GREY, font=F_RG)
folio(s, 5)
carry_notes(s, 5)

# =====================================================================
# 06 PERCEPTION — routing figure
# =====================================================================
s = slide()
head(s, "Document perception", "Read the page before classifying it.", panel="E",
     sub="A scanned image has no text layer, so OCR routing has to happen first.")
y = Inches(2.9)
steps = [("01", "PDF page", ""), ("02", "Native text layer", "PyMuPDF"),
         ("03", "OCR fallback", "PaddleOCR CPU"), ("04", "Page text", ""),
         ("05", "Classifier", "TF-IDF + LogReg")]
for i, (n, t, sub) in enumerate(steps):
    b = gbox(3 + i * 2, 2, y, Inches(1.2))
    vrule(s, b.x, y, y + Inches(1.2), color=HAIR, w=1)
    T(s, Box(b.x + Inches(0.14), y, b.w - Inches(0.16), Inches(0.26)), n, size=10, color=GREY_L, font=F_RG)
    T(s, Box(b.x + Inches(0.14), y + Inches(0.32), b.w - Inches(0.16), Inches(0.5)),
      t, size=13, color=INK, font=F_SL, spacing=1.15)
    if sub:
        T(s, Box(b.x + Inches(0.14), y + Inches(0.92), b.w - Inches(0.16), Inches(0.26)),
          sub, size=9.5, color=GREY, font=F_MN)
T(s, Box(gbox(5, 4, y - Inches(0.34), Inches(0.26)).x, y - Inches(0.34), E(COLW * 4), Inches(0.26)),
  "whichever the page needs", size=9.5, color=GREY, font=F_RG)
hrule(s, col(3, 1)[0], Inches(4.4), SW - M, color=HAIR, w=0.75)
cls = ["application_form", "payslip", "bank_statement", "tax_acknowledgement", "id_card"]
T(s, gbox(3, 3, Inches(4.58), Inches(0.26)), "Five canonical classes", size=10, color=GREY, font=F_SB, caps=True)
T(s, gbox(3, 10, Inches(4.92), Inches(0.4)), "   ".join(cls), size=12, color=INK, font=F_MN)
ub = gbox(3, 10, Inches(5.62), Inches(0.62))
vrule(s, ub.x, ub.y, ub.bottom, color=ACC, w=2.5)
T(s, Box(ub.x + Inches(0.22), ub.y, ub.w, ub.h),
  "Low confidence or empty text   \u2192   UNKNOWN, never a guess",
  size=16, color=ACC, font=F_SL, anchor=MSO_ANCHOR.MIDDLE)
folio(s, 6)
carry_notes(s, 6)

# =====================================================================
# 07 MODEL SELECTION — big numerals, Swiss style
# =====================================================================
s = slide()
head(s, "Model selection", "We shipped the simpler model\nand measured why.", panel="F")
mets = [("0.9823", "Macro-F1", "held-out, unseen\ntemplate families"),
         ("5.97", "ms per page", "p50 CPU latency"),
         ("155", "MB process RSS", "fits beside DB,\nworker and RAG"),
         ("<5", "kWh/week", "energy under the\n$25 ceiling")]
for i, (big, lab, sub) in enumerate(mets):
    b = gbox(3 + i * 2, 2, Inches(2.78), Inches(1.9))
    hrule(s, b.x, b.y, b.right - E(GUT / 2), color=RULE, w=1.25)
    T(s, Box(b.x, b.y + Inches(0.18), b.w, Inches(0.72)), big, size=44, color=INK, font=F_LT)
    T(s, Box(b.x, b.y + Inches(1.02), b.w, Inches(0.3)), lab, size=12, color=INK, font=F_SB)
    T(s, Box(b.x, b.y + Inches(1.34), b.w, Inches(0.5)), sub, size=10, color=GREY, font=F_RG, spacing=1.25)
cb = gbox(9, 4, Inches(2.78), Inches(1.9))
vrule(s, cb.x - E(GUT / 2), cb.y, cb.bottom, color=HAIR, w=1)
T(s, Box(cb.x + Inches(0.1), cb.y, cb.w, Inches(0.26)), "Challenger, measured not assumed",
  size=9, color=ACC, font=F_SB, caps=True)
T(s, Box(cb.x + Inches(0.1), cb.y + Inches(0.42), cb.w, Inches(1.4)),
  "DistilBERT scored 0.8619 Macro-F1 in the same\nharness, at 2.5\u00d7 the latency and 4.5\u00d7 the\nmemory.\n\n"
  "We trained it, evaluated it, and did not ship it.",
  size=11.5, color=GREY, font=F_RG, spacing=1.3)
hrule(s, col(3, 1)[0], Inches(5.2), SW - M, color=RULE, w=1)
T(s, gbox(3, 10, Inches(5.4), Inches(0.8)),
  "The rule was written before the result: ship whichever classifier wins on quality AND resource\n"
  "footprint. On a 2-vCPU ARM instance shared with PostgreSQL, the worker and the RAG index,\n"
  "the baseline won both.",
  size=13, color=INK, font=F_LT, spacing=1.35)
folio(s, 7)
carry_notes(s, 7)

# =====================================================================
# 08 EVIDENCE — scientific figure: source -> fact -> ref, annotated
# =====================================================================
s = slide()
head(s, "Evidence-backed extraction", "No fact without evidence.", panel="G")
img = fit(3.390, Box(col(3, 6)[0], Inches(2.8), col(3, 6)[1], Inches(1.9)))
frame(s, Box(img.x - Inches(0.03), img.y - Inches(0.03), img.w + Inches(0.06), img.h + Inches(0.06)), HAIR)
pic(s, os.path.join(C, "pdf_table.png"), img)
T(s, Box(img.x, img.y - Inches(0.3), img.w, Inches(0.24)),
  "i   source page \u2014 application form, page 1", size=9.5, color=GREY, font=F_MN)
hl = Box(img.x + Inches(0.03), img.y + E(img.h * 0.638), img.w - Inches(0.1), E(img.h * 0.115))
frame(s, hl, ACC, 1.75)

fx, fw = col(9, 2)
T(s, Box(fx, Inches(2.5), fw, Inches(0.24)), "ii   extracted fact", size=9.5, color=GREY, font=F_MN)
T(s, Box(fx, Inches(2.86), fw, Inches(0.3)), "Net salary", size=12, color=GREY, font=F_RG)
T(s, Box(fx, Inches(3.16), fw, Inches(0.6)), "\u20b9132,000", size=30, color=INK, font=F_LT)
T(s, Box(fx, Inches(3.86), fw, Inches(0.26)), "MoneyFact", size=9.5, color=GREY, font=F_MN)
T(s, Box(fx, Inches(4.2), fw, Inches(0.3)), "provenance: payslip p3, bbox [0.12, 0.45, 0.88, 0.62]", size=8.5, color=ACC, font=F_MN)

ex, ew = col(11, 2)
vrule(s, ex - E(GUT / 2), Inches(2.5), Inches(4.4), color=ACC, w=2)
T(s, Box(ex, Inches(2.5), ew, Inches(0.24)), "iii   EvidenceRef", size=9.5, color=ACC, font=F_MN)
T(s, Box(ex, Inches(2.9), ew, Inches(1.4)),
  "document_id\npage_number\nbounding_box\nquoted_span", size=11.5, color=INK, font=F_MN, spacing=1.55)

hrule(s, col(3, 1)[0], Inches(5.0), SW - M, color=RULE, w=1)
T(s, gbox(3, 10, Inches(5.22), Inches(0.5)),
  "Evidence missing or unreadable   \u2192   the value is UNKNOWN, never a guess",
  size=19, color=ACC, font=F_LT)
blk = gbox(3, 10, Inches(6.05), Inches(0.5))
block(s, blk, INK)
T(s, Box(blk.x + Inches(0.24), blk.y, blk.w - Inches(0.4), blk.h),
  "Deterministic code decides.   AI explains.   A human approves.   "
  "Every number traces back to a page in a document.",
  size=11.5, color=PAPER, font=F_RG, anchor=MSO_ANCHOR.MIDDLE)
folio(s, 8)
carry_notes(s, 8)

# =====================================================================
# 09 RULES — tabular, accent only on FLAG
# =====================================================================
s = slide()
head(s, "Deterministic rule engine", "Verdicts come from code,\nnot from a model.", panel="H")
rules = [("RULE-COMP-01", "Completeness", "All five documents present"),
          ("RULE-INC-01", "Salary audit", "Payslip net vs bank credits, 5%"),
          ("RULE-TAX-01", "Tax audit", "ITR vs annualised payslip, 10%"),
          ("RULE-ID-01", "Identity", "Fuzzy name + PAN across documents"),
          ("RULE-ID-02", "Identity cross-check", "2+ ID docs: name & PAN must match")]
ry = Inches(2.82)
rh = Inches(0.62)
hrule(s, col(3, 1)[0], ry, col(3, 7)[0] + col(3, 7)[1], color=RULE, w=1.25)
for i, (rid, name, desc) in enumerate(rules):
    y = ry + Inches(0.1) + i * rh
    T(s, Box(col(3, 2)[0], y, col(3, 2)[1], Inches(0.3)), rid, size=10.5, color=ACC, font=F_MN)
    T(s, Box(col(5, 2)[0], y, col(5, 2)[1], Inches(0.3)), name, size=13, color=INK, font=F_SB)
    T(s, Box(col(7, 3)[0], y, col(7, 3)[1], Inches(0.3)), desc, size=11, color=GREY, font=F_RG)
    hrule(s, col(3, 1)[0], y + Inches(0.44), col(3, 7)[0] + col(3, 7)[1], color=HAIR, w=0.75)
vy = ry + Inches(0.1) + 4 * rh + Inches(0.34)
for i, (v, c) in enumerate([("PASS", INK), ("FLAG", ACC), ("UNKNOWN", GREY)]):
    bx = col(3 + i * 2, 2)[0]
    T(s, Box(bx, vy, col(3, 2)[1], Inches(0.4)), v, size=19, color=c, font=F_SL)
    hrule(s, bx, vy + Inches(0.42), bx + E(COLW * 1.6), color=c, w=2)

shot = fit(1.452, Box(col(10, 3)[0], Inches(2.82), col(10, 3)[1], Inches(2.4)))
frame(s, Box(shot.x - Inches(0.03), shot.y - Inches(0.03), shot.w + Inches(0.06), shot.h + Inches(0.06)), HAIR)
pic(s, os.path.join(C, "rule_card.png"), shot)
caption(s, Box(shot.x, shot.y + shot.h + Inches(0.16), shot.w, Inches(0.7)),
        "iv   the same rule in the product:\ntyped, cited, deterministic")
folio(s, 9)
carry_notes(s, 9)

# =====================================================================
# 10 RAG + GROUNDING
# =====================================================================
s = slide()
head(s, "Policy retrieval & grounding", "Every claim must cite\nauthorised evidence.", panel="J")
sy = Inches(2.86)
steps = ["Policy\ncorpus", "BM25\nlexical", "BGE dense\nretrieval", "RRF\nfusion", "LLM\nsynthesis", "Grounding\nvalidator"]
for i, t in enumerate(steps):
    last = (i == 5)
    bx = col(1 + i * 2, 2)[0]
    bw = col(1, 2)[1]
    c = ACC if last else INK
    vrule(s, bx, sy, sy + Inches(1.1), color=c, w=2.25 if last else 1)
    T(s, Box(bx + Inches(0.14), sy, bw, Inches(0.26)), f"{i+1:02d}", size=10, color=GREY_L, font=F_RG)
    T(s, Box(bx + Inches(0.14), sy + Inches(0.34), bw - Inches(0.1), Inches(0.7)),
      t, size=12.5, color=c, font=F_SL, spacing=1.18)
gy = Inches(4.34)
hrule(s, col(3, 1)[0], gy, SW - M, color=ACC, w=1.5)
T(s, gbox(3, 10, gy + Inches(0.18), Inches(0.44)),
  "A claim with no authorised citation is stripped \u2014 the memo abstains rather than asserts.",
  size=16, color=ACC, font=F_LT)
ny = Inches(5.32)
for i, (big, lab) in enumerate([("1.00", "Recall@5"), ("1.00", "Grounding precision"), ("30", "Frozen benchmark questions")]):
    bx = col(3 + i * 3, 3)[0]
    bw = col(3, 3)[1]
    hrule(s, bx, ny, bx + bw - E(GUT / 2), color=RULE, w=1.25)
    T(s, Box(bx, ny + Inches(0.16), bw, Inches(0.56)), big, size=34, color=INK, font=F_LT)
    T(s, Box(bx, ny + Inches(0.82), bw, Inches(0.3)), lab, size=11, color=GREY, font=F_RG)
T(s, gbox(3, 10, Inches(5.2), Inches(0.3)),
  "18 dev + 12 held-out questions, frozen weights.", size=10.5, color=GREY, font=F_MN)
folio(s, 10)
carry_notes(s, 11)

# =====================================================================
# 12 HITL — state ruler with a hard stop
# =====================================================================
s = slide()
head(s, "Human-in-the-loop", "The system prepares.\nThe human decides.", panel="K")
sy = Inches(3.1)
states = ["UPLOADED", "QUEUED", "PROCESSING", "READY_FOR_REVIEW"]
x0 = col(3, 1)[0]
x1 = SW - M - Inches(2.35)          # room for the wall + its label
hrule(s, x0, sy, x1, color=RULE, w=1.5)
stp = (x1 - x0) / 3
for i, st in enumerate(states):
    cxp = x0 + i * stp
    last = (i == 3)
    c = ACC if last else INK
    vrule(s, cxp, sy - Inches(0.14), sy + Inches(0.14), color=c, w=2.5 if last else 1.5)
    if last:
        T(s, Box(cxp - Inches(2.3), sy + Inches(0.3), Inches(2.18), Inches(0.3)), st,
          size=10.5, color=c, font=F_MN, align=PP_ALIGN.RIGHT)
    else:
        T(s, Box(cxp, sy + Inches(0.3), Inches(2.2), Inches(0.3)), st, size=10.5, color=c, font=F_MN)

# the wall
vrule(s, x1, sy - Inches(0.62), sy + Inches(1.5), color=ACC, w=3)
T(s, Box(x1 + Inches(0.18), sy - Inches(0.58), Inches(2.2), Inches(0.36)),
  "interrupt()", size=18, color=ACC, font=F_MN)
T(s, Box(x1 + Inches(0.18), sy - Inches(0.14), Inches(2.2), Inches(0.7)),
  "the graph cannot\ncontinue on its own", size=10.5, color=ACC, font=F_RG, spacing=1.3)

lb = gbox(3, 5, Inches(4.72), Inches(1.6))
T(s, Box(lb.x, lb.y, lb.w, Inches(0.8)),
  "The graph is compiled with\ninterrupt_before.", size=17, color=INK, font=F_LT, spacing=1.25)
T(s, Box(lb.x, lb.y + Inches(0.92), lb.w, Inches(0.7)),
  "Resuming needs a written rationale and the dossier ID\ntyped back \u2014 and writes an immutable audit event.",
  size=11.5, color=GREY, font=F_RG, spacing=1.3)
shot = fit(5.780, Box(col(9, 4)[0], Inches(4.84), col(9, 4)[1], Inches(1.0)))
frame(s, Box(shot.x - Inches(0.03), shot.y - Inches(0.03), shot.w + Inches(0.06), shot.h + Inches(0.06)), HAIR)
pic(s, os.path.join(C, "signoff.png"), shot)
caption(s, Box(shot.x, shot.y + shot.h + Inches(0.14), shot.w, Inches(0.3)),
        "v   the real sign-off control", size=9.5)
folio(s, 11)
carry_notes(s, 12)

# =====================================================================
# 13 CLOUD
# =====================================================================
s = slide()
head(s, "Cloud architecture", "Ports and adapters, made real.", panel="L",
     sub="Only the AWS services we actually implemented are shown.")
cy = Inches(2.98)
chain = [("React UI", "served same-origin"), ("FastAPI", "EC2 t4g.medium + Caddy"),
         ("Postgres / Redis / Worker", "containers on one host"),
         ("SQS + DLQ", "3 attempts, then DLQ"), ("S3", "SSE-AES256, presigned")]
for i, (t, sub) in enumerate(chain):
    bx = col(3 + i * 2, 2)[0]
    bw = col(3, 2)[1]
    acc = i >= 3
    c = ACC if acc else INK
    vrule(s, bx, cy, cy + Inches(1.15), color=c, w=2 if acc else 1)
    T(s, Box(bx + Inches(0.14), cy, bw, Inches(0.26)), f"{i+1:02d}", size=10, color=GREY_L, font=F_RG)
    T(s, Box(bx + Inches(0.14), cy + Inches(0.32), bw - Inches(0.05), Inches(0.5)),
      t, size=12.5, color=c, font=F_SL, spacing=1.15)
    T(s, Box(bx + Inches(0.14), cy + Inches(0.88), bw - Inches(0.05), Inches(0.3)),
      sub, size=9.5, color=GREY, font=F_MN)
hrule(s, col(3, 1)[0], Inches(4.5), SW - M, color=HAIR, w=0.75)
ay = Inches(4.76)
for i, (t, d) in enumerate([("Local adapters", "filesystem   /   Postgres SKIP LOCKED"),
                            ("Cloud adapters", "AWS S3   /   SQS + DLQ")]):
    bx = col(3 + i * 5, 5)[0]
    bw = col(3, 5)[1]
    T(s, Box(bx, ay, bw, Inches(0.3)), t, size=13, color=INK, font=F_SB)
    T(s, Box(bx, ay + Inches(0.34), bw, Inches(0.3)), d, size=11, color=GREY, font=F_MN)
T(s, gbox(3, 10, Inches(5.7), Inches(0.3)), "Same core code either way.", size=11.5, color=GREY, font=F_RG)
T(s, gbox(3, 10, Inches(6.08), Inches(0.3)),
  "One instance, containers instead of managed services \u2014 a deliberate choice under a $25 weekly ceiling.",
  size=11.5, color=GREY, font=F_RG)
folio(s, 12)
carry_notes(s, 13)

# =====================================================================
# 14 REVIEWER WORKSPACE (merged entry + three-pane)
# =====================================================================
s = slide()
head(s, "The reviewer workspace", "Authenticated desk.\nThree panes, one decision.", panel="M",
     sub="Screenshots from the running application.")
li = fit(0.938, Box(col(3, 3)[0], Inches(2.82), col(3, 3)[1], Inches(3.1)))
frame(s, Box(li.x - Inches(0.03), li.y - Inches(0.03), li.w + Inches(0.06), li.h + Inches(0.06)), HAIR)
pic(s, os.path.join(C, "login_card.png"), li)
caption(s, Box(li.x, li.y + li.h + Inches(0.18), li.w, Inches(0.8)),
        "vi   allowlisted sign-in. every sign-off is\nattributed to a named underwriter")
d2 = fit(1.393, Box(col(7, 6)[0], Inches(2.82), col(7, 6)[1], Inches(3.1)))
frame(s, Box(d2.x - Inches(0.03), d2.y - Inches(0.03), d2.w + Inches(0.06), d2.h + Inches(0.06)), HAIR)
pic(s, os.path.join(C, "desk.png"), d2)
caption(s, Box(d2.x, d2.y + d2.h + Inches(0.18), d2.w, Inches(0.8)),
        "vii   dossier desk — live backend apps,\neach showing lifecycle state")

hero = fit(1.830, Box(col(3, 10)[0], Inches(2.0), col(3, 10)[1], Inches(3.9)))
frame(s, Box(hero.x - Inches(0.03), hero.y - Inches(0.03), hero.w + Inches(0.06), hero.h + Inches(0.06)), HAIR)
pic(s, os.path.join(A, "03_reviewer_three_pane.png"), hero)
panes = [(0.094, "Dossier index", "every document, page count\nand how its text was read"),
         (0.464, "Evidence viewer", "the original PDF, with the\nbounding box behind each fact"),
         (0.870, "Findings & sign-off", "verdicts, policy explanation\nand the review decision")]
cap_y = hero.y + hero.h + Inches(0.2)
for frac, t, d in panes:
    cxp = hero.x + E(hero.w * frac)
    vrule(s, cxp, hero.y + hero.h + Inches(0.02), cap_y - Inches(0.02), color=ACC, w=1.25)
    T(s, Box(cxp + Inches(0.08), cap_y, Inches(3.0), Inches(0.28)), t, size=12.5, color=INK, font=F_SB)
    T(s, Box(cxp + Inches(0.08), cap_y + Inches(0.3), Inches(3.0), Inches(0.6)), d,
      size=10, color=GREY, font=F_RG, spacing=1.25)
T(s, gbox(3, 10, Inches(6.08), Inches(0.3)),
  "v   the real sign-off control", size=10, color=GREY, font=F_MN)
folio(s, 13)
carry_notes(s, 14)

# =====================================================================
# 15 LIVE DEMO
# =====================================================================
s = slide()
head(s, "Live demo", "What you are about to see.", panel="O")
items = ["Upload the dossier", "Worker picks up the job", "Pages classified",
         "Facts extracted with evidence", "Rules produce verdicts",
         "Grounded memo assembled", "Underwriter signs off"]
for i, t in enumerate(items):
    c_i = 3 if i < 4 else 8
    r_i = i if i < 4 else i - 4
    bx, bw = col(c_i, 5)
    y = Inches(2.86) + r_i * Inches(0.64)
    T(s, Box(bx, y, Inches(0.5), Inches(0.36)), f"{i+1:02d}", size=15, color=ACC, font=F_LT)
    T(s, Box(bx + Inches(0.6), y + Inches(0.02), bw - Inches(0.6), Inches(0.36)),
      t, size=15, color=INK, font=F_SL)
    hrule(s, bx, y + Inches(0.46), bx + bw - E(GUT / 2), color=HAIR, w=0.75)
wb = gbox(8, 5, Inches(5.5), Inches(0.9))
vrule(s, wb.x, wb.y, wb.bottom, color=ACC, w=2)
T(s, Box(wb.x + Inches(0.2), wb.y, wb.w - Inches(0.2), Inches(0.8)),
  "Watch for the two flags: a salary that does not\nreach the bank account, and a name that changes.",
  size=12.5, color=INK, font=F_RG, spacing=1.35)
# QR action item
qrb = gbox(3, 10, Inches(4.5), Inches(1.0))
block(s, qrb, INK)
T(s, Box(qrb.x + Inches(0.2), qrb.y, qrb.w - Inches(0.4), Inches(0.9)),
  "Scan to try it now.\nEvidence first.\nDecisions second.",
  size=14, color=PAPER, font=F_LT, anchor=MSO_ANCHOR.MIDDLE, spacing=1.3)
T(s, gbox(8, 10, Inches(4.0), Inches(0.3)),
  "qr code -> live demo", size=10, color=GREY, font=F_MN)
folio(s, 14)
carry_notes(s, 15)

# =====================================================================
# 16 HUMAN-IN-THE-LOOP
# =====================================================================
s = slide()
head(s, "Human-in-the-loop", "The system prepares.\nThe human decides.", panel="K")
sy = Inches(3.1)
states = ["UPLOADED", "QUEUED", "PROCESSING", "READY_FOR_REVIEW"]
x0 = col(3, 1)[0]
x1 = SW - M - Inches(2.35)
hrule(s, x0, sy, x1, color=RULE, w=1.5)
stp = (x1 - x0) / 3
for i, st in enumerate(states):
    cxp = x0 + i * stp
    last = (i == 3)
    c = ACC if last else INK
    vrule(s, cxp, sy - Inches(0.14), sy + Inches(0.14), color=c, w=2.5 if last else 1.5)
    if last:
        T(s, Box(cxp - Inches(2.3), sy + Inches(0.3), Inches(2.18), Inches(0.3)), st,
          size=10.5, color=c, font=F_MN, align=PP_ALIGN.RIGHT)
    else:
        T(s, Box(cxp, sy + Inches(0.3), Inches(2.2), Inches(0.3)), st, size=10.5, color=c, font=F_MN)

vrule(s, x1, sy - Inches(0.62), sy + Inches(1.5), color=ACC, w=3)
T(s, Box(x1 + Inches(0.18), sy - Inches(0.58), Inches(2.2), Inches(0.36)),
  "interrupt()", size=18, color=ACC, font=F_MN)
T(s, Box(x1 + Inches(0.18), sy - Inches(0.14), Inches(2.2), Inches(0.7)),
  "the graph cannot\ncontinue on its own", size=10.5, color=ACC, font=F_RG, spacing=1.3)

lb = gbox(3, 5, Inches(4.72), Inches(1.6))
T(s, Box(lb.x, lb.y, lb.w, Inches(0.8)),
  "The graph is compiled with\ninterrupt_before.", size=17, color=INK, font=F_LT, spacing=1.25)
T(s, Box(lb.x, lb.y + Inches(0.92), lb.w, Inches(0.7)),
  "Resuming needs a written rationale and the dossier ID\ntyped back \u2014 and writes an immutable audit event.",
  size=11.5, color=GREY, font=F_RG, spacing=1.3)
shot = fit(5.780, Box(col(9, 4)[0], Inches(4.84), col(9, 4)[1], Inches(1.0)))
frame(s, Box(shot.x - Inches(0.03), shot.y - Inches(0.03), shot.w + Inches(0.06), shot.h + Inches(0.06)), HAIR)
pic(s, os.path.join(C, "signoff.png"), shot)
caption(s, Box(shot.x, shot.y + shot.h + Inches(0.14), shot.w, Inches(0.3)),
        "v   the real sign-off control", size=9.5)
folio(s, 15)
carry_notes(s, 16)

# =====================================================================
# 17 RESULTS
# =====================================================================
s = slide()
head(s, "What we measured", "Verified numbers, not projections.", panel="P")
res = [("0.9823", "Macro-F1", "held-out document classification"),
       ("5.97", "ms per page", "classifier p50 on CPU"),
       ("1.00", "Recall@5", "frozen 30-question benchmark"),
       ("1.00", "Grounding precision", "claims traced to an authorised citation")]
for i, (big, lab, sub) in enumerate(res):
    bx, bw = col(3 + i * 2 + (1 if i >= 2 else 0), 2)
    y = Inches(2.82)
    hrule(s, bx, y, bx + bw - E(GUT / 2), color=RULE, w=1.25)
    T(s, Box(bx, y + Inches(0.18), bw, Inches(0.7)), big, size=40, color=INK, font=F_LT)
    T(s, Box(bx, y + Inches(0.96), bw, Inches(0.3)), lab, size=11.5, color=INK, font=F_SB)
    T(s, Box(bx, y + Inches(1.28), bw, Inches(0.6)), sub, size=10, color=GREY, font=F_RG, spacing=1.25)
vs = fit(2.215, Box(col(3, 4)[0], Inches(4.86), col(3, 4)[1], Inches(1.4)))
frame(s, Box(vs.x - Inches(0.03), vs.y - Inches(0.03), vs.w + Inches(0.06), vs.h + Inches(0.06)), HAIR)
pic(s, os.path.join(C, "verdict_strip.png"), vs)
tb = gbox(8, 5, Inches(4.86), Inches(1.4))
vrule(s, tb.x, tb.y, tb.bottom, color=ACC, w=2)
T(s, Box(tb.x + Inches(0.22), tb.y, tb.w - Inches(0.2), Inches(1.3)),
  "On the demo dossier the engine caught a 65.9% gap\nbetween the stated salary and the bank credits, and a\n"
  "name that did not match across documents \u2014 and refused\nto guess on a fifth check it could not verify.",
  size=12, color=INK, font=F_RG, spacing=1.38)
folio(s, 16)
carry_notes(s, 17)

# =====================================================================
# 18 CLOSE
# =====================================================================
s = slide(INK)
x, w = col(1, 2)
T(s, Box(x, EYE_Y, w, Inches(0.24)), "Engineering decisions", size=9, color=ACC, font=F_SB, caps=True)
tx, tw = col(3, 10)
T(s, Box(tx, Inches(1.0), tw, Inches(0.6)), "Why it is built this way.", size=30, color=PAPER, font=F_LT)
hrule(s, M, Inches(1.86), SW - M, color=RGBColor(0x3A, 0x38, 0x34), w=1)
dec = [("Rules, not LLM arithmetic", "Totals must be reproducible and provable."),
       ("A linear classifier", "It won on quality and on footprint. We measured both."),
       ("LangGraph with a hard interrupt", "Resumable state, and a pause nobody can forget."),
       ("Evidence on every fact", "Provenance is the trust contract, not a feature.")]
for i, (t, d) in enumerate(dec):
    ci = 3 if i % 2 == 0 else 8
    ri = i // 2
    bx, bw = col(ci, 5)
    y = Inches(2.24) + ri * Inches(1.08)
    T(s, Box(bx, y, bw, Inches(0.3)), t, size=13.5, color=PAPER, font=F_SB)
    T(s, Box(bx, y + Inches(0.36), bw, Inches(0.4)), d, size=11.5, color=GREY, font=F_RG)
    hrule(s, bx, y + Inches(0.84), bx + bw - E(GUT / 2), color=RGBColor(0x3A, 0x38, 0x34), w=0.75)
T(s, gbox(3, 10, Inches(4.9), Inches(0.9)),
  "Evidence first.\nDecisions second. Humans always in control.",
  size=34, color=PAPER, font=F_LT, spacing=1.2)
# QR code + action + team
qrb = gbox(8, 5, Inches(4.5), Inches(1.0))
block(s, qrb, INK)
T(s, Box(qrb.x + Inches(0.2), qrb.y, qrb.w - Inches(0.4), Inches(0.9)),
  "Scan to try it now.\nEvidence first.\nDecisions second.",
  size=14, color=PAPER, font=F_LT, anchor=MSO_ANCHOR.MIDDLE, spacing=1.3)
T(s, gbox(3, 10, Inches(6.42), Inches(0.3)),
  "Bhanu Teja   Manjunath   Jeevan   Sravanthi   Karthik   Balaji   Akshaya   Sai Mokshith",
  size=11, color=GREY, font=F_RG)
T(s, Box(x, FOLIO_Y, w, Inches(0.4)), "17", size=26, color=RGBColor(0x45, 0x43, 0x3E), font=F_LT)
carry_notes(s, 17)

OUT = os.path.join(OUT_DIR, "FinScan_Redesign_Swiss.pptx")
prs.save(OUT)
print("saved", OUT)
