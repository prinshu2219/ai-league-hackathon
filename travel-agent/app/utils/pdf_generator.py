"""
pdf_generator.py — Sprint 3B
─────────────────────────────
Generates a beautiful A4 travel itinerary PDF using reportlab.
Called by pdf_generator_agent in agents/__init__.py.
"""

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)

# ── Brand colors ──────────────────────────────────────────
TEAL       = colors.HexColor("#0D9488")
TEAL_LIGHT = colors.HexColor("#CCFBF1")
ORANGE     = colors.HexColor("#EA580C")
SLATE      = colors.HexColor("#1E293B")
SLATE_MID  = colors.HexColor("#64748B")
SLATE_LT   = colors.HexColor("#F1F5F9")
WHITE      = colors.white

SEG_COLORS = {
    "transport": colors.HexColor("#DBEAFE"),
    "checkin":   colors.HexColor("#D1FAE5"),
    "activity":  colors.HexColor("#FEE2E2"),
    "meal":      colors.HexColor("#FEF3C7"),
    "free_time": colors.HexColor("#EDE9FE"),
}
SEG_ICONS = {
    "transport": ">>", "checkin": "[H]",
    "activity": "[*]", "meal": "[~]", "free_time": "[o]",
}
DAY_COLORS = [
    TEAL,
    colors.HexColor("#EA580C"),
    colors.HexColor("#7C3AED"),
    colors.HexColor("#0369A1"),
    colors.HexColor("#166534"),
    colors.HexColor("#9D174D"),
]


def _styles():
    return {
        "cover_title": ParagraphStyle("cover_title",
            fontSize=30, leading=36, textColor=WHITE,
            fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=6),
        "cover_sub": ParagraphStyle("cover_sub",
            fontSize=12, leading=16, textColor=TEAL_LIGHT,
            fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4),
        "cover_meta": ParagraphStyle("cover_meta",
            fontSize=10, leading=14, textColor=WHITE,
            fontName="Helvetica", alignment=TA_CENTER),
        "section_head": ParagraphStyle("section_head",
            fontSize=13, leading=17, textColor=WHITE,
            fontName="Helvetica-Bold", alignment=TA_LEFT),
        "day_head": ParagraphStyle("day_head",
            fontSize=11, leading=14, textColor=WHITE,
            fontName="Helvetica-Bold", alignment=TA_LEFT),
        "day_cost": ParagraphStyle("day_cost",
            fontSize=10, leading=13, textColor=WHITE,
            fontName="Helvetica-Bold", alignment=TA_RIGHT),
        "seg_title": ParagraphStyle("seg_title",
            fontSize=10, leading=13, textColor=SLATE,
            fontName="Helvetica-Bold"),
        "seg_body": ParagraphStyle("seg_body",
            fontSize=9, leading=12, textColor=SLATE_MID,
            fontName="Helvetica"),
        "seg_note": ParagraphStyle("seg_note",
            fontSize=8, leading=11, textColor=TEAL,
            fontName="Helvetica-Oblique"),
        "seg_time": ParagraphStyle("seg_time",
            fontSize=9, leading=12, textColor=SLATE_MID,
            fontName="Helvetica-Bold"),
        "seg_cost": ParagraphStyle("seg_cost",
            fontSize=9, leading=12, textColor=SLATE,
            fontName="Helvetica-Bold", alignment=TA_RIGHT),
        "metric_val": ParagraphStyle("metric_val",
            fontSize=16, leading=20, textColor=TEAL,
            fontName="Helvetica-Bold", alignment=TA_CENTER),
        "metric_lbl": ParagraphStyle("metric_lbl",
            fontSize=8, leading=10, textColor=SLATE_MID,
            fontName="Helvetica", alignment=TA_CENTER),
        "tip": ParagraphStyle("tip",
            fontSize=9, leading=13, textColor=SLATE,
            fontName="Helvetica", leftIndent=8),
        "highlight": ParagraphStyle("highlight",
            fontSize=8, leading=11, textColor=SLATE_MID,
            fontName="Helvetica-Oblique", leftIndent=4, spaceAfter=2),
        "footer": ParagraphStyle("footer",
            fontSize=7, leading=9, textColor=SLATE_MID,
            fontName="Helvetica", alignment=TA_CENTER),
    }


def _section_banner(text, s):
    tbl = Table([[Paragraph(text, s["section_head"])]], colWidths=[170*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), TEAL),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
    ]))
    return tbl


def _day_banner(day_num, date_str, theme, cost, s):
    bg = DAY_COLORS[(day_num - 1) % len(DAY_COLORS)]
    label = f"Day {day_num}  |  {date_str}  |  {theme}"
    cost_label = f"~Rs {cost:,}"
    tbl = Table(
        [[Paragraph(label, s["day_head"]), Paragraph(cost_label, s["day_cost"])]],
        colWidths=[120*mm, 50*mm],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), bg),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    return tbl


def _segment_row(seg, s):
    seg_type = seg.get("type", "activity")
    bg       = SEG_COLORS.get(seg_type, SLATE_LT)
    icon     = SEG_ICONS.get(seg_type, "-")
    cost_raw = seg.get("cost", 0)
    cost_str = f"Rs {cost_raw:,}" if cost_raw > 0 else "Free"

    desc_content = [Paragraph(f"{icon}  {seg.get('title','')}", s["seg_title"])]
    if seg.get("description"):
        desc_content.append(Paragraph(seg["description"], s["seg_body"]))
    note = seg.get("notes", "")
    if note and note != seg.get("description", ""):
        desc_content.append(Paragraph(f"Tip: {note}", s["seg_note"]))

    tbl = Table(
        [[Paragraph(seg.get("time",""), s["seg_time"]),
          desc_content,
          Paragraph(cost_str, s["seg_cost"])]],
        colWidths=[18*mm, 128*mm, 24*mm],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), bg),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("LINEBELOW",     (0,0), (-1,-1), 0.3, colors.HexColor("#E2E8F0")),
    ]))
    return tbl


def _build_cover(story, summary, s):
    dest     = summary.get("destination", "Your Destination")
    duration = summary.get("duration", "")
    dates    = summary.get("dates", "")
    travelers = summary.get("travelers", 1)
    style_name = summary.get("style", "")
    cost     = summary.get("estimated_cost", "")
    savings  = summary.get("savings", "")

    traveler_str = f"{travelers} traveler{'s' if int(str(travelers)) > 1 else ''}"

    cover = Table([
        [Paragraph("AI Travel Planning Agent", s["cover_sub"])],
        [Spacer(1, 4)],
        [Paragraph(f"Your {duration} Trip to", s["cover_sub"])],
        [Paragraph(dest, s["cover_title"])],
        [Spacer(1, 8)],
        [Paragraph(f"{dates}  ·  {traveler_str}  ·  {style_name}", s["cover_meta"])],
        [Spacer(1, 6)],
        [Paragraph(f"Estimated cost: {cost}  ·  {savings}", s["cover_meta"])],
        [Spacer(1, 8)],
        [Paragraph("Powered by GPT-4o", ParagraphStyle("badge",
            fontSize=9, textColor=TEAL_LIGHT, fontName="Helvetica", alignment=TA_CENTER))],
    ], colWidths=[170*mm])
    cover.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), SLATE),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(cover)
    story.append(Spacer(1, 8*mm))


def _build_metrics(story, summary, budget, s):
    story.append(_section_banner("  Trip At A Glance", s))
    story.append(Spacer(1, 4*mm))

    items = [
        (summary.get("estimated_cost", ""), "Total Cost"),
        (summary.get("savings", ""),         "Budget Remaining"),
        (f"Rs {budget.get('travel', 0):,}",  "Transport"),
        (f"Rs {budget.get('stay', 0):,}",    "Accommodation"),
        (f"Rs {budget.get('food', 0):,}",    "Food"),
        (f"Rs {budget.get('activities', 0):,}", "Activities"),
    ]

    rows_of_3 = [items[i:i+3] for i in range(0, len(items), 3)]
    for row in rows_of_3:
        while len(row) < 3:
            row.append(("", ""))
        tbl = Table(
            [[Paragraph(v, s["metric_val"]) for v, _ in row],
             [Paragraph(l, s["metric_lbl"]) for _, l in row]],
            colWidths=[56*mm, 56*mm, 58*mm],
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), SLATE_LT),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LINEAFTER",     (0,0), (-2,-1), 0.5, colors.HexColor("#CBD5E1")),
            ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 2*mm))


def _build_itinerary(story, itinerary, s):
    story.append(Spacer(1, 4*mm))
    story.append(_section_banner("  Day-by-Day Itinerary", s))

    for day in itinerary:
        story.append(Spacer(1, 4*mm))
        block = [
            _day_banner(day["day_number"], day.get("date", ""),
                        day.get("theme", ""), day.get("daily_cost_estimate", 0), s),
        ]
        for seg in day.get("segments", []):
            block.append(_segment_row(seg, s))

        highlights = day.get("highlights", [])
        if highlights:
            hl_text = "  ·  ".join(highlights)
            block.append(Paragraph(f"Highlights: {hl_text}", s["highlight"]))

        # Keep at least the header + first 2 segs together
        story.append(KeepTogether(block[:3]))
        for item in block[3:]:
            story.append(item)


def _build_tips(story, tips, s):
    if not tips:
        return
    story.append(Spacer(1, 6*mm))
    story.append(_section_banner("  Local Tips & Advice", s))
    story.append(Spacer(1, 3*mm))
    for tip in tips:
        story.append(Paragraph(f"•  {tip}", s["tip"]))
        story.append(Spacer(1, 2*mm))


def _build_footer(story, s):
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_LT))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "Generated by AI Travel Planning Agent  ·  Powered by GPT-4o  ·  "
        "Prices are estimates — verify availability before booking",
        s["footer"],
    ))


def generate_pdf_bytes(trip_summary: dict, daily_itinerary: list,
                       final_budget_summary: dict) -> bytes:
    """
    Generate the PDF and return raw bytes (for Streamlit download button).
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=15*mm, bottomMargin=15*mm,
        title=f"{trip_summary.get('destination', 'Trip')} Itinerary",
        author="AI Travel Planning Agent",
    )

    s     = _styles()
    story = []

    _build_cover(story, trip_summary, s)
    _build_metrics(story, trip_summary, final_budget_summary, s)
    story.append(PageBreak())
    _build_itinerary(story, daily_itinerary, s)
    _build_tips(story, trip_summary.get("local_tips", []), s)
    _build_footer(story, s)

    doc.build(story)
    return buf.getvalue()