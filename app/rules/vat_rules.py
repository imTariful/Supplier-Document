"""
VAT compliance rules:
H05 — VAT: VAT is not separately shown at 15% -> HUMAN_REVIEW
Verify the VAT rate, VAT amount, and separate presentation.
"""

from decimal import Decimal
from typing import Optional
from app.schemas.models import RuleResult

def evaluate_vat_rules(
    vat_separate: bool,
    subtotal: Optional[Decimal],
    vat_amount: Optional[Decimal],
    doc_filename: str = "quotation.pdf",
    page: int = 1,
    evidence_text: str = ""
) -> RuleResult:
    if not vat_separate:
        return RuleResult(
            rule_id="H05",
            rule_name="VAT presentation non-compliant",
            status="REVIEW_REQUIRED",
            actual_value="VAT not separately itemized at 15%",
            expected_value="VAT separately itemized at statutory 15%",
            severity="HUMAN_REVIEW",
            document=doc_filename,
            page=page,
            evidence=evidence_text or "VAT not separately itemized",
            explanation="Statutory 15% VAT is not separately broken down on quotation or contract."
        )

    if subtotal is not None and vat_amount is not None and subtotal > Decimal("0.00"):
        expected_vat = (subtotal * Decimal("0.15")).quantize(Decimal("0.01"))
        diff = abs(vat_amount - expected_vat)
        # Tolerance BDT 0.05
        if diff > Decimal("0.05"):
            return RuleResult(
                rule_id="H05",
                rule_name="VAT rate inconsistency",
                status="REVIEW_REQUIRED",
                actual_value=f"VAT BDT {vat_amount:.2f}",
                expected_value=f"BDT {expected_vat:.2f} (15% of subtotal BDT {subtotal:.2f})",
                severity="HUMAN_REVIEW",
                document=doc_filename,
                page=page,
                evidence=evidence_text or f"VAT: BDT {vat_amount:.2f}",
                explanation=f"Calculated VAT deviates from standard 15% by BDT {diff:.2f}."
            )

    return RuleResult(
        rule_id="H05",
        rule_name="VAT compliance",
        status="PASS",
        actual_value="15% VAT separately itemized",
        expected_value="15% VAT separately itemized",
        severity="INFO",
        document=doc_filename,
        page=page,
        evidence=evidence_text or "15% VAT separately itemized",
        explanation="VAT is separately itemized at the statutory 15% rate."
    )
