"""
Quotation validity rules:
H07 — Quotation validity: validity < 30 days -> HUMAN_REVIEW
Boundary: 30 days or greater: PASS.
"""

from typing import Optional
from app.schemas.models import RuleResult

def evaluate_validity_rules(
    validity_days: Optional[int],
    doc_filename: str = "quotation.pdf",
    page: int = 1,
    evidence_text: str = ""
) -> RuleResult:
    if validity_days is None:
        return RuleResult(
            rule_id="H08",
            rule_name="Uncertain quotation validity",
            status="REVIEW_REQUIRED",
            actual_value="Not specified",
            expected_value="At least 30 days",
            severity="HUMAN_REVIEW",
            document=doc_filename,
            page=page,
            evidence=evidence_text,
            explanation="Quotation validity period is absent or could not be verified."
        )

    if validity_days < 30:
        return RuleResult(
            rule_id="H07",
            rule_name="Quotation validity less than 30 days",
            status="REVIEW_REQUIRED",
            actual_value=f"{validity_days} days",
            expected_value="At least 30 days",
            severity="HUMAN_REVIEW",
            document=doc_filename,
            page=page,
            evidence=evidence_text or f"Validity: {validity_days} days",
            explanation=f"Quotation is valid for only {validity_days} days, risking price expiration during procurement review."
        )

    return RuleResult(
        rule_id="H07",
        rule_name="Quotation validity",
        status="PASS",
        actual_value=f"{validity_days} days",
        expected_value=">= 30 days",
        severity="INFO",
        document=doc_filename,
        page=page,
        evidence=evidence_text or f"Validity: {validity_days} days",
        explanation="Quotation validity meets the mandatory 30-day minimum."
    )
