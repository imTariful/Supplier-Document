"""
Report Generator module for individual and consolidated supplier verification audits.
Produces professional, audit-grade PDF reports with exact evidence excerpts and rule evaluations.
"""

import os
from decimal import Decimal
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.schemas.models import VerificationResult

class SupplierReportGenerator:
    @staticmethod
    def generate_single_report(verif_result: VerificationResult, output_pdf_path: str):
        os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
        doc = SimpleDocTemplate(output_pdf_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'AudTitle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'AudSub',
            parent=styles['Normal'],
            fontSize=8,
            leading=12,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=10
        )
        bold_style = ParagraphStyle(
            'AudBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=11
        )
        body_style = ParagraphStyle(
            'AudBody',
            parent=styles['Normal'],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b")
        )

        elements = []

        # Header
        elements.append(Paragraph("Aamar Garments Ltd — Supplier Verification Audit", title_style))
        elements.append(Paragraph(
            f"<b>Supplier ID:</b> {verif_result.supplier_id} | <b>Supplier Name:</b> {verif_result.supplier_name}<br/>"
            f"<b>Purchase Request:</b> PR-2026-AGL-0089 | <b>Audit Timestamp:</b> {verif_result.timestamp or '2026-11-03 21:00 UTC'}",
            subtitle_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10))

        # Decision Banner
        dec = verif_result.final_decision
        if dec == "APPROVE":
            dec_bg = colors.HexColor("#dcfce7")
            dec_color = "#15803d"
            dec_text = "PASSED & APPROVED FOR PROCUREMENT"
        elif dec == "REJECT":
            dec_bg = colors.HexColor("#fee2e2")
            dec_color = "#b91c1c"
            dec_text = "FAILED PROCUREMENT POLICY — REJECTED"
        else:
            dec_bg = colors.HexColor("#fef3c7")
            dec_color = "#b45309"
            dec_text = "ESCALATED FOR COMMERCIAL HUMAN REVIEW"

        dec_table = Table(
            [[Paragraph(f"<font size=12 color='{dec_color}'><b>DECISION: {verif_result.final_decision}</b></font><br/><font size=9 color='{dec_color}'>{dec_text}</font>", body_style)]],
            colWidths=[540]
        )
        dec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), dec_bg),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(dec_color)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(dec_table)
        elements.append(Spacer(1, 14))

        # Triggered Conditions & Evidence
        if verif_result.triggered_rules:
            elements.append(Paragraph("<b>Triggered Business Rules & Evidence Audit Trail</b>", ParagraphStyle('H2', parent=styles['Heading2'], fontSize=11, leading=14)))
            elements.append(Spacer(1, 6))

            headers = [
                Paragraph("<b>Rule ID</b>", bold_style),
                Paragraph("<b>Rule Description</b>", bold_style),
                Paragraph("<b>Actual Value</b>", bold_style),
                Paragraph("<b>Required Condition</b>", bold_style),
                Paragraph("<b>Source Evidence / Page</b>", bold_style)
            ]
            rule_rows = [headers]
            for r in verif_result.triggered_rules:
                rule_rows.append([
                    Paragraph(f"<b>{r.rule_id}</b>", bold_style),
                    Paragraph(r.rule_name, body_style),
                    Paragraph(r.actual_value, body_style),
                    Paragraph(r.expected_value, body_style),
                    Paragraph(f"<i>'{r.evidence}'</i><br/>[Doc: {r.document}, p.{r.page}]", body_style)
                ])

            rule_table = Table(rule_rows, colWidths=[55, 120, 105, 110, 150])
            rule_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(rule_table)
            elements.append(Spacer(1, 14))
        else:
            elements.append(Paragraph("<b>Triggered Business Rules:</b> None. All mandatory compliance rules evaluated with PASS status.", body_style))
            elements.append(Spacer(1, 14))

        # Complete Rule Evaluation Inventory
        elements.append(Paragraph("<b>Complete Policy Evaluation Checklist</b>", ParagraphStyle('H3', parent=styles['Heading3'], fontSize=10, leading=13)))
        elements.append(Spacer(1, 4))
        chk_headers = [Paragraph("<b>Rule ID</b>", bold_style), Paragraph("<b>Rule Name</b>", bold_style), Paragraph("<b>Status</b>", bold_style), Paragraph("<b>Severity</b>", bold_style), Paragraph("<b>Finding Summary</b>", bold_style)]
        chk_rows = [chk_headers]
        for r in verif_result.all_rule_results:
            st_color = "#16a34a" if r.status == "PASS" else ("#dc2626" if r.status == "FAILED" else "#d97706")
            chk_rows.append([
                Paragraph(r.rule_id, body_style),
                Paragraph(r.rule_name, body_style),
                Paragraph(f"<font color='{st_color}'><b>{r.status}</b></font>", body_style),
                Paragraph(r.severity, body_style),
                Paragraph(r.explanation, body_style)
            ])
        chk_table = Table(chk_rows, colWidths=[55, 135, 65, 75, 210])
        chk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(chk_table)

        doc.build(elements)
        print(f"Generated single report: {output_pdf_path}")
