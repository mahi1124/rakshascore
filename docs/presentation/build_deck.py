#!/usr/bin/env python3
"""Build the RakshaScore project presentation (16:9 PowerPoint).

Usage:
    python docs/presentation/build_deck.py
    python docs/presentation/build_deck.py --out path/to/deck.pptx

Screenshots live in docs/presentation/assets/ and are captured from the running
Streamlit app. Edit the text in the slide functions below to tailor the story.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
DEFAULT_OUT = HERE.parents[1] / "RakshaScore_Presentation.pptx"

W, H = 13.333, 7.5
FONT = "Segoe UI"

NAVY = RGBColor(0x0F, 0x2A, 0x47)
NAVY_DEEP = RGBColor(0x0B, 0x1F, 0x3A)
NAVY_SOFT = RGBColor(0x17, 0x33, 0x5C)
BLUE = RGBColor(0x25, 0x63, 0xEB)
BLUE_L = RGBColor(0x3B, 0x82, 0xF6)
INK = RGBColor(0x1B, 0x2B, 0x3C)
SLATE = RGBColor(0x47, 0x54, 0x67)
MUTED = RGBColor(0x98, 0xA2, 0xB3)
BORDER = RGBColor(0xE3, 0xE8, 0xEF)
BG = RGBColor(0xF7, 0xF8, 0xFC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x15, 0x80, 0x3D)
GREEN_BG = RGBColor(0xEC, 0xFD, 0xF3)
AMBER = RGBColor(0xB5, 0x47, 0x08)
AMBER_BG = RGBColor(0xFF, 0xFA, 0xEB)
RED = RGBColor(0xDC, 0x26, 0x26)
RED_BG = RGBColor(0xFE, 0xF3, 0xF2)
BLUE_BG = RGBColor(0xEE, 0xF4, 0xFF)
PALE = RGBColor(0xF9, 0xFA, 0xFB)


# ---------------------------------------------------------------- primitives
def rect(slide, x, y, w, h, fill, line=None, radius=None, line_w=1.0):
    """Rectangle or rounded rectangle (inches)."""
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shp.adjustments[0] = radius
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(line_w)
    shp.shadow.inherit = False
    return shp


def oval(slide, x, y, w, h, fill, line=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1)
    shp.shadow.inherit = False
    return shp


def tb(slide, x, y, w, h, text="", size=12, color=INK, bold=False, italic=False,
       align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.0, font=FONT, spc=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = spacing
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font
    run.font.color.rgb = color
    if spc is not None:
        run.font._rPr.set("spc", str(int(spc * 100)))
    return box


def rich(slide, x, y, w, h, parts, size=12, align=PP_ALIGN.LEFT, spacing=1.0,
         anchor=MSO_ANCHOR.TOP):
    """One paragraph built from (text, color, bold) tuples."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = spacing
    for text, color, bold in parts:
        run = p.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.name = FONT
        run.font.color.rgb = color
    return box


def bullets(slide, x, y, w, h, items, size=11.5, color=SLATE, gap=7,
            bullet_color=BLUE, spacing=1.12):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.line_spacing = spacing
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(int(Inches(0.21))))
        pPr.set("indent", str(int(-Inches(0.21))))
        dot = p.add_run()
        dot.text = "•  "
        dot.font.size = Pt(size)
        dot.font.bold = True
        dot.font.name = FONT
        dot.font.color.rgb = bullet_color
        if isinstance(item, tuple):
            lead, rest = item
            r1 = p.add_run()
            r1.text = lead
            r1.font.size = Pt(size)
            r1.font.bold = True
            r1.font.name = FONT
            r1.font.color.rgb = INK
            r2 = p.add_run()
            r2.text = rest
            r2.font.size = Pt(size)
            r2.font.name = FONT
            r2.font.color.rgb = color
        else:
            run = p.add_run()
            run.text = item
            run.font.size = Pt(size)
            run.font.name = FONT
            run.font.color.rgb = color
    return box


def logo(slide, x, y, size, fill=BLUE_L):
    """Shield mark + check, drawn as a freeform so it scales cleanly."""
    pts = [(12, 2), (4, 5), (4, 11), (12, 22), (20, 11), (20, 5)]
    u = size / 24.0
    first = (x + pts[0][0] * u, y + pts[0][1] * u)
    builder = slide.shapes.build_freeform(
        Emu(int(first[0] * 914400)), Emu(int(first[1] * 914400)), scale=1)
    builder.add_line_segments(
        [(Emu(int((x + px * u) * 914400)), Emu(int((y + py * u) * 914400)))
         for px, py in pts[1:]], close=True)
    shp = builder.convert_to_shape()
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    shp.shadow.inherit = False
    tb(slide, x + size * 0.18, y + size * 0.28, size * 0.64, size * 0.48,
       "✓", size=size * 32, color=WHITE, bold=True, align=PP_ALIGN.CENTER,
       anchor=MSO_ANCHOR.MIDDLE)


def eyebrow(slide, text, y=0.48):
    rect(slide, 0.45, y + 0.02, 0.055, 0.2, BLUE)
    tb(slide, 0.62, y - 0.02, 8.0, 0.28, text.upper(), size=9.5, color=BLUE,
       bold=True, spc=1.3)


def heading(slide, title, sub=None, title_size=30):
    tb(slide, 0.45, 0.72, 12.4, 0.75, title, size=title_size, color=NAVY,
       bold=True, spacing=0.95)
    if sub:
        tb(slide, 0.45, 1.4, 11.6, 0.5, sub, size=12.5, color=SLATE, spacing=1.15)


def footer(slide, num):
    rect(slide, 0.45, 7.02, 12.43, 0.008, BORDER)
    tb(slide, 0.45, 7.1, 8.0, 0.25, "RAKSHASCORE  ·  CYBER RISK ASSESSMENT PLATFORM",
       size=8, color=MUTED, bold=False, spc=0.8)
    tb(slide, 11.9, 7.1, 0.98, 0.25, f"{num:02d}", size=9, color=SLATE,
       bold=True, align=PP_ALIGN.RIGHT)


def card(slide, x, y, w, h, fill=WHITE, line=BORDER, radius=0.07):
    return rect(slide, x, y, w, h, fill, line, radius=radius)


def stat_card(slide, x, y, w, h, value, label, note="", accent=BLUE,
              value_size=30, fill=WHITE):
    card(slide, x, y, w, h, fill=fill)
    rect(slide, x, y, 0.055, h, accent)
    tb(slide, x + 0.25, y + 0.19, w - 0.4, 0.22, label.upper(), size=8.5,
       color=SLATE, bold=True, spc=0.9)
    tb(slide, x + 0.25, y + 0.42, w - 0.4, 0.62, value, size=value_size,
       color=NAVY, bold=True, spacing=0.9)
    if note:
        tb(slide, x + 0.25, y + h - 0.47, w - 0.45, 0.38, note, size=9,
           color=SLATE, spacing=1.05)


def chip(slide, x, y, w, text, fill=BLUE_BG, color=BLUE, size=8.5, h=0.26,
         bold=True):
    rect(slide, x, y, w, h, fill, None, radius=0.5)
    tb(slide, x, y, w, h, text, size=size, color=color, bold=bold,
       align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, spc=0.4)


def picture(slide, path, x, y, w, border=True):
    h = w * 844 / 1040
    if border:
        card(slide, x - 0.035, y - 0.035, w + 0.07, h + 0.07, WHITE, BORDER,
             radius=0.03)
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    return h


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def new_slide(prs, bg=BG):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    rect(slide, 0, 0, W, H, bg)
    return slide


# ---------------------------------------------------------------- slides
def title_slide(prs):
    s = new_slide(prs, NAVY)
    oval(s, 10.2, -2.2, 6.2, 6.2, NAVY_SOFT)
    oval(s, 11.9, 3.4, 4.4, 4.4, RGBColor(0x12, 0x2C, 0x4E))
    oval(s, -1.8, 5.4, 3.6, 3.6, RGBColor(0x12, 0x2C, 0x4E))

    logo(s, 0.85, 1.35, 0.92)
    tb(s, 1.95, 1.42, 8.0, 0.34, "RAKSHASCORE", size=15, color=WHITE, bold=True, spc=2.4)
    tb(s, 1.95, 1.76, 8.0, 0.3, "CYBER RISK ASSESSMENT PLATFORM", size=8.5,
       color=RGBColor(0x8F, 0xA5, 0xC2), bold=True, spc=1.8)

    tb(s, 0.85, 2.55, 10.8, 0.35, "SEMESTER 5  ·  MACHINE LEARNING PROJECT",
       size=10, color=BLUE_L, bold=True, spc=2.0)
    tb(s, 0.85, 2.95, 11.2, 1.7, "See your cyber risk.\nFix what matters first.",
       size=46, color=WHITE, bold=True, spacing=1.0)
    tb(s, 0.85, 4.75, 8.6, 0.95,
       "An AI-assisted platform that scores a small business's security posture, "
       "explains every point and turns the gaps into a costed 90-day plan.",
       size=14, color=RGBColor(0xC9, 0xD4, 0xE5), spacing=1.2)

    for i, (label, w) in enumerate([("RANDOM FOREST + SHAP", 2.35),
                                    ("STREAMLIT", 1.45),
                                    ("OFFLINE-FIRST", 1.6)]):
        x = 0.85 + sum([2.35, 1.45, 1.6][:i]) + i * 0.18
        chip(s, x, 5.95, w, label, fill=NAVY_SOFT, color=RGBColor(0xC9, 0xD4, 0xE5),
             size=7.5, h=0.3)

    rect(s, 0.85, 6.62, 11.6, 0.01, RGBColor(0x2A, 0x45, 0x70))
    tb(s, 0.85, 6.76, 7.5, 0.28, "github.com/mahi1124/rakshascore", size=10,
       color=RGBColor(0xC9, 0xD4, 0xE5))
    tb(s, 9.5, 6.76, 2.95, 0.28, "NOVEMBER 2026", size=9, color=RGBColor(0x8F, 0xA5, 0xC2),
       bold=True, align=PP_ALIGN.RIGHT, spc=1.2)
    notes(s, "Open with the one-line pitch: RakshaScore turns a security questionnaire "
             "into a score a manager can act on. The project is a full application, not "
             "just a notebook: trained models, explainability, a remediation engine and "
             "a downloadable report.")


def agenda_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "Agenda")
    heading(s, "From questionnaire to action plan",
            "Six short sections: the problem, the product, the model and the engineering.")
    items = [
        ("01", "The problem", "Why small businesses get advice they cannot act on."),
        ("02", "The product", "One assessment, five management-ready outputs."),
        ("03", "How it works", "Intake, validation, scoring, explanation, planning."),
        ("04", "Model & results", "Four algorithms compared on 10,000 records."),
        ("05", "Explain & remediate", "SHAP points and modelled score reductions."),
        ("06", "Engineering", "Tests, performance, guardrails and what comes next."),
    ]
    x0, y0 = 0.45, 2.0
    for i, (n, title, desc) in enumerate(items):
        col = i % 2
        row = i // 2
        x = x0 + col * 6.35
        y = y0 + row * 1.55
        card(s, x, y, 5.95, 1.28)
        tb(s, x + 0.25, y + 0.2, 0.75, 0.5, n, size=20, color=BLUE, bold=True)
        tb(s, x + 1.05, y + 0.2, 4.7, 0.36, title, size=14.5, color=NAVY, bold=True)
        tb(s, x + 1.05, y + 0.62, 4.65, 0.5, desc, size=10.5, color=SLATE, spacing=1.12)
    footer(s, num)
    notes(s, "Keep the agenda to twenty seconds. Flag that the demo is embedded as "
             "screenshots, and that the code and models are in the public repository.")


def problem_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "01 · The problem")
    heading(s, "Enterprise threats, startup budgets",
            "Security guidance exists. What is missing is prioritisation.")
    cards = [
        ("No dedicated team", "The owner or an IT generalist is the security function. "
                              "Nobody has time to interpret a 100-page framework.",
         RED, RED_BG),
        ("Frameworks, not answers", "CIS Controls, ISO 27001 and NIST CSF describe what "
                                    "good looks like, not which gap to fix on Monday.",
         AMBER, AMBER_BG),
        ("Static, unexplained reports", "Checklists produce a grade without a reason, and "
                                        "recommend actions without quantifying the benefit.",
         BLUE, BLUE_BG),
    ]
    for i, (title, body, accent, tint) in enumerate(cards):
        x = 0.45 + i * 4.23
        card(s, x, 2.05, 3.95, 3.0)
        rect(s, x, 2.05, 3.95, 0.09, accent)
        oval(s, x + 0.3, 2.4, 0.58, 0.58, tint)
        tb(s, x + 0.3, 2.4, 0.58, 0.58, str(i + 1), size=16, color=accent, bold=True,
           align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        tb(s, x + 0.3, 3.2, 3.4, 0.4, title, size=15, color=NAVY, bold=True)
        tb(s, x + 0.3, 3.68, 3.35, 1.2, body, size=11, color=SLATE, spacing=1.18)

    card(s, 0.45, 5.42, 12.43, 1.05, NAVY, None)
    tb(s, 0.75, 5.62, 11.9, 0.28, "THE GAP", size=8.5, color=BLUE_L, bold=True, spc=1.6)
    tb(s, 0.75, 5.88, 11.8, 0.4,
       "A fast, explainable assessment that says what to fix first — and what fixing it is worth.",
       size=14, color=WHITE, bold=True)
    footer(s, num)
    notes(s, "Do not quote statistics that are not in the sources. The argument is "
             "structural: small teams lack time, frameworks lack prioritisation, and "
             "static reports lack explanation. RakshaScore addresses all three.")


def solution_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "02 · The product")
    heading(s, "One assessment. Five decisions.",
            "A 37-question questionnaire becomes a management-ready risk picture.")
    items = [
        ("0–100", "Risk score", "A calibrated score from the trained regressor.", BLUE),
        ("4", "Risk tiers", "Low, Medium, High and Critical, from the classifier.", NAVY_SOFT),
        ("SHAP", "The reason", "Points contributed by every individual answer.", GREEN),
        ("90 days", "The plan", "Actions sequenced by effort and modelled impact.", AMBER),
        ("HTML", "The evidence", "Print-ready report plus CSV register and JSON data.", RED),
    ]
    for i, (value, label, desc, accent) in enumerate(items):
        x = 0.45 + i * 2.52
        card(s, x, 2.05, 2.3, 3.15)
        rect(s, x, 2.05, 2.3, 0.08, accent)
        tb(s, x + 0.22, 2.34, 1.9, 0.55, value, size=24, color=accent, bold=True)
        tb(s, x + 0.22, 2.98, 1.9, 0.32, label, size=13, color=NAVY, bold=True)
        tb(s, x + 0.22, 3.42, 1.92, 1.5, desc, size=10.5, color=SLATE, spacing=1.16)
    card(s, 0.45, 5.5, 12.43, 0.95, BLUE_BG, RGBColor(0xCF, 0xE0, 0xFF))
    tb(s, 0.75, 5.66, 11.9, 0.3, "DESIGNED FOR THE REAL CONSTRAINT", size=8.5,
       color=BLUE, bold=True, spc=1.5)
    tb(s, 0.75, 5.94, 11.8, 0.32,
       "A full run takes seconds and works offline — no API key, no GPU and no consultant required.",
       size=12.5, color=NAVY, bold=True)
    footer(s, num)
    notes(s, "The five outputs are the product. Everything else in the deck explains how "
             "they are produced and why they can be trusted. Stress that the app runs "
             "offline, so a demo never depends on a network key.")


def pipeline_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "03 · How it works")
    heading(s, "From free text to a costed plan",
            "Five deterministic stages; the language model is optional and never sets the score.")
    steps = [
        ("1", "Intake", "Questionnaire, or a free-text description pre-filled by an LLM."),
        ("2", "Validate", "Answers checked against schema.json; defaults recorded as assumptions."),
        ("3", "Score", "Random Forest predicts the tier; a regressor predicts 0–100."),
        ("4", "Explain", "SHAP attributes the score to each control, then to each domain."),
        ("5", "Plan", "Every fix is re-scored to build the 30/60/90-day roadmap and report."),
    ]
    for i, (n, title, desc) in enumerate(steps):
        x = 0.45 + i * 2.52
        card(s, x, 2.1, 2.28, 2.85)
        oval(s, x + 0.22, 2.3, 0.5, 0.5, BLUE)
        tb(s, x + 0.22, 2.3, 0.5, 0.5, n, size=14, color=WHITE, bold=True,
           align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        tb(s, x + 0.22, 2.98, 1.95, 0.3, title, size=13.5, color=NAVY, bold=True)
        tb(s, x + 0.22, 3.36, 1.9, 1.45, desc, size=10, color=SLATE, spacing=1.15)
        if i < 4:
            ar = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 2.33),
                                    Inches(3.38), Inches(0.14), Inches(0.2))
            ar.fill.solid()
            ar.fill.fore_color.rgb = BLUE_L
            ar.line.fill.background()
            ar.shadow.inherit = False

    card(s, 0.45, 5.35, 6.05, 1.25, GREEN_BG, RGBColor(0xAB, 0xEF, 0xC6))
    tb(s, 0.7, 5.5, 5.6, 0.28, "DETERMINISTIC CORE", size=8.5, color=GREEN, bold=True, spc=1.4)
    tb(s, 0.7, 5.78, 5.55, 0.7,
       "Scores come from persisted model weights, so the same answers always produce the same score.",
       size=10.5, color=INK, spacing=1.12)
    card(s, 6.83, 5.35, 6.05, 1.25, BLUE_BG, RGBColor(0xCF, 0xE0, 0xFF))
    tb(s, 7.08, 5.5, 5.6, 0.28, "OPTIONAL AI LAYER", size=8.5, color=BLUE, bold=True, spc=1.4)
    tb(s, 7.08, 5.78, 5.55, 0.7,
       "The LLM only pre-fills answers and drafts narrative from computed facts — never the score.",
       size=10.5, color=INK, spacing=1.12)
    footer(s, num)
    notes(s, "Walk the five stages left to right. The key governance point is the split "
             "between the deterministic model core and the optional generative layer. "
             "If the audience is technical, mention schema validation and assumption tracking.")


def coverage_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "03 · How it works")
    heading(s, "Eleven domains. Thirty-three controls.",
            "A control-based questionnaire covering the areas attackers actually exploit.")
    domains = [
        ("PRF", "Business Profile"), ("IAM", "Identity & Access"),
        ("NET", "Network Security"), ("END", "Endpoint Protection"),
        ("VUL", "Vulnerability & Patch"), ("BCK", "Backup & Recovery"),
        ("GOV", "Governance & Resilience"), ("AWR", "Security Awareness"),
        ("DAT", "Data Protection"), ("MON", "Monitoring & Logging"),
        ("TPR", "Third Parties & Incidents"),
    ]
    for i, (code, name) in enumerate(domains):
        col, row = i % 4, i // 4
        x = 0.45 + col * 2.32
        y = 2.0 + row * 0.98
        card(s, x, y, 2.15, 0.8)
        tb(s, x + 0.18, y + 0.12, 0.6, 0.28, code, size=10, color=BLUE, bold=True, spc=1.0)
        tb(s, x + 0.18, y + 0.41, 1.85, 0.3, name, size=9.5, color=NAVY, bold=True)

    x = 9.75
    card(s, x, 2.0, 3.13, 3.72, NAVY, None)
    tb(s, x + 0.28, 2.22, 2.6, 0.28, "ONE RECORD", size=8.5, color=BLUE_L, bold=True, spc=1.5)
    for i, (value, label) in enumerate([("37", "model features"), ("33", "scored controls"),
                                        ("4", "risk tiers"), ("2", "trained models")]):
        y = 2.62 + i * 0.74
        tb(s, x + 0.28, y, 0.9, 0.45, value, size=21, color=WHITE, bold=True)
        tb(s, x + 1.18, y + 0.08, 1.7, 0.3, label, size=10, color=RGBColor(0xC9, 0xD4, 0xE5))

    tb(s, 0.45, 5.95, 9.0, 0.3,
       "Every control references CIS Controls v8 · ISO/IEC 27001:2022 · NIST CSF (indicative mapping).",
       size=10, color=SLATE, italic=True)
    footer(s, num)
    notes(s, "Coverage matters for credibility: the questionnaire is not a generic quiz, "
             "it is mapped to recognised frameworks. Be precise that the mapping is "
             "indicative and is not a compliance certification.")


def model_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "04 · Model & results")
    heading(s, "Four models compared. Random Forest wins.",
            "10,000 synthetic SMB records · stratified 80/20 split · 5-fold cross-validation")

    rows = [
        ("Logistic Regression", "93.5%", "0.848"),
        ("Decision Tree", "91.9%", "0.808"),
        ("Random Forest", "95.5%", "0.875"),
        ("XGBoost", "95.3%", "0.854"),
    ]
    x0, y0 = 0.45, 2.05
    widths = [2.45, 1.45, 1.35]
    rowh = 0.46
    heads = ["Model", "Accuracy", "Macro-F1"]
    xs = [x0]
    for w in widths[:-1]:
        xs.append(xs[-1] + w)
    rect(s, x0, y0, sum(widths), rowh, NAVY)
    for x, w, head in zip(xs, widths, heads):
        tb(s, x + 0.15, y0, w - 0.2, rowh, head, size=9.5,
           color=WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE,
           align=PP_ALIGN.LEFT if head == "Model" else PP_ALIGN.RIGHT)
    for i, (name, acc, f1) in enumerate(rows):
        y = y0 + rowh * (i + 1)
        best = name == "Random Forest"
        rect(s, x0, y, sum(widths), rowh, BLUE_BG if best else (WHITE if i % 2 == 0 else PALE))
        if best:
            rect(s, x0, y, 0.06, rowh, BLUE)
        for j, (x, w, value) in enumerate(zip(xs, widths, (name, acc, f1))):
            tb(s, x + 0.15, y, w - 0.2, rowh, value, size=10.5,
               color=NAVY if best else SLATE, bold=best,
               anchor=MSO_ANCHOR.MIDDLE,
               align=PP_ALIGN.LEFT if j == 0 else PP_ALIGN.RIGHT)
    tb(s, x0 + 0.15, y0 + rowh * 5 + 0.1, 5.0, 0.3,
       "Random Forest selected and persisted to models/cyber_risk_best_model_10k.pkl",
       size=8.5, color=MUTED)

    stats = [
        ("95.5%", "CLASSIFIER ACCURACY", "Held-out test set", BLUE),
        ("0.88", "MACRO-F1", "5-fold CV 0.8895 ± 0.0285", GREEN),
        ("1.66", "SCORE MAE", "0–100 regressor error", AMBER),
        ("0.979", "SCORE R²", "Variance explained", NAVY_SOFT),
    ]
    for i, (value, label, note, accent) in enumerate(stats):
        col, row = i % 2, i // 2
        x = 7.0 + col * 2.98
        y = 2.05 + row * 1.72
        stat_card(s, x, y, 2.78, 1.52, value, label, note, accent, value_size=27)

    card(s, 0.45, 5.55, 5.6, 1.0, AMBER_BG, RGBColor(0xFE, 0xD7, 0x89))
    tb(s, 0.7, 5.68, 5.1, 0.26, "READ THIS BEFORE QUOTING ACCURACY", size=8, color=AMBER,
       bold=True, spc=1.2)
    tb(s, 0.7, 5.95, 5.1, 0.5,
       "The dataset is synthetic: high accuracy shows the model learned the generator's "
       "scoring logic, not real-world predictive power.",
       size=9.5, color=INK, spacing=1.1)
    footer(s, num)
    notes(s, "Lead with the comparison, not the number. Random Forest was selected on "
             "macro-F1 as well as accuracy because the Critical class dominates the data. "
             "Then state the synthetic-data caveat yourself before anyone asks.")


def explain_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "05 · Explainability")
    heading(s, "Every point has a reason",
            "SHAP attributes the score to each answer, then aggregates it back to a control.")
    bullets(s, 0.45, 2.05, 5.65, 2.6, [
        ("Baseline 85.0 — ", "the average organisation in the training data."),
        ("Per-answer points — ", "a missing EDR adds 3.4 points; daily backups remove 3.9."),
        ("Reconciles exactly — ", "baseline plus contributions equals the final score."),
        ("Grounded language — ", "drivers are explained from a control knowledge base, not invented."),
    ], size=10.8, gap=9)

    card(s, 0.45, 4.65, 5.65, 0.95, WHITE, BORDER)
    tb(s, 0.68, 4.77, 5.2, 0.22, "SCORE DECOMPOSITION", size=8, color=SLATE, bold=True, spc=1.2)
    rich(s, 0.68, 5.02, 5.2, 0.42, [
        ("85.0", NAVY, True), ("  baseline  ", SLATE, False),
        ("+  Σ contributions  ", BLUE, True), ("=  ", SLATE, False),
        ("67.3", GREEN, True), ("  final", SLATE, False),
    ], size=12.5, anchor=MSO_ANCHOR.MIDDLE)
    tb(s, 0.45, 5.95, 5.65, 0.6,
       "The same explanation powers the waterfall chart, the driver list and the HTML report.",
       size=9.5, color=SLATE, italic=True, spacing=1.12)

    h = picture(s, ASSETS / "clean-explain.jpeg", 6.9, 2.05, 5.5)
    tb(s, 6.9, 2.05 + h + 0.08, 5.5, 0.25,
       "Score Explanation page · baseline, waterfall and plain-language drivers",
       size=8, color=MUTED, align=PP_ALIGN.CENTER)
    footer(s, num)
    notes(s, "Use the waterfall on the right as the visual anchor. Explain that SHAP values "
             "are computed on the transformed feature matrix and summed back to the original "
             "questions, so a manager sees controls rather than encoded columns.")


def remediation_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "05 · Explainability")
    heading(s, "Remediation is modelled, not guessed",
            "Every gap is re-scored by changing the answer and re-running the model.")
    steps = [
        ("Re-score", "Try every allowed value for the control."),
        ("Rank", "Keep the changes with the largest modelled drop."),
        ("Sequence", "Group by effort and cost into 0–30, 30–60 and 60–90 days."),
    ]
    for i, (title, desc) in enumerate(steps):
        y = 2.05 + i * 1.08
        oval(s, 0.45, y, 0.45, 0.45, BLUE)
        tb(s, 0.45, y, 0.45, 0.45, str(i + 1), size=12, color=WHITE, bold=True,
           align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        tb(s, 1.05, y - 0.02, 4.6, 0.3, title, size=12.5, color=NAVY, bold=True)
        tb(s, 1.05, y + 0.27, 4.55, 0.6, desc, size=10, color=SLATE, spacing=1.12)

    card(s, 0.45, 5.35, 5.65, 1.18, GREEN_BG, RGBColor(0xAB, 0xEF, 0xC6))
    tb(s, 0.7, 5.48, 5.2, 0.24, "PROJECTED AFTER THE 90-DAY ROADMAP", size=8, color=GREEN,
       bold=True, spc=1.2)
    rich(s, 0.7, 5.73, 5.2, 0.55, [
        ("67.3", NAVY, True), ("  →  ", SLATE, False), ("24.2", GREEN, True),
        ("   (−43.1 points)", GREEN, False),
    ], size=22)

    h = picture(s, ASSETS / "clean-remediation.jpeg", 6.9, 2.05, 5.5)
    tb(s, 6.9, 2.05 + h + 0.08, 5.5, 0.25,
       "Remediation Roadmap · phases, changes, effort and modelled reduction",
       size=8, color=MUTED, align=PP_ALIGN.CENTER)
    footer(s, num)
    notes(s, "This is the differentiator over a checklist: the plan is generated by the same "
             "model that produced the score. If you change an answer, the projection changes "
             "consistently. Mention the what-if simulator on the same page.")


def tour_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "02 · The product")
    heading(s, "Six pages, one workflow",
            "Assessment, dashboard, explanation, remediation, reports and methodology.")
    shots = [
        ("clean-assessment.jpeg", "Assessment", "33 controls with live score feedback"),
        ("clean-dashboard.jpeg", "Dashboard", "Posture, domains and top SHAP drivers"),
        ("clean-reports.jpeg", "Reports", "HTML report, CSV register and JSON data"),
    ]
    for i, (file, title, desc) in enumerate(shots):
        x = 0.45 + i * 4.23
        h = picture(s, ASSETS / file, x, 1.98, 3.95)
        tb(s, x, 1.98 + h + 0.1, 3.95, 0.28, title, size=12, color=NAVY, bold=True)
        tb(s, x, 1.98 + h + 0.38, 3.95, 0.3, desc, size=9.5, color=SLATE)
    tb(s, 0.45, 6.5, 12.4, 0.3,
       "Score Explanation and Remediation turn the numbers into action; Methodology documents the models and limits.",
       size=9.5, color=MUTED, align=PP_ALIGN.CENTER)
    footer(s, num)
    notes(s, "Show the product breadth quickly. The assessment page is the data entry, the "
             "dashboard is the executive read, and the report is what leaves the room. "
             "Point out that navigation is role-relevant rather than a generic dashboard.")


def engineering_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "06 · Engineering")
    heading(s, "Built like a product, not a notebook",
            "Reproducible setup, automated checks and a packaging layout that scales.")
    stats = [
        ("18", "AUTOMATED TESTS", "pytest: schema, extraction, scoring, reports", BLUE),
        ("5.6×", "FASTER PLANNING", "13 s → 2.3 s of model time", GREEN),
        ("14/14", "EXTRACTION CHECKS", "Rule-based fallback on labelled cases", AMBER),
        ("1 click", "FROM CLONE TO APP", "run.bat creates the venv and launches", NAVY_SOFT),
    ]
    for i, (value, label, note, accent) in enumerate(stats):
        col, row = i % 2, i // 2
        x = 0.45 + col * 3.15
        y = 2.0 + row * 1.62
        stat_card(s, x, y, 2.95, 1.45, value, label, note, accent, value_size=29)

    x = 7.15
    tb(s, x, 2.02, 5.6, 0.3, "STRUCTURE", size=8.5, color=BLUE, bold=True, spc=1.5)
    bullets(s, x, 2.38, 5.65, 1.7, [
        ("src/rakshascore — ", "pipeline, insights and one paths module."),
        ("config, data, models, results — ", "separated and reproducible."),
        ("pyproject + pinned requirements — ", "installable with pip install -e ."),
    ], size=10, gap=6)
    tb(s, x, 4.05, 5.6, 0.3, "GUARDRAILS", size=8.5, color=GREEN, bold=True, spc=1.5)
    bullets(s, x, 4.41, 5.65, 1.7, [
        ("No secrets in the repository — ", ".env is ignored; keys stay local."),
        ("Schema validation — ", "unknown values are dropped, not guessed."),
        ("Graceful degradation — ", "rules and templates work without an LLM."),
    ], size=10, gap=6)

    chips = ["Python 3.12", "pandas", "scikit-learn", "XGBoost", "SHAP", "Streamlit", "pytest"]
    cx = 0.45
    for label in chips:
        w = 0.34 + len(label) * 0.075
        chip(s, cx, 5.62, w, label, fill=WHITE, color=SLATE, size=8, h=0.3, bold=False)
        cx += w + 0.12
    footer(s, num)
    notes(s, "If the audience is academic, emphasise the test suite and the refactor: the "
             "project moved from a flat folder to a src layout with a single paths module. "
             "The performance fix batches model calls instead of scoring one row at a time.")


def ai_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "06 · Guardrails")
    heading(s, "AI assists. It never decides.",
            "Generative AI is confined to intake and narrative; the score stays deterministic.")
    card(s, 0.45, 2.05, 6.05, 3.55)
    rect(s, 0.45, 2.05, 6.05, 0.08, BLUE)
    tb(s, 0.75, 2.28, 5.4, 0.3, "WHERE AI HELPS", size=9, color=BLUE, bold=True, spc=1.4)
    bullets(s, 0.75, 2.68, 5.45, 2.6, [
        ("Free-text intake — ", "a description of the business pre-fills the questionnaire."),
        ("Narrative drafting — ", "management summaries written from a facts-only JSON."),
        ("Provider choice — ", "Anthropic Claude, Google Gemini or a local Ollama model."),
        ("Human override — ", "every extracted answer remains editable before scoring."),
    ], size=10.5, gap=8)

    card(s, 6.83, 2.05, 6.05, 3.55)
    rect(s, 6.83, 2.05, 6.05, 0.08, GREEN)
    tb(s, 7.13, 2.28, 5.4, 0.3, "WHERE AI IS NOT ALLOWED", size=9, color=GREEN, bold=True, spc=1.4)
    bullets(s, 7.13, 2.68, 5.45, 2.6, [
        ("The score — ", "produced by persisted model weights, not a prompt."),
        ("The explanation — ", "SHAP values from the model, not a generated story."),
        ("The facts — ", "answers are validated against config/schema.json."),
        ("The fallback — ", "rule-based extraction and templates work with no key."),
    ], size=10.5, gap=8, bullet_color=GREEN)

    card(s, 0.45, 5.9, 12.43, 0.82, NAVY, None)
    tb(s, 0.75, 6.04, 11.9, 0.24, "SECURITY POSTURE", size=8, color=BLUE_L, bold=True, spc=1.4)
    tb(s, 0.75, 6.3, 11.85, 0.32,
       "Keys live in .env or the session only; prompts receive the minimum facts needed; the repository contains no credentials.",
       size=11.5, color=WHITE, bold=True)
    footer(s, num)
    notes(s, "This slide pre-empts the obvious question about AI reliability. The architecture "
             "deliberately keeps the model in charge of the score and confines the LLM to "
             "language tasks. Offline mode makes the guarantee testable.")


def limitations_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "Honest by design")
    heading(s, "What this project does not claim",
            "Stating the limits is part of the engineering, not a disclaimer at the end.")
    items = [
        ("Synthetic training data",
         "Built from published breach statistics because no public labelled SMB dataset exists. "
         "Accuracy reflects the generator's logic, not real-world prediction."),
        ("Self-reported answers",
         "Responses are not independently verified. The score is only as honest as the input."),
        ("Indicative framework mapping",
         "CIS, ISO and NIST references help prioritise work; they are not a compliance audit."),
        ("Not a penetration test",
         "The result is a decision aid. It does not replace a professional security assessment."),
    ]
    for i, (title, body) in enumerate(items):
        y = 2.0 + i * 1.12
        card(s, 0.45, y, 8.55, 0.98)
        oval(s, 0.68, y + 0.24, 0.5, 0.5, RED_BG)
        tb(s, 0.68, y + 0.24, 0.5, 0.5, "!", size=14, color=RED, bold=True,
           align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        tb(s, 1.35, y + 0.15, 7.4, 0.3, title, size=11.5, color=NAVY, bold=True)
        tb(s, 1.35, y + 0.45, 7.45, 0.5, body, size=9.5, color=SLATE, spacing=1.1)

    card(s, 9.35, 2.0, 3.53, 4.55, NAVY, None)
    tb(s, 9.65, 2.3, 2.9, 0.3, "THE PRINCIPLE", size=8.5, color=BLUE_L, bold=True, spc=1.5)
    tb(s, 9.65, 2.7, 2.95, 2.5,
       "“Trust comes from stating the limits as clearly as the results.”",
       size=17, color=WHITE, bold=True, spacing=1.15)
    rect(s, 9.65, 5.25, 0.7, 0.05, BLUE_L)
    tb(s, 9.65, 5.4, 2.95, 0.9,
       "Each report repeats the assumptions and limitations for the reader.",
       size=9.5, color=RGBColor(0xC9, 0xD4, 0xE5), spacing=1.15)
    footer(s, num)
    notes(s, "Do not rush this slide. Examiners and practitioners both trust projects more "
             "when the author names the weaknesses. The report itself repeats these limits "
             "so the end user sees them too.")


def roadmap_slide(prs, num):
    s = new_slide(prs)
    eyebrow(s, "What's next")
    heading(s, "From strong prototype to pilot-ready",
            "A realistic path: harden the product, then validate it with real organisations.")
    cols = [
        ("NOW", "Shipped", GREEN, GREEN_BG, [
            "Six-page Streamlit application",
            "Explainable scoring and waterfall",
            "Modelled 30/60/90-day roadmap",
            "HTML, CSV and JSON exports",
            "18 tests, docs and one-click launcher",
        ]),
        ("NEXT", "0–3 months", BLUE, BLUE_BG, [
            "Authentication and workspaces",
            "PDF export and report branding",
            "CI pipeline and coverage gate",
            "More labelled extraction cases",
            "Deployment guide (Docker)",
        ]),
        ("LATER", "3–12 months", NAVY_SOFT, PALE, [
            "Partnership for real incident data",
            "Blind pilot with SMBs",
            "Benchmark against auditor ratings",
            "Microsoft 365 / Google Workspace",
            "Longitudinal score tracking",
        ]),
    ]
    for i, (tag, window, accent, tint, items) in enumerate(cols):
        x = 0.45 + i * 4.23
        card(s, x, 2.0, 3.95, 4.05)
        rect(s, x, 2.0, 3.95, 0.09, accent)
        chip(s, x + 0.28, 2.28, 0.95, tag, fill=tint, color=accent, size=8, h=0.26)
        tb(s, x + 0.28, 2.7, 3.35, 0.35, window, size=14, color=NAVY, bold=True)
        bullets(s, x + 0.28, 3.18, 3.4, 2.7, items, size=10, gap=5.5, bullet_color=accent)
    footer(s, num)
    notes(s, "Be honest that the current version is a prototype. The next step is not more "
             "features, it is validation: authentication for real use and a pilot that "
             "compares scores with an auditor's judgement.")


def close_slide(prs):
    s = new_slide(prs, NAVY)
    oval(s, -1.6, -2.0, 5.2, 5.2, NAVY_SOFT)
    oval(s, 10.9, 4.6, 4.6, 4.6, RGBColor(0x12, 0x2C, 0x4E))
    logo(s, 0.85, 1.15, 0.9)
    tb(s, 1.95, 1.2, 7.0, 0.34, "RAKSHASCORE", size=15, color=WHITE, bold=True, spc=2.4)
    tb(s, 1.95, 1.54, 7.0, 0.3, "CYBER RISK ASSESSMENT PLATFORM", size=8.5,
       color=RGBColor(0x8F, 0xA5, 0xC2), bold=True, spc=1.8)

    tb(s, 0.85, 2.35, 8.4, 1.9, "Know your score.\nFix what matters.",
       size=42, color=WHITE, bold=True, spacing=1.02)
    tb(s, 0.85, 4.3, 7.5, 0.7,
       "A full assessment, explanation and 90-day plan in under ten seconds — "
       "online or offline.",
       size=14, color=RGBColor(0xC9, 0xD4, 0xE5), spacing=1.2)

    card(s, 0.85, 5.35, 6.55, 0.62, NAVY_SOFT, RGBColor(0x2A, 0x45, 0x70))
    tb(s, 1.05, 5.45, 6.15, 0.42, "github.com/mahi1124/rakshascore",
       size=13, color=WHITE, bold=True)
    tb(s, 0.85, 6.2, 7.6, 0.3, "MIT licensed  ·  public repository  ·  double-click run.bat to start",
       size=9.5, color=RGBColor(0x8F, 0xA5, 0xC2))

    qr = HERE / "assets" / "repo_qr.png"
    if qr.exists():
        card(s, 10.15, 4.85, 2.35, 1.95, RGBColor(0x12, 0x2C, 0x4E), None)
        s.shapes.add_picture(str(qr), Inches(10.3), Inches(4.95), Inches(1.55), Inches(1.55))
        tb(s, 10.3, 6.55, 2.0, 0.24, "Scan to open the repo", size=7.5,
           color=RGBColor(0x8F, 0xA5, 0xC2), align=PP_ALIGN.CENTER)

    tb(s, 0.85, 6.72, 8.0, 0.36, "Thank you — questions?", size=16, color=WHITE, bold=True)
    notes(s, "Close on the repository. Invite questions about the model, the SHAP "
             "implementation or the product decisions. Mention that the deck, generator "
             "script and screenshots are in docs/presentation/.")


def build(out: Path):
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    prs.core_properties.title = "RakshaScore — AI-assisted cyber risk assessment"
    prs.core_properties.author = "RakshaScore contributors"
    prs.core_properties.subject = "Semester 5 machine learning project"
    prs.core_properties.comments = "Generated by docs/presentation/build_deck.py"

    title_slide(prs)
    agenda_slide(prs, 2)
    problem_slide(prs, 3)
    solution_slide(prs, 4)
    pipeline_slide(prs, 5)
    coverage_slide(prs, 6)
    model_slide(prs, 7)
    explain_slide(prs, 8)
    remediation_slide(prs, 9)
    tour_slide(prs, 10)
    engineering_slide(prs, 11)
    ai_slide(prs, 12)
    limitations_slide(prs, 13)
    roadmap_slide(prs, 14)
    close_slide(prs)

    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    print(f"Saved {out} ({len(prs.slides)} slides)")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build the RakshaScore presentation.")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output .pptx path")
    build(Path(ap.parse_args().out))
