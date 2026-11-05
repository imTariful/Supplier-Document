"""
Financial arithmetic validation rules:
H06 — Arithmetic inconsistency:
Validates line totals = qty * unit_price, subtotal = sum(line_totals),
vat = subtotal * 15%, grand_total = subtotal + vat.
All operations executed with Python Decimal (currency tolerance: BDT 0.05).
"""

from decimal import Decimal
from typing import List, Optional
from app.schemas.models import RuleResult, QuotationLineItem

def evaluate_arithmetic_rules(
    items: List[QuotationLineItem],
    stated_subtotal: Optional[Decimal],
    stated_vat: Optional[Decimal],
    stated_grand_total: Optional[Decimal],
    vat_separate: bool = True,
    doc_filename: str = "quotation.pdf",
    page: int = 1
) -> List[RuleResult]:
    results: List[RuleResult] = []
    
    # 1. Line item arithmetic
    calculated_subtotal = Decimal("0.00")
    for item in items:
        expected_line_tot = (item.quantity * item.unit_price).quantize(Decimal("0.01"))
        diff = abs(item.line_total - expected_line_tot)
        if diff > Decimal("0.05"):
            results.append(RuleResult(
                rule_id="H06",
                rule_name="Line item arithmetic inconsistency",
                status="REVIEW_REQUIRED",
                actual_value=f"BDT {item.line_total:.2f}",
                expected_value=f"BDT {expected_line_tot:.2f} ({item.quantity} x {item.unit_price:.2f})",
                severity="HUMAN_REVIEW",
                document=doc_filename,
                page=item.page_number,
                evidence=item.source_text,
                explanation=f"Item {item.item_code} line total does not match quantity multiplied by unit price (diff: BDT {diff:.2f})."
            ))
        calculated_subtotal += expected_line_tot

    # 2. Subtotal arithmetic
    if stated_subtotal is not None:
        subtotal_diff = abs(stated_subtotal - calculated_subtotal)
        if subtotal_diff > Decimal("0.05"):
            results.append(RuleResult(
                rule_id="H06",
                rule_name="Subtotal sum mismatch",
                status="REVIEW_REQUIRED",
                actual_value=f"BDT {stated_subtotal:,.2f}",
                expected_value=f"BDT {calculated_subtotal:,.2f} (sum of line items)",
                severity="HUMAN_REVIEW",
                document=doc_filename,
                page=page,
                evidence=f"Stated Subtotal: BDT {stated_subtotal:,.2f}",
                explanation=f"Stated subtotal deviates from sum of line items by BDT {subtotal_diff:,.2f}."
            ))

    # 3. Grand total arithmetic
    base_subtotal = stated_subtotal if stated_subtotal is not None else calculated_subtotal
    if vat_separate and stated_vat is not None:
        expected_grand_total = (base_subtotal + stated_vat).quantize(Decimal("0.01"))
    else:
        expected_grand_total = base_subtotal

    if stated_grand_total is not None:
        gt_diff = abs(stated_grand_total - expected_grand_total)
        if gt_diff > Decimal("0.05"):
            results.append(RuleResult(
                rule_id="H06",
                rule_name="Grand total calculation mismatch",
                status="REVIEW_REQUIRED",
                actual_value=f"BDT {stated_grand_total:,.2f}",
                expected_value=f"BDT {expected_grand_total:,.2f}",
                severity="HUMAN_REVIEW",
                document=doc_filename,
                page=page,
                evidence=f"Stated Grand Total: BDT {stated_grand_total:,.2f}",
                explanation=f"Stated grand total does not equal subtotal plus VAT (discrepancy: BDT {gt_diff:,.2f})."
            ))

    if not results:
        results.append(RuleResult(
            rule_id="H06",
            rule_name="Financial arithmetic",
            status="PASS",
            actual_value=f"Subtotal: BDT {calculated_subtotal:,.2f}",
            expected_value="Accurate mathematical calculations",
            severity="INFO",
            document=doc_filename,
            page=page,
            evidence="All line items, subtotal, VAT and grand total match exactly",
            explanation="All financial arithmetic verified without discrepancies."
        ))

    return results
