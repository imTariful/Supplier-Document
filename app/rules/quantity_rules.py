"""
Quantity rules:
H02 — Quantity deviation: quantity_deviation > 5% -> HUMAN_REVIEW
Formula: quantity_deviation = abs(quoted_quantity - requested_quantity) / requested_quantity * 100
Boundary: Deviation of exactly 5% does not trigger review.
"""

from decimal import Decimal
from typing import List, Dict
from app.schemas.models import RuleResult, QuotationLineItem, PurchaseRequestItem

def evaluate_quantity_rules(
    quoted_items: List[QuotationLineItem],
    pr_items: Dict[str, PurchaseRequestItem],
    doc_filename: str = "quotation.pdf"
) -> List[RuleResult]:
    results: List[RuleResult] = []

    for item in quoted_items:
        pr_item = pr_items.get(item.item_code)
        if not pr_item:
            continue

        req_qty = pr_item.quantity
        quo_qty = item.quantity

        deviation = (abs(quo_qty - req_qty) / req_qty) * Decimal("100")

        if deviation > Decimal("5.0"):
            results.append(RuleResult(
                rule_id="H02",
                rule_name="Quantity deviation",
                status="REVIEW_REQUIRED",
                actual_value=f"{quo_qty} {item.unit} ({deviation:.2f}% diff)",
                expected_value=f"{req_qty} {pr_item.unit} (within +/- 5%)",
                severity="HUMAN_REVIEW",
                document=doc_filename,
                page=item.page_number,
                evidence=item.source_text or f"{item.item_code} Qty: {quo_qty}",
                explanation=f"{item.item_code} quoted quantity {quo_qty} diverges from requested quantity {req_qty} by {deviation:.2f}% (> 5%)."
            ))
        else:
            results.append(RuleResult(
                rule_id="H02",
                rule_name="Quantity deviation",
                status="PASS",
                actual_value=f"{quo_qty} {item.unit}",
                expected_value=f"{req_qty} {pr_item.unit} (+/- 5%)",
                severity="INFO",
                document=doc_filename,
                page=item.page_number,
                evidence=item.source_text or f"{item.item_code} Qty: {quo_qty}",
                explanation=f"{item.item_code} quoted quantity is compliant with purchase request."
            ))

    return results
