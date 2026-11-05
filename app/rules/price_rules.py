"""
Price rules:
R01 — Excessive unit price: price_deviation > 3% -> REJECT
H01 — Minor price deviation: 0% < price_deviation <= 3% -> HUMAN_REVIEW
Formula: price_deviation = ((quoted_price - maximum_price) / maximum_price) * 100
"""

from decimal import Decimal
from typing import List, Dict
from app.schemas.models import RuleResult, QuotationLineItem, PurchaseRequestItem

def evaluate_price_rules(
    quoted_items: List[QuotationLineItem],
    pr_items: Dict[str, PurchaseRequestItem],
    doc_filename: str = "quotation.pdf"
) -> List[RuleResult]:
    results: List[RuleResult] = []

    for item in quoted_items:
        pr_item = pr_items.get(item.item_code)
        if not pr_item:
            results.append(RuleResult(
                rule_id="H08",
                rule_name="Unmatched item code",
                status="REVIEW_REQUIRED",
                actual_value=item.item_code,
                expected_value="Known purchase request item",
                severity="HUMAN_REVIEW",
                document=doc_filename,
                page=item.page_number,
                evidence=item.source_text or item.description,
                explanation=f"Item code {item.item_code} was not found in authoritative purchase request."
            ))
            continue

        quoted_price = item.unit_price
        max_price = pr_item.max_unit_price

        # Formula: price_deviation = ((quoted_price - maximum_price) / maximum_price) * 100
        deviation = ((quoted_price - max_price) / max_price) * Decimal("100")

        # Boundary rules:
        # Price <= maximum: PASS
        # Price > maximum and deviation <= 3.0: HUMAN_REVIEW (H01)
        # Price > maximum and deviation > 3.0: REJECT (R01)
        # Exactly 3%: HUMAN_REVIEW
        if deviation > Decimal("3.0"):
            results.append(RuleResult(
                rule_id="R01",
                rule_name="Excessive unit price",
                status="FAILED",
                actual_value=f"BDT {quoted_price:.2f} (+{deviation:.2f}%)",
                expected_value=f"Not more than BDT {max_price * Decimal('1.03'):.2f} (<= +3.0%)",
                severity="REJECT",
                document=doc_filename,
                page=item.page_number,
                evidence=item.source_text or f"{item.item_code}: BDT {quoted_price:.2f}",
                explanation=f"{item.item_code} ({item.description}) quoted at BDT {quoted_price:.2f}, exceeding max BDT {max_price:.2f} by {deviation:.2f}% (> 3%)."
            ))
        elif deviation > Decimal("0.0"):
            results.append(RuleResult(
                rule_id="H01",
                rule_name="Minor price deviation",
                status="REVIEW_REQUIRED",
                actual_value=f"BDT {quoted_price:.2f} (+{deviation:.2f}%)",
                expected_value=f"BDT {max_price:.2f} or below",
                severity="HUMAN_REVIEW",
                document=doc_filename,
                page=item.page_number,
                evidence=item.source_text or f"{item.item_code}: BDT {quoted_price:.2f}",
                explanation=f"{item.item_code} ({item.description}) quoted at BDT {quoted_price:.2f}, within minor deviation tolerance of +3% (+{deviation:.2f}%)."
            ))
        else:
            results.append(RuleResult(
                rule_id="R01",
                rule_name="Excessive unit price",
                status="PASS",
                actual_value=f"BDT {quoted_price:.2f}",
                expected_value=f"<= BDT {max_price:.2f}",
                severity="INFO",
                document=doc_filename,
                page=item.page_number,
                evidence=item.source_text or f"{item.item_code}: BDT {quoted_price:.2f}",
                explanation=f"{item.item_code} quoted unit price is within maximum allowable ceiling."
            ))

    return results
