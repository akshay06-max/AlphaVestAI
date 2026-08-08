"""PDF Report Generator for AlphaVest Capital using ReportLab — Page 18 Download Requirements."""
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from models.schemas import InvestmentReport, CompanyComparison


def generate_investment_report_pdf(report: InvestmentReport) -> bytes:
    """Generate a clean, professional PDF from an InvestmentReport."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0D47A1"),
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#555555"),
    )
    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1565C0"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#222222"),
    )
    bullet_style = ParagraphStyle(
        "BulletCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#222222"),
        leftIndent=12,
    )

    story = []

    # Title & Header
    story.append(Paragraph("💹 AlphaVest Capital — Investment Research Report", title_style))
    story.append(Paragraph(f"<b>Company:</b> {report.company_name} &nbsp;|&nbsp; <b>Industry:</b> {report.industry}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0D47A1"), spaceAfter=10))

    # Executive / Investment Summary
    story.append(Paragraph("Executive Summary & Recommendation", h2_style))
    summary_text = report.executive_summary if report.executive_summary else report.investment_summary
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 8))

    # Company Overview
    story.append(Paragraph("Company Overview & Business Model", h2_style))
    story.append(Paragraph(f"<b>Overview:</b> {report.company_overview}", body_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Business Model:</b> {report.business_model}", body_style))
    story.append(Spacer(1, 8))

    # Financial Highlights & Latest News
    story.append(Paragraph("Financial Highlights & Recent Developments", h2_style))
    story.append(Paragraph(f"<b>Financial Data:</b> {report.financial_highlights}", body_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Recent News:</b> {report.latest_news}", body_style))
    story.append(Spacer(1, 8))

    # Strengths & Weaknesses Table
    story.append(Paragraph("Strategic Evaluation (Strengths & Risks)", h2_style))
    
    strengths_html = "<br/>".join(f"• {s}" for s in report.strengths)
    weaknesses_html = "<br/>".join(f"• {w}" for w in report.weaknesses)
    
    table_data = [
        [
            Paragraph("<b>✅ Key Strengths</b>", ParagraphStyle("THead1", parent=body_style, fontName="Helvetica-Bold", textColor=colors.HexColor("#1B5E20"))),
            Paragraph("<b>⚠️ Potential Risks / Challenges</b>", ParagraphStyle("THead2", parent=body_style, fontName="Helvetica-Bold", textColor=colors.HexColor("#B71C1C"))),
        ],
        [
            Paragraph(strengths_html, body_style),
            Paragraph(weaknesses_html, body_style),
        ],
    ]
    
    t = Table(table_data, colWidths=[270, 270])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#E8F5E9")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FFEBEE")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    # Growth Opportunities
    if report.growth_opportunities:
        story.append(Paragraph("Growth Opportunities", h2_style))
        for g in report.growth_opportunities:
            story.append(Paragraph(f"• {g}", bullet_style))
        story.append(Spacer(1, 8))

    # Conclusion & Disclaimer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#999999"), spaceBefore=10, spaceAfter=6))
    disclaimer = "<i>Confidential — Prepared by AlphaVest Capital AI Research Assistant for investment advisory analysis.</i>"
    story.append(Paragraph(disclaimer, ParagraphStyle("Disc", parent=body_style, fontSize=8, textColor=colors.HexColor("#777777"))))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_comparison_pdf(comparison: CompanyComparison, raw_research: dict = None) -> bytes:
    """Generate a clean PDF for multi-company comparisons."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CompTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.HexColor("#0D47A1"),
    )
    body_style = ParagraphStyle(
        "CompBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
    )
    h2_style = ParagraphStyle(
        "CompH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#1565C0"),
        spaceBefore=8,
        spaceAfter=4,
    )

    story = [
        Paragraph("💹 AlphaVest Capital — Multi-Company Comparative Analysis", title_style),
        Paragraph(f"<b>Compared:</b> {', '.join(comparison.companies_compared)}", body_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0D47A1"), spaceAfter=10),
        Paragraph("Executive Summary & Recommended Pick", h2_style),
        Paragraph(f"<b>Recommended Pick:</b> {comparison.recommended_pick}", body_style),
        Spacer(1, 4),
        Paragraph(comparison.comparison_summary, body_style),
        Spacer(1, 8),
    ]

    if raw_research:
        story.append(Paragraph("Company Research Summaries", h2_style))
        for comp, txt in raw_research.items():
            story.append(Paragraph(f"<b>{comp}:</b>", h2_style))
            story.append(Paragraph(txt[:600] + ("..." if len(txt) > 600 else ""), body_style))
            story.append(Spacer(1, 4))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
