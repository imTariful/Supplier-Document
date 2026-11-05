"""
Advance payment rules:
R02 — Excessive advance payment: advance > 20% -> REJECT
Boundary: 20% passes, 20.01% rejects.
"""

from decimal import Decimal
from typing import Optional
from app.schemas.models import RuleResult

def evaluate_advance_rules(
    advance_pct: Optional[Decimal],
    doc_filename: str = "contract.pdf",
    page: int = 1,
    evidence_text: str = ""
) -> RuleResult:
    if advance_pct is None:
        return RuleResult(
            rule_id="H08",
            rule_name="Uncertain advance payment terms",
            status="REVIEW_REQUIRED",
            actual_value="Not specified",
            expected_value="Advance <= 20%",
            severity="HUMAN_REVIEW",
            document=doc_filename,
            page=page,
            evidence=evidence_text,
            explanation="Advance payment percentage could not be extracted from document."
        )

    if advance_pct > Decimal("20.0"):
        return RuleResult(
            rule_id="R02",
            rule_name="Excessive advance payment",
            status="FAILED",
            actual_value=f"{advance_pct}%",
            expected_value="Not more than 20%",
            severity="REJECT",
            document=doc_filename,
            page=page,
            evidence=evidence_text or f"Advance payment: {advance_pct}%",
            explanation=f"Demanded advance payment of {advance_pct}% exceeds the allowable company limit of 20%."
        )

    return RuleResult(
        rule_id="R02",
        rule_name="Excessive advance payment",
        status="PASS",
        actual_value=f"{advance_pct}%",
        expected_value="<= 20%",
        severity="INFO",
        document=doc_filename,
        page=page,
        evidence=evidence_text or f"Advance payment: {advance_pct}%",
        explanation=f"Advance payment of {advance_pct}% complies with company procurement policy."
    )
