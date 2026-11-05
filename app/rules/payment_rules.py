"""
Payment terms rules:
H03 — Payment terms: unclear or outside 30 to 60 days after delivery -> HUMAN_REVIEW
The remaining payment deadline must be clearly stated and measured from delivery.
"""

from typing import Optional
from app.schemas.models import RuleResult

def evaluate_payment_terms_rules(
    remaining_days: Optional[int],
    doc_filename: str = "contract.pdf",
    page: int = 1,
    evidence_text: str = ""
) -> RuleResult:
    if remaining_days is None:
        return RuleResult(
            rule_id="H03",
            rule_name="Unclear payment terms",
            status="REVIEW_REQUIRED",
            actual_value="Unspecified or ambiguous reference date",
            expected_value="Clearly stated remaining payment 30 to 60 days after delivery",
            severity="HUMAN_REVIEW",
            document=doc_filename,
            page=page,
            evidence=evidence_text,
            explanation="Payment terms do not clearly establish a payment window tied to delivery."
        )

    if remaining_days < 30 or remaining_days > 60:
        return RuleResult(
            rule_id="H03",
            rule_name="Payment terms outside allowable window",
            status="REVIEW_REQUIRED",
            actual_value=f"{remaining_days} days after delivery",
            expected_value="30 to 60 days after delivery",
            severity="HUMAN_REVIEW",
            document=doc_filename,
            page=page,
            evidence=evidence_text or f"Remaining payment: {remaining_days} days after delivery",
            explanation=f"Remaining payment deadline of {remaining_days} days is outside the standard 30–60 days window."
        )

    return RuleResult(
        rule_id="H03",
        rule_name="Payment terms",
        status="PASS",
        actual_value=f"{remaining_days} days after delivery",
        expected_value="30 to 60 days after delivery",
        severity="INFO",
        document=doc_filename,
        page=page,
        evidence=evidence_text or f"Remaining payment: {remaining_days} days after delivery",
        explanation="Payment terms are fully compliant with company procurement guidelines."
    )
