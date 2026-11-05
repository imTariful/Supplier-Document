"""
Tax identity rules:
R04 — Missing TIN: supplier TIN missing -> REJECT
R05 — Missing BIN: supplier BIN missing -> REJECT
"""

from typing import Optional, List
from app.schemas.models import RuleResult

def evaluate_tax_identity_rules(
    tin: Optional[str],
    bin_num: Optional[str],
    doc_filename: str = "quotation.pdf",
    page: int = 1,
    evidence_text: str = ""
) -> List[RuleResult]:
    results: List[RuleResult] = []

    # TIN Check
    clean_tin = (tin or "").strip()
    if not clean_tin or "unregistered" in clean_tin.lower() or "pending" in clean_tin.lower():
        results.append(RuleResult(
            rule_id="R04",
            rule_name="Missing supplier TIN",
            status="FAILED",
            actual_value="Missing / Unregistered",
            expected_value="Valid 12-digit statutory TIN",
            severity="REJECT",
            document=doc_filename,
            page=page,
            evidence=evidence_text or "Supplier TIN: NOT SPECIFIED",
            explanation="Supplier Taxpayer Identification Number (TIN) is absent from submitted pack."
        ))
    else:
        results.append(RuleResult(
            rule_id="R04",
            rule_name="Supplier TIN",
            status="PASS",
            actual_value=clean_tin,
            expected_value="Valid TIN present",
            severity="INFO",
            document=doc_filename,
            page=page,
            evidence=evidence_text or f"Supplier TIN: {clean_tin}",
            explanation="Supplier TIN verified."
        ))

    # BIN Check
    clean_bin = (bin_num or "").strip()
    if not clean_bin or "unregistered" in clean_bin.lower() or "pending" in clean_bin.lower():
        results.append(RuleResult(
            rule_id="R05",
            rule_name="Missing supplier BIN",
            status="FAILED",
            actual_value="Missing / Unregistered",
            expected_value="Valid statutory BIN (VAT Registration)",
            severity="REJECT",
            document=doc_filename,
            page=page,
            evidence=evidence_text or "Supplier BIN: NOT SPECIFIED",
            explanation="Supplier Business Identification Number (BIN) is missing from submitted pack."
        ))
    else:
        results.append(RuleResult(
            rule_id="R05",
            rule_name="Supplier BIN",
            status="PASS",
            actual_value=clean_bin,
            expected_value="Valid BIN present",
            severity="INFO",
            document=doc_filename,
            page=page,
            evidence=evidence_text or f"Supplier BIN: {clean_bin}",
            explanation="Supplier BIN verified."
        ))

    return results
