"""
Delivery rules:
R06 — Excessive delivery period: delivery > 45 days -> REJECT
H04 — Delivery period: 31 <= delivery <= 45 days -> HUMAN_REVIEW
Boundary:
- <= 30 days: PASS
- 31–45 days: HUMAN REVIEW
- Exactly 45 days: HUMAN REVIEW
- Exactly 46 days: REJECT
"""

from typing import Optional
from app.schemas.models import RuleResult

def evaluate_delivery_rules(
    delivery_days: Optional[int],
    doc_filename: str = "contract.pdf",
    page: int = 1,
    evidence_text: str = ""
) -> RuleResult:
    if delivery_days is None:
        return RuleResult(
            rule_id="H08",
            rule_name="Uncertain delivery period",
            status="REVIEW_REQUIRED",
            actual_value="Not specified",
            expected_value="<= 30 days (max 45 days with approval)",
            severity="HUMAN_REVIEW",
            document=doc_filename,
            page=page,
            evidence=evidence_text,
            explanation="Delivery period is missing or could not be established."
        )

    if delivery_days > 45:
        return RuleResult(
            rule_id="R06",
            rule_name="Excessive delivery period",
            status="FAILED",
            actual_value=f"{delivery_days} days",
            expected_value="Not more than 45 days",
            severity="REJECT",
            document=doc_filename,
            page=page,
            evidence=evidence_text or f"Delivery period: {delivery_days} days",
            explanation=f"Promised delivery of {delivery_days} days violates company procurement ceiling of 45 days."
        )

    if delivery_days > 30:
        return RuleResult(
            rule_id="H04",
            rule_name="Delivery period requiring review",
            status="REVIEW_REQUIRED",
            actual_value=f"{delivery_days} days",
            expected_value="30 days or less for standard approval",
            severity="HUMAN_REVIEW",
            document=doc_filename,
            page=page,
            evidence=evidence_text or f"Delivery period: {delivery_days} days",
            explanation=f"Promised delivery of {delivery_days} days is within 31 to 45 days, requiring commercial review."
        )

    return RuleResult(
        rule_id="R06",
        rule_name="Delivery period",
        status="PASS",
        actual_value=f"{delivery_days} days",
        expected_value="<= 30 days",
        severity="INFO",
        document=doc_filename,
        page=page,
        evidence=evidence_text or f"Delivery period: {delivery_days} days",
        explanation=f"Delivery timeline of {delivery_days} days meets target schedule."
    )
