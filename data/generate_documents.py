#!/usr/bin/env python3
"""
Aamar Garments Ltd — Supplier Document Generator
Generates 10 supplier packs (10 quotations + 10 contracts = 20 PDF documents)
covering all deterministic business rules and boundary cases.
"""

import os
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

OUTPUT_DIR = "data/input"
os.makedirs(OUTPUT_DIR, exist_ok=True)

PACKS_DATA = [
    {
        "id": "PACK-01",
        "supplier_name": "Vertex Textiles & Trims Ltd",
        "reg_address": "Plot 42-48, Export Processing Zone, Dhaka-1349",
        "tin": "482910482910",
        "bin": "001928374-0101",
        "contact_person": "Engr. Rafiqul Islam, Director of Sales",
        "items": [
            {"code": "ITEM-A", "desc": "Cotton twill fabric, 280 gsm", "qty": 12000, "unit": "metre", "unit_price": Decimal("470.00")},
            {"code": "ITEM-B", "desc": "Metal zipper, 18 cm", "qty": 20000, "unit": "piece", "unit_price": Decimal("37.00")},
            {"code": "ITEM-C", "desc": "Polyester sewing thread, High tenacity 40/2", "qty": 800, "unit": "cone", "unit_price": Decimal("205.00")},
            {"code": "ITEM-D", "desc": "Poly bag, 30 x 40 cm LDPE", "qty": 50000, "unit": "piece", "unit_price": Decimal("6.40")},
            {"code": "ITEM-E", "desc": "Carton box, 5-ply corrugated export grade", "qty": 3000, "unit": "piece", "unit_price": Decimal("92.00")},
        ],
        "delivery_days": 25,
        "validity_days": 60,
        "advance_pct": Decimal("15.0"),
        "remaining_days": 45,
        "penalty_clause": "In the event of delay in delivery beyond the agreed schedule, the Supplier shall pay a late-delivery penalty of 0.5% of total order value per week of delay.",
        "vat_separate": True,
        "arithmetic_error": False,
        "scanned": False,
        "expected_decision": "APPROVE",
        "expected_rule_ids": []
    },
    {
        "id": "PACK-02",
        "supplier_name": "Apex Apparel Accessories Ltd",
        "reg_address": "Chandana Chowrasta, Gazipur-1702",
        "tin": "771829401923",
        "bin": "002849102-0202",
        "contact_person": "Mahmudul Hasan, Head of Commercial",
        "items": [
            {"code": "ITEM-A", "desc": "Cotton twill fabric, 280 gsm", "qty": 12000, "unit": "metre", "unit_price": Decimal("510.00")}, # R01: 510 > 480*1.03 (494.40) -> +6.25%
            {"code": "ITEM-B", "desc": "Metal zipper, 18 cm", "qty": 20000, "unit": "piece", "unit_price": Decimal("38.00")},
            {"code": "ITEM-C", "desc": "Polyester sewing thread, High tenacity 40/2", "qty": 800, "unit": "cone", "unit_price": Decimal("210.00")},
            {"code": "ITEM-D", "desc": "Poly bag, 30 x 40 cm LDPE", "qty": 50000, "unit": "piece", "unit_price": Decimal("6.50")},
            {"code": "ITEM-E", "desc": "Carton box, 5-ply corrugated export grade", "qty": 3000, "unit": "piece", "unit_price": Decimal("95.00")},
        ],
        "delivery_days": 28,
        "validity_days": 45,
        "advance_pct": Decimal("20.0"),
        "remaining_days": 45,
        "penalty_clause": "The Supplier agrees to a liquidated damage of 0.5% of order value per week of delay for failure to deliver within promised period.",
        "vat_separate": True,
        "arithmetic_error": False,
        "scanned": False,
        "expected_decision": "REJECT",
        "expected_rule_ids": ["R01"]
    },
    {
        "id": "PACK-03",
        "supplier_name": "Bengal Stitch & Pack Solutions",
        "reg_address": "BSCIC Industrial Estate, Narayanganj-1400",
        "tin": "552910482110",
        "bin": "003928103-0303",
        "contact_person": "Tanveer Ahmed, General Manager",
        "items": [
            {"code": "ITEM-A", "desc": "Cotton twill fabric, 280 gsm", "qty": 12000, "unit": "metre", "unit_price": Decimal("475.00")},
            {"code": "ITEM-B", "desc": "Metal zipper, 18 cm", "qty": 20000, "unit": "piece", "unit_price": Decimal("37.50")},
            {"code": "ITEM-C", "desc": "Polyester sewing thread, High tenacity 40/2", "qty": 800, "unit": "cone", "unit_price": Decimal("208.00")},
            {"code": "ITEM-D", "desc": "Poly bag, 30 x 40 cm LDPE", "qty": 50000, "unit": "piece", "unit_price": Decimal("6.40")},
            {"code": "ITEM-E", "desc": "Carton box, 5-ply corrugated export grade", "qty": 3000, "unit": "piece", "unit_price": Decimal("94.00")},
        ],
        "delivery_days": 30,
        "validity_days": 40,
        "advance_pct": Decimal("25.0"), # R02: 25% > 20%
        "remaining_days": 30,
        "penalty_clause": "Late delivery shall attract a penalty equal to 0.75% of order value per week of delay.",
        "vat_separate": True,
        "arithmetic_error": False,
        "scanned": False,
        "expected_decision": "REJECT",
        "expected_rule_ids": ["R02"]
    },
    {
        "id": "PACK-04",
        "supplier_name": "Meghna Fasteners & Accessories Ltd",
        "reg_address": "Baizid Bostami Industrial Zone, Chittagong-4210",
        "tin": "992810482012",
        "bin": "004928104-0404",
        "contact_person": "Shahadat Hossain, Commercial Lead",
        "items": [
            {"code": "ITEM-A", "desc": "Cotton twill fabric, 280 gsm", "qty": 12000, "unit": "metre", "unit_price": Decimal("465.00")},
            {"code": "ITEM-B", "desc": "Metal zipper, 18 cm", "qty": 20000, "unit": "piece", "unit_price": Decimal("36.00")},
            {"code": "ITEM-C", "desc": "Polyester sewing thread, High tenacity 40/2", "qty": 800, "unit": "cone", "unit_price": Decimal("200.00")},
            {"code": "ITEM-D", "desc": "Poly bag, 30 x 40 cm LDPE", "qty": 50000, "unit": "piece", "unit_price": Decimal("6.30")},
            {"code": "ITEM-E", "desc": "Carton box, 5-ply corrugated export grade", "qty": 3000, "unit": "piece", "unit_price": Decimal("90.00")},
        ],
        "delivery_days": 25,
        "validity_days": 50,
        "advance_pct": Decimal("15.0"),
        "remaining_days": 45,
        "penalty_clause": "In case of delayed shipment, a token penalty of 0.25% of order value per week of delay shall be deducted.", # R07: 0.25% < 0.5%
        "vat_separate": True,
        "arithmetic_error": False,
        "scanned": False,
        "expected_decision": "REJECT",
        "expected_rule_ids": ["R07"]
    },
    {
        "id": "PACK-05",
        "supplier_name": "Padma Packaging & Labeling Corp",
        "reg_address": "Hemayetpur, Savar, Dhaka-1340",
        "tin": "", # R04: Missing TIN
        "bin": "", # R05: Missing BIN
        "contact_person": "Nazmul Huda, Sales Director",
        "items": [
            {"code": "ITEM-A", "desc": "Cotton twill fabric, 280 gsm", "qty": 12000, "unit": "metre", "unit_price": Decimal("470.00")},
            {"code": "ITEM-B", "desc": "Metal zipper, 18 cm", "qty": 20000, "unit": "piece", "unit_price": Decimal("37.00")},
            {"code": "ITEM-C", "desc": "Polyester sewing thread, High tenacity 40/2", "qty": 800, "unit": "cone", "unit_price": Decimal("205.00")},
            {"code": "ITEM-D", "desc": "Poly bag, 30 x 40 cm LDPE", "qty": 50000, "unit": "piece", "unit_price": Decimal("6.40")},
            {"code": "ITEM-E", "desc": "Carton box, 5-ply corrugated export grade", "qty": 3000, "unit": "piece", "unit_price": Decimal("91.00")},
        ],
        "delivery_days": 28,
        "validity_days": 45,
        "advance_pct": Decimal("18.0"),
        "remaining_days": 45,
        "penalty_clause": "Late delivery penalty is stipulated at 0.5% of total order value per week of unexcused delay.",
        "vat_separate": True,
        "arithmetic_error": False,
        "scanned": True,
        "expected_decision": "REJECT",
        "expected_rule_ids": ["R04", "R05"]
    },
    {
        "id": "PACK-06",
        "supplier_name": "Jamuna Yarn & Thread Mills",
        "reg_address": "Kashimpur, Gazipur-1700",
        "tin": "334910482911",
        "bin": "006928106-0606",
        "contact_person": "Golam Kibria, General Manager",
        "items": [
            {"code": "ITEM-A", "desc": "Cotton twill fabric, 280 gsm", "qty": 12000, "unit": "metre", "unit_price": Decimal("472.00")},
            {"code": "ITEM-B", "desc": "Metal zipper, 18 cm", "qty": 20000, "unit": "piece", "unit_price": Decimal("37.20")},
            {"code": "ITEM-C", "desc": "Polyester sewing thread, High tenacity 40/2", "qty": 800, "unit": "cone", "unit_price": Decimal("206.00")},
            {"code": "ITEM-D", "desc": "Poly bag, 30 x 40 cm LDPE", "qty": 50000, "unit": "piece", "unit_price": Decimal("6.45")},
            {"code": "ITEM-E", "desc": "Carton box, 5-ply corrugated export grade", "qty": 3000, "unit": "piece", "unit_price": Decimal("93.00")},
        ],
        "delivery_days": 52, # R06: 52 > 45 days
        "validity_days": 45,
        "advance_pct": Decimal("15.0"),
        "remaining_days": 45,
        "penalty_clause": "Delay penalty shall be assessed at 0.6% of order value per week of delay beyond promised completion.",
        "vat_separate": True,
        "arithmetic_error": False,
        "scanned": False,
        "expected_decision": "REJECT",
        "expected_rule_ids": ["R06"]
    },
    {
        "id": "PACK-07",
        "supplier_name": "Rupsha Trims & Poly Industries",
        "reg_address": "Tongi Industrial Area, Gazipur-1710",
        "tin": "882910482912",
        "bin": "007928107-0707",
        "contact_person": "Kazi Moinuddin, Commercial Manager",
        "items": [
            {"code": "ITEM-A", "desc": "Cotton twill fabric, 280 gsm", "qty": 12000, "unit": "metre", "unit_price": Decimal("488.00")}, # H01: 488 > 480 and 488 <= 494.40 (+1.67%)
            {"code": "ITEM-B", "desc": "Metal zipper, 18 cm", "qty": 20000, "unit": "piece", "unit_price": Decimal("37.50")},
            {"code": "ITEM-C", "desc": "Polyester sewing thread, High tenacity 40/2", "qty": 800, "unit": "cone", "unit_price": Decimal("205.00")},
            {"code": "ITEM-D", "desc": "Poly bag, 30 x 40 cm LDPE", "qty": 50000, "unit": "piece", "unit_price": Decimal("6.40")},
            {"code": "ITEM-E", "desc": "Carton box, 5-ply corrugated export grade", "qty": 3000, "unit": "piece", "unit_price": Decimal("94.00")},
        ],
        "delivery_days": 38, # H04: 38 is in 31-45 days
        "validity_days": 45,
        "advance_pct": Decimal("15.0"),
        "remaining_days": 45,
        "penalty_clause": "In case of delay, 0.5% per week of order value will be deducted as late delivery penalty.",
        "vat_separate": True,
        "arithmetic_error": False,
        "scanned": False,
        "expected_decision": "NEEDS_HUMAN_REVIEW",
        "expected_rule_ids": ["H01", "H04"]
    },
    {
        "id": "PACK-08",
        "supplier_name": "Karnafuli Zipper & Button Co",
        "reg_address": "Chittagong Export Processing Zone, Sector 2",
        "tin": "112910482913",
        "bin": "008928108-0808",
        "contact_person": "Jasim Uddin, Sales Executive",
        "items": [
            {"code": "ITEM-A", "desc": "Cotton twill fabric, 280 gsm", "qty": 10000, "unit": "metre", "unit_price": Decimal("470.00")}, # H02: 10000 vs 12000 (-16.67% > 5%)
            {"code": "ITEM-B", "desc": "Metal zipper, 18 cm", "qty": 20000, "unit": "piece", "unit_price": Decimal("37.00")},
            {"code": "ITEM-C", "desc": "Polyester sewing thread, High tenacity 40/2", "qty": 800, "unit": "cone", "unit_price": Decimal("205.00")},
            {"code": "ITEM-D", "desc": "Poly bag, 30 x 40 cm LDPE", "qty": 50000, "unit": "piece", "unit_price": Decimal("6.40")},
            {"code": "ITEM-E", "desc": "Carton box, 5-ply corrugated export grade", "qty": 3000, "unit": "piece", "unit_price": Decimal("92.00")},
        ],
        "delivery_days": 28,
        "validity_days": 45,
        "advance_pct": Decimal("10.0"),
        "remaining_days": 45,
        "penalty_clause": "Late delivery penalty is stipulated at 0.5% of order value per week of delay.",
        "vat_separate": True,
        "arithmetic_error": False,
        "scanned": False,
        "expected_decision": "NEEDS_HUMAN_REVIEW",
        "expected_rule_ids": ["H02"]
    },
    {
        "id": "PACK-09",
        "supplier_name": "Shitalakshya Dyeing & Trims Ltd",
        "reg_address": "Fatullah, Narayanganj-1420",
        "tin": "662910482914",
        "bin": "009928109-0909",
        "contact_person": "Abdul Wadud, Managing Partner",
        "items": [
            {"code": "ITEM-A", "desc": "Cotton twill fabric, 280 gsm", "qty": 12000, "unit": "metre", "unit_price": Decimal("468.00")},
            {"code": "ITEM-B", "desc": "Metal zipper, 18 cm", "qty": 20000, "unit": "piece", "unit_price": Decimal("36.50")},
            {"code": "ITEM-C", "desc": "Polyester sewing thread, High tenacity 40/2", "qty": 800, "unit": "cone", "unit_price": Decimal("204.00")},
            {"code": "ITEM-D", "desc": "Poly bag, 30 x 40 cm LDPE", "qty": 50000, "unit": "piece", "unit_price": Decimal("6.35")},
            {"code": "ITEM-E", "desc": "Carton box, 5-ply corrugated export grade", "qty": 3000, "unit": "piece", "unit_price": Decimal("91.00")},
        ],
        "delivery_days": 26,
        "validity_days": 20, # H07: 20 days < 30 days
        "advance_pct": Decimal("15.0"),
        "remaining_days": 75, # H03: 75 days > 60 days
        "penalty_clause": "Liquidated damages for late delivery shall be 0.5% of total order value per week of delay.",
        "vat_separate": True,
        "arithmetic_error": False,
        "scanned": False,
        "expected_decision": "NEEDS_HUMAN_REVIEW",
        "expected_rule_ids": ["H03", "H07"]
    },
    {
        "id": "PACK-10",
        "supplier_name": "Surma Carton & Packaging Works",
        "reg_address": "Shahjibazar, Habiganj-3300",
        "tin": "222910482915",
        "bin": "010928110-1010",
        "contact_person": "Siddiqur Rahman, Operations Head",
        "items": [
            {"code": "ITEM-A", "desc": "Cotton twill fabric, 280 gsm", "qty": 12000, "unit": "metre", "unit_price": Decimal("470.00")},
            {"code": "ITEM-B", "desc": "Metal zipper, 18 cm", "qty": 20000, "unit": "piece", "unit_price": Decimal("37.00")},
            {"code": "ITEM-C", "desc": "Polyester sewing thread, High tenacity 40/2", "qty": 800, "unit": "cone", "unit_price": Decimal("205.00")},
            {"code": "ITEM-D", "desc": "Poly bag, 30 x 40 cm LDPE", "qty": 50000, "unit": "piece", "unit_price": Decimal("6.40")},
            {"code": "ITEM-E", "desc": "Carton box, 5-ply corrugated export grade", "qty": 3000, "unit": "piece", "unit_price": Decimal("92.00")},
        ],
        "delivery_days": 28,
        "validity_days": 45,
        "advance_pct": Decimal("15.0"),
        "remaining_days": 45,
        "penalty_clause": "Late delivery penalty is agreed at 0.5% of total order value per week of delay.",
        "vat_separate": False, # H05: VAT not separately shown at 15%
        "arithmetic_error": True, # H06: Line totals / subtotal discrepancy
        "scanned": False,
        "expected_decision": "NEEDS_HUMAN_REVIEW",
        "expected_rule_ids": ["H05", "H06"]
    }
]

def build_pdf_document(pack, doc_type="quotation"):
    filename = f"{OUTPUT_DIR}/{pack['id'].lower()}_{doc_type}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )
    bold_style = ParagraphStyle(
        'DocBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    elements = []
    
    if doc_type == "quotation":
        # Header
        elements.append(Paragraph(f"<b>COMMERCIAL QUOTATION</b>", title_style))
        elements.append(Paragraph(f"<b>Quotation Reference:</b> QUO-{pack['id']}-2026 | <b>Date:</b> October 20, 2026<br/><b>Purchase Request Reference:</b> PR-2026-AGL-0089", subtitle_style))
        elements.append(Spacer(1, 8))
        
        # Supplier Details Table
        tin_str = pack['tin'] if pack['tin'] else "NOT SPECIFIED / UNREGISTERED"
        bin_str = pack['bin'] if pack['bin'] else "NOT SPECIFIED / UNREGISTERED"
        meta_data = [
            [Paragraph("<b>Supplier:</b>", bold_style), Paragraph(pack["supplier_name"], body_style),
             Paragraph("<b>Contact:</b>", bold_style), Paragraph(pack["contact_person"], body_style)],
            [Paragraph("<b>Address:</b>", bold_style), Paragraph(pack["reg_address"], body_style),
             Paragraph("<b>Quotation Validity:</b>", bold_style), Paragraph(f"Quotation validity is {pack['validity_days']} days from the date of issuance.", body_style)],
            [Paragraph("<b>Supplier TIN:</b>", bold_style), Paragraph(tin_str, body_style),
             Paragraph("<b>Supplier BIN:</b>", bold_style), Paragraph(bin_str, body_style)]
        ]
        meta_table = Table(meta_data, colWidths=[100, 180, 110, 150])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 14))
        
        # Items Table
        items_header = [Paragraph("<b>Item Code</b>", bold_style),
                        Paragraph("<b>Description</b>", bold_style),
                        Paragraph("<b>Quantity</b>", bold_style),
                        Paragraph("<b>Unit</b>", bold_style),
                        Paragraph("<b>Unit Price (BDT)</b>", bold_style),
                        Paragraph("<b>Line Total (BDT)</b>", bold_style)]
        table_rows = [items_header]
        
        subtotal = Decimal("0.00")
        for item in pack["items"]:
            line_tot = (Decimal(str(item["qty"])) * item["unit_price"]).quantize(Decimal("0.01"))
            subtotal += line_tot
            table_rows.append([
                Paragraph(item["code"], body_style),
                Paragraph(item["desc"], body_style),
                Paragraph(f"{item['qty']:,}", body_style),
                Paragraph(item["unit"], body_style),
                Paragraph(f"{item['unit_price']:.2f}", body_style),
                Paragraph(f"{line_tot:,.2f}", body_style)
            ])
            
        items_table = Table(table_rows, colWidths=[65, 175, 60, 50, 90, 100])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 10))
        
        # Financial Summary
        if pack["arithmetic_error"]:
            stated_subtotal = subtotal + Decimal("120000.00")
        else:
            stated_subtotal = subtotal
            
        vat_rate = Decimal("0.15")
        if pack["vat_separate"]:
            vat_amount = (stated_subtotal * vat_rate).quantize(Decimal("0.01"))
            grand_total = stated_subtotal + vat_amount
            summary_data = [
                [Paragraph("<b>Subtotal (Excl. VAT):</b>", body_style), Paragraph(f"BDT {stated_subtotal:,.2f}", bold_style)],
                [Paragraph("<b>Applicable VAT (15% separately itemized):</b>", body_style), Paragraph(f"BDT {vat_amount:,.2f}", bold_style)],
                [Paragraph("<b>Total Quoted Value (Incl. VAT):</b>", bold_style), Paragraph(f"BDT {grand_total:,.2f}", bold_style)],
            ]
        else:
            grand_total = stated_subtotal
            summary_data = [
                [Paragraph("<b>Total Quoted Value (All-inclusive, VAT not separated):</b>", bold_style), Paragraph(f"BDT {grand_total:,.2f}", bold_style)],
                [Paragraph("<b>VAT Note:</b>", body_style), Paragraph("Prices inclusive of all local taxes, VAT not separately itemized.", body_style)],
            ]
            
        summary_table = Table(summary_data, colWidths=[240, 160], hAlign='RIGHT')
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 14))
        
        # Quotation Terms
        elements.append(Paragraph(f"<b>Delivery Terms:</b> Promised delivery within {pack['delivery_days']} days from purchase order date.", body_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"<b>Quotation Validity:</b> Quotation validity is {pack['validity_days']} days from the date of submission.", body_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"<b>Payment Terms:</b> {pack['advance_pct']}% advance upon contract, remainder payable {pack['remaining_days']} days after delivery.", body_style))
        
    else:
        # Contract Document
        elements.append(Paragraph(f"<b>SUPPLY AGREEMENT AND GENERAL CONDITIONS</b>", title_style))
        elements.append(Paragraph(f"<b>Agreement No:</b> AGR-{pack['id']}-2026 | <b>Reference PR:</b> PR-2026-AGL-0089<br/><b>Buyer:</b> Aamar Garments Ltd | <b>Supplier:</b> {pack['supplier_name']}", subtitle_style))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("<b>ARTICLE 1: PARTIES AND RECITALS</b>", bold_style))
        elements.append(Paragraph(
            f"This Supply Agreement is entered into between Aamar Garments Ltd (Buyer) and {pack['supplier_name']} (Supplier), "
            f"having its registered office at {pack['reg_address']}, holding TIN {pack['tin'] or 'UNSPECIFIED'} and BIN {pack['bin'] or 'UNSPECIFIED'}.",
            body_style
        ))
        elements.append(Spacer(1, 8))
        
        elements.append(Paragraph("<b>ARTICLE 2: DELIVERY SCHEDULE</b>", bold_style))
        elements.append(Paragraph(
            f"The Supplier shall deliver the complete order within {pack['delivery_days']} days from the purchase order issuance date.",
            body_style
        ))
        elements.append(Spacer(1, 8))
        
        elements.append(Paragraph("<b>ARTICLE 3: PAYMENT TERMS</b>", bold_style))
        elements.append(Paragraph(
            f"Buyer shall pay an advance payment of {pack['advance_pct']}% of the total order value upon execution of this contract. "
            f"The remaining payment of {100 - pack['advance_pct']}% shall be settled within {pack['remaining_days']} days after delivery of all goods in satisfactory condition.",
            body_style
        ))
        elements.append(Spacer(1, 8))
        
        elements.append(Paragraph("<b>ARTICLE 4: LATE DELIVERY PENALTY AND LIQUIDATED DAMAGES</b>", bold_style))
        elements.append(Paragraph(pack["penalty_clause"], body_style))
        elements.append(Spacer(1, 8))
        
        elements.append(Paragraph("<b>ARTICLE 5: TAXES AND VAT COMPLIANCE</b>", bold_style))
        if pack["vat_separate"]:
            elements.append(Paragraph(
                "VAT is applicable at the statutory rate of 15% and is separately shown on all commercial invoices and tax challans.",
                body_style
            ))
        else:
            elements.append(Paragraph(
                "All contractual prices are inclusive of all taxes. VAT is not separately shown.",
                body_style
            ))
        elements.append(Spacer(1, 8))
        
        elements.append(Paragraph("<b>ARTICLE 6: EXECUTION & SIGNATURES</b>", bold_style))
        elements.append(Paragraph(f"Signed for and on behalf of Supplier by {pack['contact_person']}. Signed for Buyer by Procurement Directorate, Aamar Garments Ltd.", body_style))
        
    doc.build(elements)
    
    # If document represents a scanned document, embed raster scan layer
    if pack.get("scanned", False) and doc_type == "quotation":
        import pymupdf
        scan_doc = pymupdf.open(filename)
        for page in scan_doc:
            pix = page.get_pixmap(dpi=150)
            page.insert_image(page.rect, stream=pix.tobytes("png"))
        tmp_name = filename + ".tmp.pdf"
        scan_doc.save(tmp_name)
        scan_doc.close()
        os.replace(tmp_name, filename)
        
    print(f"Generated: {filename}")

def main():
    print("Generating 10 Supplier Quotations and 10 Contracts...")
    for pack in PACKS_DATA:
        build_pdf_document(pack, "quotation")
        build_pdf_document(pack, "contract")
    print("All 20 documents successfully generated in data/input/")

if __name__ == "__main__":
    main()
