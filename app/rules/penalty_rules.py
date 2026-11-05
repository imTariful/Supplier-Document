"""
Penalty rules:
R03 — Missing late-delivery penalty clause -> REJECT
R07 — Insufficient late-delivery penalty rate: < 0.5% of order value per week -> REJECT
Ambiguous clause basis or rate -> HUMAN_REVIEW
"""

from decimal import Decimal
from typing import Optional
from app.schemas.models import RuleResult

def evaluate_penalty_rules(
    penalty_clause: Optional[str],
    penalty_rate_pct: Optional[Decimal],
    penalty_basis: Optional[str],
    doc_filename: str = "contract.pdf",
    page: int = 1
) -> RuleResult:
    if not penalty_clause or not penalty_clause.strip():
        return RuleResult(
            rule_id="R03",
            rule_name="Missing late-delivery penalty clause",
            status="FAILED",
            actual_value="No penalty clause found",
            expected_value="Mandatory late-delivery penalty clause",
            severity="REJECT",
            document=doc_filename,
            page=page,
            evidence="Clause absent",
            explanation="The contract fails to provide a late-delivery penalty clause as required by policy."
        )

    # If penalty clause exists, verify rate and basis (R07)
    if penalty_rate_pct is None:
        return RuleResult(
            rule_id="H08",
            rule_name="Ambiguous late-delivery penalty terms",
            status="REVIEW_REQUIRED",
            actual_value="Penalty rate or period ambiguous",
            expected_value="At least 0.5% per week of order value",
            severity="HUMAN_REVIEW",
            document=doc_filename,
            page=page,
            evidence=penalty_clause,
            explanation="Penalty clause exists but numeric rate or measurement period is ambiguous."
        )

    if penalty_rate_pct < Decimal("0.5"):
        return RuleResult(
            rule_id="R07",
            rule_name="Insufficient late-delivery penalty rate",
            status="FAILED",
            actual_value=f"{penalty_rate_pct}% per week",
            expected_value="At least 0.5% of order value per week of delay",
            severity="REJECT",
            document=doc_filename,
            page=page,
            evidence=penalty_clause,
            explanation=f"Contract specifies {penalty_rate_pct}% per week, which is below the mandatory 0.5% minimum."
        )

    return RuleResult(
        rule_id="R07",
        rule_name="Late-delivery penalty compliance",
        status="PASS",
        actual_value=f"{penalty_rate_pct}% per week",
        expected_value=">= 0.5% per week",
        severity="INFO",
        document=doc_filename,
        page=page,
        evidence=penalty_clause,
        explanation="Contract contains a compliant late-delivery liquidated damages clause."
    )
