"""
Aamar Garments Ltd — 10-Document Challenge Evaluation Engine.
Processes all 10 supplier packs through the LangGraph workflow, compares against
independently verified ground-truth.csv, computes comprehensive classification metrics,
and exports all required evaluation reports (PDF, CSV, PNG confusion matrix, JSON).
"""

import os
import csv
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, List, Any
from decimal import Decimal

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

import sys
sys.path.insert(0, ".")
from app.workflow.graph import build_verification_workflow
from app.services.pr_service import PurchaseRequestService

GROUND_TRUTH_PATH = "evaluation/ground_truth.csv"
OUTPUT_DIR = "outputs/reports"
JSON_OUTPUT_DIR = "outputs/json"
CSV_OUTPUT_DIR = "outputs/csv"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(JSON_OUTPUT_DIR, exist_ok=True)
os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)

def load_ground_truth() -> Dict[str, Dict[str, Any]]:
    gt = {}
    with open(GROUND_TRUTH_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["supplier_id"].strip()
            gt[sid] = {
                "supplier_id": sid,
                "expected_decision": row["expected_decision"].strip(),
                "expected_rule_ids": [r.strip() for r in row["expected_rule_ids"].split("|") if r.strip()],
                "verified_by": row.get("verified_by", "Auditor"),
                "verification_notes": row.get("verification_notes", "")
            }
    return gt

def plot_confusion_matrix(matrix: Dict[str, Dict[str, int]], labels: List[str], save_path: str):
    fig, ax = plt.subplots(figsize=(6, 5), dpi=300)
    data = [[matrix[true_lbl].get(pred_lbl, 0) for pred_lbl in labels] for true_lbl in labels]
    
    cax = ax.matshow(data, cmap="Blues")
    fig.colorbar(cax)
    
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="left", fontsize=9, fontweight='bold')
    ax.set_yticklabels(labels, fontsize=9, fontweight='bold')
    
    for i in range(len(labels)):
        for j in range(len(labels)):
            val = data[i][j]
            ax.text(j, i, str(val), ha="center", va="center", color="white" if val > 2 else "black", fontsize=11, fontweight='bold')
            
    plt.title("Aamar Garments — Evaluation Confusion Matrix\n(10 Supplier Packs Ground Truth vs Prediction)", fontsize=11, pad=20, fontweight='bold')
    plt.xlabel("Predicted Decision", fontsize=10, labelpad=10)
    plt.ylabel("Expected Decision (Ground Truth)", fontsize=10)
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

def generate_pdf_evaluation_report(results: List[Dict[str, Any]], summary: Dict[str, Any], pdf_path: str, cm_image_path: str):
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'RepTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'RepSub',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14
    )
    bold_style = ParagraphStyle(
        'RepBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11
    )
    body_style = ParagraphStyle(
        'RepBody',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e293b")
    )
    
    elements = []
    
    # Title
    elements.append(Paragraph("Aamar Garments Ltd — Supplier Verification Evaluation Report", title_style))
    elements.append(Paragraph(
        f"<b>Audit Date:</b> 2026-11-03 | <b>Purchase Request:</b> PR-2026-AGL-0089<br/>"
        f"<b>Workflow:</b> Deterministic LangGraph Pipeline + Python Decimal Rule Engine | <b>Target:</b> 10 Supplier Packs",
        subtitle_style
    ))
    elements.append(Spacer(1, 10))
    
    # KPI Cards Table
    kpi_data = [
        [
            Paragraph("<b>Overall Accuracy</b>", bold_style),
            Paragraph("<b>False Approvals</b>", bold_style),
            Paragraph("<b>Total Evaluated</b>", bold_style),
            Paragraph("<b>Correct Decisions</b>", bold_style)
        ],
        [
            Paragraph(f"<font size=14 color='#16a34a'><b>{summary['accuracy']:.1f}%</b></font>", body_style),
            Paragraph(f"<font size=14 color='#dc2626'><b>{summary['false_approval_rate']:.1f}% ({summary['false_approvals']})</b></font>", body_style),
            Paragraph(f"<font size=14><b>{summary['total_evaluated']}</b></font>", body_style),
            Paragraph(f"<font size=14 color='#2563eb'><b>{summary['correct_decisions']} / {summary['total_evaluated']}</b></font>", body_style)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[130, 130, 130, 130])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 14))
    
    # Detailed Decision Table
    elements.append(Paragraph("<b>10-Document Challenge Detailed Verification Matrix</b>", ParagraphStyle('H2', parent=styles['Heading2'], fontSize=12, leading=15)))
    elements.append(Spacer(1, 6))
    
    table_headers = [
        Paragraph("<b>Supplier ID</b>", bold_style),
        Paragraph("<b>Supplier Name</b>", bold_style),
        Paragraph("<b>Expected (Ground Truth)</b>", bold_style),
        Paragraph("<b>Predicted Decision</b>", bold_style),
        Paragraph("<b>Triggered Rules</b>", bold_style),
        Paragraph("<b>Match</b>", bold_style)
    ]
    doc_rows = [table_headers]
    for r in results:
        match_color = "#16a34a" if r["is_correct"] else "#dc2626"
        match_text = f"<font color='{match_color}'><b>{'CORRECT' if r['is_correct'] else 'MISMATCH'}</b></font>"
        doc_rows.append([
            Paragraph(r["supplier_id"], body_style),
            Paragraph(r["supplier_name"], body_style),
            Paragraph(r["expected_decision"], body_style),
            Paragraph(r["actual_decision"], body_style),
            Paragraph(", ".join(r["triggered_rule_ids"]) if r["triggered_rule_ids"] else "None (Approved)", body_style),
            Paragraph(match_text, body_style)
        ])
        
    doc_table = Table(doc_rows, colWidths=[65, 145, 95, 95, 80, 60])
    doc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(doc_table)
    elements.append(Spacer(1, 14))
    
    # Class-wise Breakdown
    elements.append(Paragraph("<b>Class-wise Evaluation & Confusion Matrix</b>", ParagraphStyle('H3', parent=styles['Heading2'], fontSize=12, leading=15)))
    elements.append(Spacer(1, 6))
    
    if os.path.exists(cm_image_path):
        elements.append(RLImage(cm_image_path, width=320, height=260))
        
    doc.build(elements)
    print(f"Generated PDF evaluation report at: {pdf_path}")

def run_evaluation() -> Dict[str, Any]:
    print("=" * 60)
    print("RUNNING 10-DOCUMENT CHALLENGE EVALUATION WORKFLOW")
    print("=" * 60)

    gt_data = load_ground_truth()
    workflow = build_verification_workflow()
    pr_items = PurchaseRequestService.load_purchase_request()

    labels = ["APPROVE", "REJECT", "NEEDS_HUMAN_REVIEW"]
    confusion_matrix = {t: {p: 0 for p in labels} for t in labels}

    results: List[Dict[str, Any]] = []
    correct_count = 0
    false_approvals = 0

    supplier_packs = sorted(list(gt_data.keys()))

    for sid in supplier_packs:
        expected = gt_data[sid]
        q_path = f"data/input/{sid.lower()}_quotation.pdf"
        c_path = f"data/input/{sid.lower()}_contract.pdf"

        # Execute LangGraph Workflow
        state_input = {
            "supplier_id": sid,
            "quotation_path": q_path,
            "contract_path": c_path,
            "purchase_request_items": pr_items
        }

        workflow_out = workflow.invoke(state_input)
        actual_decision = workflow_out.get("final_decision", "NEEDS_HUMAN_REVIEW")
        sup_name = workflow_out.get("supplier_name", sid)
        rule_results = workflow_out.get("rule_results", [])
        evidence_records = workflow_out.get("evidence_records", [])

        # Extract triggered rule IDs
        triggered_ids = [r.rule_id for r in rule_results if r.status in ("FAILED", "REVIEW_REQUIRED")]
        triggered_ids = sorted(list(set(triggered_ids)))

        expected_decision = expected["expected_decision"]
        is_correct = (actual_decision == expected_decision)
        if is_correct:
            correct_count += 1

        if actual_decision == "APPROVE" and expected_decision != "APPROVE":
            false_approvals += 1

        confusion_matrix[expected_decision][actual_decision] += 1

        res_record = {
            "supplier_id": sid,
            "supplier_name": sup_name,
            "expected_decision": expected_decision,
            "actual_decision": actual_decision,
            "is_correct": is_correct,
            "expected_rule_ids": expected["expected_rule_ids"],
            "triggered_rule_ids": triggered_ids,
            "evidence_count": len(evidence_records),
            "evidence_records": [e.model_dump() for e in evidence_records],
            "comparison_results": workflow_out.get("comparison_results", []),
            "all_rule_results": [r.model_dump() for r in rule_results],
            "structured_quotation": {
                "subtotal": float(workflow_out["structured_quotation"].subtotal) if workflow_out.get("structured_quotation") and workflow_out["structured_quotation"].subtotal else None,
                "vat_amount": float(workflow_out["structured_quotation"].vat_amount) if workflow_out.get("structured_quotation") and workflow_out["structured_quotation"].vat_amount else None,
                "grand_total": float(workflow_out["structured_quotation"].grand_total) if workflow_out.get("structured_quotation") and workflow_out["structured_quotation"].grand_total else None,
                "delivery_days": workflow_out["structured_quotation"].delivery_days if workflow_out.get("structured_quotation") else None,
                "validity_days": workflow_out["structured_quotation"].validity_days if workflow_out.get("structured_quotation") else None,
                "items": [it.model_dump(mode="json") for it in workflow_out["structured_quotation"].items] if workflow_out.get("structured_quotation") else []
            } if workflow_out.get("structured_quotation") else None,
            "verification_notes": expected["verification_notes"]
        }
        results.append(res_record)

        print(f"[{'PASS' if is_correct else 'FAIL'}] {sid} | Expected: {expected_decision:<18} | Actual: {actual_decision:<18} | Rules: {', '.join(triggered_ids)}")

    total_evaluated = len(results)
    accuracy = (correct_count / total_evaluated * 100.0) if total_evaluated > 0 else 0.0
    false_approval_rate = (false_approvals / total_evaluated * 100.0) if total_evaluated > 0 else 0.0

    # Counts by class
    approved_count = sum(1 for r in results if r["actual_decision"] == "APPROVE")
    rejected_count = sum(1 for r in results if r["actual_decision"] == "REJECT")
    review_count = sum(1 for r in results if r["actual_decision"] == "NEEDS_HUMAN_REVIEW")

    summary = {
        "total_evaluated": total_evaluated,
        "correct_decisions": correct_count,
        "incorrect_decisions": total_evaluated - correct_count,
        "accuracy": accuracy,
        "false_approvals": false_approvals,
        "false_approval_rate": false_approval_rate,
        "number_approved": approved_count,
        "number_rejected": rejected_count,
        "number_requiring_human_review": review_count,
        "processing_failures": 0,
        "unresolved_cases": 0,
        "confusion_matrix": confusion_matrix
    }

    # 1. Save JSON
    json_path = f"{OUTPUT_DIR}/evaluation_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    # Also save to outputs/json
    with open(f"{JSON_OUTPUT_DIR}/evaluation_summary.json", "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    # 2. Save CSV
    csv_path = f"{OUTPUT_DIR}/evaluation_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "supplier_id", "supplier_name", "expected_decision", "actual_decision",
            "is_correct", "triggered_rule_ids", "evidence_count", "verification_notes"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "supplier_id": r["supplier_id"],
                "supplier_name": r["supplier_name"],
                "expected_decision": r["expected_decision"],
                "actual_decision": r["actual_decision"],
                "is_correct": r["is_correct"],
                "triggered_rule_ids": "|".join(r["triggered_rule_ids"]),
                "evidence_count": r["evidence_count"],
                "verification_notes": r["verification_notes"]
            })
    with open(f"{CSV_OUTPUT_DIR}/evaluation_results.csv", "w", newline="", encoding="utf-8") as f:
        with open(csv_path, "r", encoding="utf-8") as rf:
            f.write(rf.read())

    # 3. Generate Confusion Matrix PNG
    cm_path = f"{OUTPUT_DIR}/confusion_matrix.png"
    plot_confusion_matrix(confusion_matrix, labels, cm_path)

    # 4. Generate PDF Report
    pdf_path = f"{OUTPUT_DIR}/evaluation_report.pdf"
    generate_pdf_evaluation_report(results, summary, pdf_path, cm_path)

    print("\n" + "=" * 60)
    print(f"EVALUATION COMPLETE: {correct_count}/{total_evaluated} CORRECT ({accuracy:.1f}% ACCURACY)")
    print(f"FALSE APPROVALS: {false_approvals} ({false_approval_rate:.1f}%)")
    print(f"Approved: {approved_count} | Rejected: {rejected_count} | Human Review: {review_count}")
    print("=" * 60)

    return summary

if __name__ == "__main__":
    run_evaluation()
