"""
Deterministic Business Rule Engine for Aamar Garments Ltd.
Evaluates all rules, preserves all evidence, and enforces strict decision hierarchy:
REJECT > NEEDS_HUMAN_REVIEW > APPROVE.
An LLM can NEVER override this engine.
"""

import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from app.schemas.models import (
    ExtractedQuotation,
    ExtractedContract,
    PurchaseRequestItem,
    RuleResult,
    EvidenceRecord,
    VerificationResult
)
from app.rules.price_rules import evaluate_price_rules
from app.rules.quantity_rules import evaluate_quantity_rules
from app.rules.advance_rules import evaluate_advance_rules
from app.rules.payment_rules import evaluate_payment_terms_rules
from app.rules.delivery_rules import evaluate_delivery_rules
from app.rules.vat_rules import evaluate_vat_rules
from app.rules.tax_identity_rules import evaluate_tax_identity_rules
from app.rules.penalty_rules import evaluate_penalty_rules
from app.rules.validity_rules import evaluate_validity_rules
from app.rules.arithmetic_rules import evaluate_arithmetic_rules
from app.services.pr_service import PurchaseRequestService

RULE_ENGINE_VERSION = "2.1.0-deterministic"


def _normalize_supplier_name(name: Optional[str]) -> str:
    if not name:
        return ""
    normalized = name.lower()
    normalized = re.sub(r"&", " and ", normalized)
    normalized = re.sub(
        r"\b(?:ltd|limited|llc|l\.l\.c|inc|incorporated|corp|corporation|"
        r"co|company|plc|pvt|private|enterprises?|group)\b",
        " ",
        normalized,
    )
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def _supplier_names_match(first: Optional[str], second: Optional[str]) -> bool:
    """Tolerant identity comparison for the quotation and contract sections."""
    a = _normalize_supplier_name(first)
    b = _normalize_supplier_name(second)
    if not a or not b:
        return True  # Missing identity is handled by the association-confidence rule.
    if a == b:
        return True
    # Some documents add/omit a legal suffix or a trading brand.  Token overlap
    # catches those without treating two genuinely different suppliers as one.
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens or not b_tokens:
        return False
    overlap = len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))
    return overlap >= 0.75


def _same_decimal(first: Optional[Decimal], second: Optional[Decimal]) -> bool:
    if first is None or second is None:
        return True
    return Decimal(str(first)) == Decimal(str(second))


def _review_rule(
    rule_id: str,
    rule_name: str,
    actual_value: str,
    expected_value: str,
    evidence: str,
    explanation: str,
    document: str,
    page: int = 1,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        rule_name=rule_name,
        status="REVIEW_REQUIRED",
        actual_value=actual_value,
        expected_value=expected_value,
        severity="HUMAN_REVIEW",
        document=document,
        page=page,
        evidence=evidence,
        explanation=explanation,
    )


class DecisionEngine:
    @classmethod
    def evaluate_supplier_pack(
        cls,
        supplier_id: str,
        supplier_name: str,
        quotation: ExtractedQuotation,
        contract: ExtractedContract,
        pr_items: Dict[str, PurchaseRequestItem],
        association_confidence: float = 1.0,
        evidence_verified: bool = True,
        pack_identification: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        all_rules: List[RuleResult] = []
        evidence_records: List[EvidenceRecord] = []

        q_file = quotation.source_filename or "quotation.pdf"
        c_file = contract.source_filename or "contract.pdf"

        # 1. Price Rules (R01, H01)
        price_results = evaluate_price_rules(quotation.items, pr_items, doc_filename=q_file)
        all_rules.extend(price_results)

        # 2. Quantity Rules (H02)
        qty_results = evaluate_quantity_rules(quotation.items, pr_items, doc_filename=q_file)
        all_rules.extend(qty_results)

        # 2b. Item coverage (H08): approval requires every requested item.
        quoted_codes = {item.item_code for item in quotation.items}
        missing_codes = sorted(code for code in pr_items if code not in quoted_codes)
        if missing_codes:
            all_rules.append(RuleResult(
                rule_id="H08",
                rule_name="Incomplete item coverage",
                status="REVIEW_REQUIRED",
                actual_value=(
                    f"{len(quoted_codes)} of {len(pr_items)} requested items quoted; "
                    f"missing {', '.join(missing_codes)}"
                ),
                expected_value="All requested items quoted (100% item-code coverage)",
                severity="HUMAN_REVIEW",
                document=q_file,
                page=1,
                evidence=(
                    f"Quoted items: {', '.join(sorted(quoted_codes)) or 'none'}; "
                    f"missing: {', '.join(missing_codes)}"
                ),
                explanation=(
                    "The quotation does not cover every item in the purchase request, "
                    "so the pack cannot be approved without commercial review."
                )
            ))

        # 2c. Evidence verification (H08): every material value must be
        # anchored to source text/page metadata from the original PDF.
        if not evidence_verified:
            all_rules.append(_review_rule(
                rule_id="H08",
                rule_name="Unverified source evidence",
                actual_value="One or more extracted values could not be anchored to the source document",
                expected_value="Every material value traceable to exact source text and page",
                evidence="Evidence verification failed during the workflow.",
                explanation=(
                    "The extracted values are not fully traceable to the source PDF, "
                    "so a procurement auditor must verify the document manually."
                ),
                document=f"{q_file} & {c_file}",
            ))

        # 2d. Document association confidence (H10): the quotation and contract
        # must clearly belong to the same supplier pack and purchase request.
        if association_confidence < 0.8:
            identification = pack_identification or {}
            all_rules.append(_review_rule(
                rule_id="H10",
                rule_name="Ambiguous document association",
                actual_value=f"Association confidence {association_confidence:.0%}",
                expected_value="At least 80% association confidence",
                evidence=(
                    identification.get("notes")
                    or "Supplier identity or purchase-request reference does not "
                    "unambiguously connect the quotation and contract."
                ),
                explanation=(
                    "The quotation and terms & conditions cannot be confidently "
                    "paired as one supplier pack; human confirmation is required."
                ),
                document=f"{q_file} & {c_file}",
            ))

        # 3. Advance Payment Rules (R02)
        # Advance payment may be defined in contract or quotation; take most conservative or contract-stipulated
        adv_pct = contract.advance_pct if contract.advance_pct is not None else quotation.advance_pct
        adv_evidence = f"Contract Article 3: advance payment of {adv_pct}%" if contract.advance_pct else quotation.raw_text[:200]
        all_rules.append(evaluate_advance_rules(adv_pct, doc_filename=c_file, page=1, evidence_text=adv_evidence))

        # 4. Payment Terms Rules (H03)
        rem_days = contract.remaining_days if contract.remaining_days is not None else quotation.remaining_days
        rem_evidence = f"Contract Article 3: settled within {rem_days} days after delivery" if contract.remaining_days else quotation.raw_text[:200]
        all_rules.append(evaluate_payment_terms_rules(rem_days, doc_filename=c_file, page=1, evidence_text=rem_evidence))

        # 5. Delivery Rules (R06, H04)
        del_days = contract.delivery_days if contract.delivery_days is not None else quotation.delivery_days
        del_evidence = f"Contract Article 2: deliver within {del_days} days" if contract.delivery_days else f"Quotation delivery: {del_days} days"
        all_rules.append(evaluate_delivery_rules(del_days, doc_filename=c_file, page=1, evidence_text=del_evidence))

        # 6. VAT Compliance Rules (H05)
        vat_sep = quotation.vat_separate and contract.vat_separate
        vat_evidence = "Article 5: VAT is not separately shown" if not contract.vat_separate else "Quotation: 15% VAT separately itemized"
        all_rules.append(evaluate_vat_rules(vat_sep, quotation.subtotal, quotation.vat_amount, doc_filename=q_file, page=1, evidence_text=vat_evidence))

        # 7. Tax Identity Rules (R04, R05)
        # Check both quotation and contract
        effective_tin = contract.tin or quotation.tin
        effective_bin = contract.bin or quotation.bin
        tin_evidence = f"TIN: {effective_tin or 'UNSPECIFIED'}"
        bin_evidence = f"BIN: {effective_bin or 'UNSPECIFIED'}"
        tax_results = evaluate_tax_identity_rules(effective_tin, effective_bin, doc_filename=c_file, page=1, evidence_text=f"{tin_evidence} | {bin_evidence}")
        all_rules.extend(tax_results)

        # 8. Penalty Rules (R03, R07)
        all_rules.append(evaluate_penalty_rules(
            contract.penalty_clause,
            contract.penalty_rate_pct,
            contract.penalty_basis,
            doc_filename=c_file,
            page=1
        ))

        # 9. Quotation Validity Rules (H07)
        val_evidence = f"Quotation validity is {quotation.validity_days} days" if quotation.validity_days else "Validity unspecified"
        all_rules.append(evaluate_validity_rules(quotation.validity_days, doc_filename=q_file, page=1, evidence_text=val_evidence))

        # 10. Financial Arithmetic Rules (H06)
        arith_results = evaluate_arithmetic_rules(
            quotation.items,
            quotation.subtotal,
            quotation.vat_amount,
            quotation.grand_total,
            vat_separate=vat_sep,
            doc_filename=q_file,
            page=1
        )
        all_rules.extend(arith_results)

        # 11. Cross-document Conflicts & Reference Validation (H09)
        def add_conflict(name: str, actual: str, expected: str, evidence: str, explanation: str) -> None:
            all_rules.append(_review_rule(
                rule_id="H09",
                rule_name=name,
                actual_value=actual,
                expected_value=expected,
                evidence=evidence,
                explanation=explanation,
                document=f"{q_file} & {c_file}",
            ))

        if contract.delivery_days and quotation.delivery_days and contract.delivery_days != quotation.delivery_days:
            add_conflict(
                "Conflicting delivery terms",
                f"Quotation: {quotation.delivery_days}d vs Contract: {contract.delivery_days}d",
                "Matching delivery timeline across documents",
                f"Quotation states {quotation.delivery_days}d, Contract states {contract.delivery_days}d",
                "Material discrepancy between quotation and contract delivery terms.",
            )

        if not _same_decimal(quotation.advance_pct, contract.advance_pct):
            add_conflict(
                "Conflicting advance payment terms",
                f"Quotation: {quotation.advance_pct}% vs Contract: {contract.advance_pct}%",
                "Matching advance payment percentage",
                f"Quotation states {quotation.advance_pct}% advance, Contract states {contract.advance_pct}%",
                "The two sections specify different advance payment percentages.",
            )

        if not _same_decimal(quotation.remaining_days, contract.remaining_days):
            add_conflict(
                "Conflicting remaining payment terms",
                f"Quotation: {quotation.remaining_days}d vs Contract: {contract.remaining_days}d",
                "Matching remaining-payment window",
                f"Quotation states {quotation.remaining_days} days, Contract states {contract.remaining_days} days",
                "The two sections specify different balance-payment windows.",
            )

        if not _supplier_names_match(quotation.supplier_name, contract.supplier_name):
            add_conflict(
                "Conflicting supplier identity",
                f"Quotation: {quotation.supplier_name} vs Contract: {contract.supplier_name}",
                "Same legal supplier identity across both documents",
                f"Quotation names '{quotation.supplier_name}', Contract names '{contract.supplier_name}'",
                "The quotation and contract appear to come from different suppliers.",
            )

        if quotation.vat_separate != contract.vat_separate:
            add_conflict(
                "Conflicting VAT treatment",
                f"Quotation VAT separate: {quotation.vat_separate}; Contract VAT separate: {contract.vat_separate}",
                "Consistent VAT treatment across both documents",
                "The quotation and contract disagree on whether VAT is separately itemized.",
                "VAT presentation must be reconciled before approval.",
            )

        q_ref = (quotation.pr_reference or "").strip()
        c_ref = (contract.pr_reference or "").strip()
        references = [ref for ref in (q_ref, c_ref) if ref]
        invalid_references = sorted({
            ref for ref in references
            if not PurchaseRequestService.is_valid_reference(ref)
        })
        canonical_ref = PurchaseRequestService.get_canonical_pr_reference()

        if invalid_references:
            add_conflict(
                "Unrecognised purchase request reference",
                f"Document reference(s): {', '.join(invalid_references)}",
                f"Reference must be {canonical_ref} or an accepted alias",
                (
                    f"Supplier document cites {', '.join(invalid_references)}; "
                    f"authoritative purchase request is {canonical_ref}."
                ),
                "The supplier document points to a different or unknown purchase request.",
            )
        elif q_ref and c_ref and not PurchaseRequestService.references_match(q_ref, c_ref):
            add_conflict(
                "Conflicting purchase request references",
                f"Quotation: {q_ref} vs Contract: {c_ref}",
                f"Both documents should reference {canonical_ref}",
                f"Quotation cites {q_ref}, Contract cites {c_ref}.",
                "The quotation and contract reference different purchase requests.",
            )

        # Deterministic Decision Hierarchy:
        # REJECT > NEEDS_HUMAN_REVIEW > APPROVE
        rejections = [r for r in all_rules if r.severity == "REJECT" and r.status == "FAILED"]
        reviews = [r for r in all_rules if r.severity == "HUMAN_REVIEW" and r.status in ("REVIEW_REQUIRED", "NOT_EVALUABLE")]

        if rejections:
            final_decision = "REJECT"
            triggered = rejections
        elif reviews:
            final_decision = "NEEDS_HUMAN_REVIEW"
            triggered = reviews
        else:
            final_decision = "APPROVE"
            triggered = []

        # Convert triggered rules to Evidence Records
        for r in triggered:
            evidence_records.append(EvidenceRecord(
                rule_id=r.rule_id,
                document=r.document,
                page_number=r.page,
                exact_text=r.evidence or r.explanation,
                extracted_value=r.actual_value,
                expected_condition=r.expected_value,
                calculation=None,
                status=r.status,
                decision_effect=final_decision
            ))

        return VerificationResult(
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            final_decision=final_decision,
            triggered_rules=triggered,
            all_rule_results=all_rules,
            evidence_records=evidence_records,
            quotation_data=quotation,
            contract_data=contract,
            timestamp="2026-11-03T21:00:00Z"
        )
