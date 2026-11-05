"""
LangGraph Sequential & Conditional Workflow for Supplier Document Verification.
Implements the 12-node pipeline with support for Combined Supplier Documents
(Quotation + Terms & Conditions in a single PDF) with exact page tracking and evidence.
"""

import os
from decimal import Decimal
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from app.workflow.state import VerificationWorkflowState
from app.extraction.pdf_extractor import PDFExtractor
from app.extraction.ocr_extractor import OCRExtractor
from app.extraction.llm_extractor import StructuredExtractor
from app.rules.rule_engine import DecisionEngine, _supplier_names_match
from app.services.pr_service import PurchaseRequestService
from app.schemas.models import RuleResult, EvidenceRecord

# --- NODE IMPLEMENTATIONS ---

def node_ingest_documents(state: VerificationWorkflowState) -> Dict[str, Any]:
    doc_path = state.get("document_path", "")
    q_path = state.get("quotation_path", "")
    c_path = state.get("contract_path", "")
    errors = []

    if doc_path:
        if not os.path.exists(doc_path):
            errors.append(f"Combined supplier document not found at: {doc_path}")
    elif q_path or c_path:
        if q_path and not os.path.exists(q_path):
            errors.append(f"Quotation file not found at: {q_path}")
        if c_path and not os.path.exists(c_path):
            errors.append(f"Contract file not found at: {c_path}")
    else:
        errors.append("No supplier document provided for verification.")

    # Load authoritative purchase request if not already populated
    pr_items = state.get("purchase_request_items")
    if not pr_items:
        pr_items = PurchaseRequestService.load_purchase_request()

    return {
        "extraction_errors": errors,
        "purchase_request_items": pr_items,
        "status": "DOCUMENTS_INGESTED" if not errors else "INGESTION_ERROR"
    }

def node_identify_supplier_pack(state: VerificationWorkflowState) -> Dict[str, Any]:
    """
    Associate the quotation and contract sections with one supplier pack.

    Combined PDFs are one physical document, so association is inherently
    strong; separate files are scored on supplier identity and PR reference
    agreement.  A score below 0.8 becomes rule H10 in the decision engine.
    """
    quotation = state.get("structured_quotation")
    contract = state.get("structured_contract")
    is_combined = bool(state.get("document_doc_info"))

    q_name = quotation.supplier_name if quotation else ""
    c_name = contract.supplier_name if contract else ""
    q_ref = (quotation.pr_reference if quotation else "") or ""
    c_ref = (contract.pr_reference if contract else "") or ""
    notes: List[str] = []

    if is_combined:
        confidence = 0.98
        if not q_name or q_name == "Unknown Supplier":
            confidence -= 0.30
            notes.append("Supplier identity could not be read from the document.")
        if not (q_ref or c_ref):
            confidence -= 0.25
            notes.append("No purchase-request reference was found.")
    else:
        confidence = 0.0
        if quotation and contract:
            confidence += 0.40
        else:
            notes.append("Only one of the quotation and contract documents is available.")

        if quotation and contract and _supplier_names_match(q_name, c_name):
            confidence += 0.35
        elif q_name and c_name:
            notes.append(
                f"Supplier names differ: '{q_name}' vs '{c_name}'."
            )

        if q_ref and c_ref and PurchaseRequestService.references_match(q_ref, c_ref):
            confidence += 0.25
        elif q_ref or c_ref:
            confidence += 0.10
            notes.append("Only one document cites a purchase-request reference.")
        else:
            notes.append("Neither document cites a purchase-request reference.")

    confidence = max(0.0, min(1.0, round(confidence, 2)))

    supplier_name = q_name or c_name or state.get("supplier_name") or "Unknown Supplier"
    supplier_id = state.get("supplier_id") or ""
    if not supplier_id:
        stem = os.path.splitext(os.path.basename(
            state.get("document_path") or state.get("quotation_path") or ""
        ))[0]
        supplier_id = stem.upper() or "UNIDENTIFIED-PACK"

    pack_identification = {
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "document_kind": "combined" if is_combined else "separate",
        "quotation_reference": q_ref,
        "contract_reference": c_ref,
        "references_match": bool(
            q_ref and c_ref and PurchaseRequestService.references_match(q_ref, c_ref)
        ),
        "association_confidence": confidence,
        "notes": " ".join(notes).strip(),
    }

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "pack_identification": pack_identification,
        "association_confidence": confidence,
        "status": "PACK_IDENTIFIED",
    }

def node_extract_document_text(state: VerificationWorkflowState) -> Dict[str, Any]:
    doc_path = state.get("document_path")
    if doc_path and os.path.exists(doc_path):
        doc_info = OCRExtractor.extract_scanned(doc_path)
        is_scanned = doc_info.get("is_scanned", False)
        ocr_conf = doc_info.get("ocr_confidence", 1.0)
        return {
            "document_doc_info": doc_info,
            "quotation_doc_info": doc_info,
            "contract_doc_info": doc_info,
            "is_scanned": is_scanned,
            "ocr_confidence": ocr_conf,
            "status": "TEXT_EXTRACTED"
        }

    # Fallback to separate files if provided
    q_path = state.get("quotation_path", "")
    c_path = state.get("contract_path", "")
    q_info = OCRExtractor.extract_scanned(q_path) if q_path and os.path.exists(q_path) else {}
    c_info = OCRExtractor.extract_scanned(c_path) if c_path and os.path.exists(c_path) else {}

    is_scanned = q_info.get("is_scanned", False) or c_info.get("is_scanned", False)
    min_conf = min(q_info.get("ocr_confidence", 1.0), c_info.get("ocr_confidence", 1.0))

    return {
        "document_doc_info": None,
        "quotation_doc_info": q_info,
        "contract_doc_info": c_info,
        "is_scanned": is_scanned,
        "ocr_confidence": min_conf,
        "status": "TEXT_EXTRACTED"
    }

def node_assess_extraction_quality(state: VerificationWorkflowState) -> Dict[str, Any]:
    doc_info = state.get("document_doc_info")
    if doc_info:
        text_len = len(doc_info.get("full_text", ""))
        score = 1.0
        if text_len < 100:
            score = 0.4
        elif state.get("is_scanned", False):
            score = 0.91
        return {
            "extraction_quality_score": score,
            "status": "QUALITY_ASSESSED"
        }

    q_info = state.get("quotation_doc_info", {})
    c_info = state.get("contract_doc_info", {})
    q_len = len(q_info.get("full_text", ""))
    c_len = len(c_info.get("full_text", ""))

    score = 1.0
    if q_len < 100 or c_len < 100:
        score = 0.4
    elif state.get("is_scanned", False):
        score = 0.91

    return {
        "extraction_quality_score": score,
        "status": "QUALITY_ASSESSED"
    }

def node_extract_structured_data(state: VerificationWorkflowState) -> Dict[str, Any]:
    doc_info = state.get("document_doc_info")
    if doc_info:
        # Extract both Section A: Quotation and Section B: Terms & Conditions from single PDF
        structured_q, structured_c = StructuredExtractor.extract_combined_document(doc_info)
        return {
            "quotation_details": structured_q,
            "contract_terms": structured_c,
            "structured_quotation": structured_q,
            "structured_contract": structured_c,
            "supplier_name": structured_q.supplier_name,
            "status": "STRUCTURED_EXTRACTED"
        }

    # Fallback to separate files
    q_info = state.get("quotation_doc_info", {})
    c_info = state.get("contract_doc_info", {})
    structured_q = StructuredExtractor.extract_quotation(q_info)
    structured_c = StructuredExtractor.extract_contract(c_info)

    return {
        "quotation_details": structured_q,
        "contract_terms": structured_c,
        "structured_quotation": structured_q,
        "structured_contract": structured_c,
        "supplier_name": structured_q.supplier_name,
        "status": "STRUCTURED_EXTRACTED"
    }

def node_validate_extracted_data(state: VerificationWorkflowState) -> Dict[str, Any]:
    structured_q = state.get("structured_quotation")
    errors = list(state.get("extraction_errors", []))

    if not structured_q or not structured_q.items:
        errors.append("No line items could be extracted from quotation section.")

    return {
        "extraction_errors": errors,
        "status": "DATA_VALIDATED" if not errors else "VALIDATION_FAILED"
    }

def _normalized_contains(haystack: str, needle: str) -> bool:
    def normalize(value: str) -> str:
        return " ".join((value or "").split()).lower()
    return normalize(needle) in normalize(haystack)


def node_verify_evidence(state: VerificationWorkflowState) -> Dict[str, Any]:
    """
    Anchor extracted values to the original text and page metadata.

    This is deliberately stricter than "source_text is non-empty": the snippet
    must actually occur in the extracted document text and every page citation
    must fall inside the document.
    """
    structured_q = state.get("structured_quotation")
    structured_c = state.get("structured_contract")
    issues: List[str] = []

    if structured_q is None or structured_c is None:
        issues.append("Structured quotation or contract data is missing.")

    if structured_q is not None:
        raw_text = structured_q.raw_text or ""
        page_count = max(1, structured_q.page_count or 1)

        for item in structured_q.items:
            if not item.source_text or len(item.source_text.strip()) < 5:
                issues.append(f"{item.item_code}: item has no usable source snippet.")
            elif raw_text and not _normalized_contains(raw_text, item.source_text):
                issues.append(f"{item.item_code}: source snippet is not present in the PDF text.")
            if item.page_number < 1 or item.page_number > page_count:
                issues.append(f"{item.item_code}: cited page {item.page_number} is outside the document.")

        if structured_q.supplier_name and structured_q.supplier_name != "Unknown Supplier":
            if raw_text and not _normalized_contains(raw_text, structured_q.supplier_name):
                issues.append("Supplier name could not be anchored to the source text.")

        if structured_q.quotation_no and raw_text:
            if not _normalized_contains(raw_text, structured_q.quotation_no):
                issues.append("Quotation number could not be anchored to the source text.")

    evidence_verified = not issues
    return {
        "evidence_verified": evidence_verified,
        "evidence_issues": issues,
        "status": "EVIDENCE_VERIFIED" if evidence_verified else "EVIDENCE_UNVERIFIED",
    }

def node_compare_purchase_request(state: VerificationWorkflowState) -> Dict[str, Any]:
    structured_q = state["structured_quotation"]
    pr_items = state["purchase_request_items"]

    comparisons = []
    for item in structured_q.items:
        pr_item = pr_items.get(item.item_code)
        if pr_item:
            price_dev = ((item.unit_price - pr_item.max_unit_price) / pr_item.max_unit_price) * 100
            qty_dev = (abs(item.quantity - pr_item.quantity) / pr_item.quantity) * 100
            comparisons.append({
                "item_code": item.item_code,
                "requested_qty": float(pr_item.quantity),
                "quoted_qty": float(item.quantity),
                "qty_deviation_pct": float(qty_dev),
                "max_unit_price": float(pr_item.max_unit_price),
                "quoted_unit_price": float(item.unit_price),
                "price_deviation_pct": float(price_dev)
            })

    return {
        "comparison_results": comparisons,
        "status": "PR_COMPARED"
    }

def node_validate_contract(state: VerificationWorkflowState) -> Dict[str, Any]:
    """Check that the T&C section contains the clauses later rules rely on."""
    contract = state.get("structured_contract")
    checks: List[Dict[str, Any]] = []

    def check(field: str, passed: bool, detail: str) -> None:
        checks.append({
            "field": field,
            "status": "PASS" if passed else "REVIEW",
            "detail": detail,
        })

    if contract is None:
        return {
            "contract_compliance_results": [{
                "field": "contract_section",
                "status": "REVIEW",
                "detail": "No contract / terms & conditions section was extracted.",
            }],
            "contract_validation_passed": False,
            "status": "CONTRACT_VALIDATED",
        }

    check(
        "agreement_reference",
        bool(contract.agreement_no),
        contract.agreement_no or "Agreement/contract reference is missing.",
    )
    check(
        "supplier_identity",
        bool(contract.supplier_name) and contract.supplier_name != "Unknown Supplier",
        contract.supplier_name or "Supplier identity is missing.",
    )
    check(
        "delivery_terms",
        contract.delivery_days is not None,
        f"Delivery period: {contract.delivery_days} days" if contract.delivery_days is not None
        else "Delivery period is missing.",
    )
    check(
        "advance_terms",
        contract.advance_pct is not None,
        f"Advance: {contract.advance_pct}%" if contract.advance_pct is not None
        else "Advance payment term is missing.",
    )
    check(
        "remaining_payment_terms",
        contract.remaining_days is not None,
        f"Balance payment: {contract.remaining_days} days after delivery" if contract.remaining_days is not None
        else "Remaining payment window is missing.",
    )
    check(
        "late_delivery_penalty",
        bool(contract.penalty_clause) and contract.penalty_rate_pct is not None,
        (
            f"Penalty: {contract.penalty_rate_pct}% per week ({contract.penalty_basis})"
            if contract.penalty_clause and contract.penalty_rate_pct is not None
            else "Late-delivery penalty clause or rate is missing."
        ),
    )
    check(
        "tax_identity",
        bool(contract.tin) and bool(contract.bin),
        f"TIN: {contract.tin or 'missing'}; BIN: {contract.bin or 'missing'}",
    )
    check(
        "purchase_request_reference",
        bool(contract.pr_reference) and PurchaseRequestService.is_valid_reference(contract.pr_reference),
        contract.pr_reference or "Purchase-request reference is missing.",
    )

    return {
        "contract_compliance_results": checks,
        "contract_validation_passed": all(c["status"] == "PASS" for c in checks),
        "status": "CONTRACT_VALIDATED",
    }

def node_validate_financials(state: VerificationWorkflowState) -> Dict[str, Any]:
    """Independently recompute line totals, subtotal, VAT and grand total."""
    quotation = state.get("structured_quotation")
    checks: List[Dict[str, Any]] = []
    tolerance = Decimal("0.05")

    def check(field: str, stated: Any, computed: Any, detail: str) -> None:
        if stated is None or computed is None:
            checks.append({
                "field": field,
                "status": "NOT_EVALUABLE",
                "stated": None,
                "computed": None,
                "difference": None,
                "detail": detail,
            })
            return
        stated_dec = Decimal(str(stated))
        computed_dec = Decimal(str(computed))
        difference = stated_dec - computed_dec
        checks.append({
            "field": field,
            "status": "PASS" if abs(difference) <= tolerance else "REVIEW",
            "stated": str(stated_dec),
            "computed": str(computed_dec),
            "difference": str(difference),
            "detail": detail,
        })

    if quotation is None:
        return {
            "financial_validation_results": [{
                "field": "quotation_section",
                "status": "NOT_EVALUABLE",
                "detail": "No quotation section was extracted.",
            }],
            "financial_validation_passed": False,
            "status": "FINANCIALS_VALIDATED",
        }

    computed_lines = [
        (item.quantity * item.unit_price)
        for item in quotation.items
    ]
    item_sum = sum(computed_lines, Decimal("0"))

    for item, expected_total in zip(quotation.items, computed_lines):
        check(
            f"line_total:{item.item_code}",
            item.line_total,
            expected_total,
            "Line total must equal quantity x unit price.",
        )

    check(
        "subtotal",
        quotation.subtotal,
        item_sum if quotation.items else None,
        "Subtotal must equal the sum of line totals.",
    )

    if quotation.vat_amount is not None and quotation.subtotal is not None:
        check(
            "vat_at_15_percent",
            quotation.vat_amount,
            quotation.subtotal * Decimal("0.15"),
            "VAT must equal 15% of the stated subtotal.",
        )

    if quotation.grand_total is not None and quotation.subtotal is not None:
        expected_grand = quotation.subtotal + (quotation.vat_amount or Decimal("0"))
        check(
            "grand_total",
            quotation.grand_total,
            expected_grand,
            "Grand total must equal subtotal plus VAT.",
        )

    return {
        "financial_validation_results": checks,
        "financial_validation_passed": all(c["status"] in ("PASS", "NOT_EVALUABLE") for c in checks),
        "status": "FINANCIALS_VALIDATED",
    }

def node_evaluate_rules(state: VerificationWorkflowState) -> Dict[str, Any]:
    supplier_id = state["supplier_id"]
    supplier_name = state.get("supplier_name", "Unknown Supplier")
    structured_q = state["structured_quotation"]
    structured_c = state["structured_contract"]
    pr_items = state["purchase_request_items"]

    verif_result = DecisionEngine.evaluate_supplier_pack(
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        quotation=structured_q,
        contract=structured_c,
        pr_items=pr_items,
        association_confidence=state.get("association_confidence", 1.0),
        evidence_verified=state.get("evidence_verified", True),
        pack_identification=state.get("pack_identification"),
    )
    triggered_ids = sorted({r.rule_id for r in verif_result.triggered_rules})

    return {
        "final_decision": verif_result.final_decision,
        "rule_results": verif_result.all_rule_results,
        "triggered_rules": verif_result.triggered_rules,
        "triggered_rule_ids": triggered_ids,
        "evidence_records": verif_result.evidence_records,
        "status": "RULES_EVALUATED"
    }

def node_generate_report(state: VerificationWorkflowState) -> Dict[str, Any]:
    supplier_id = state["supplier_id"]
    decision = state["final_decision"]
    triggered_models = state.get("triggered_rules")
    if triggered_models is None:
        triggered_models = [
            r for r in state.get("rule_results", [])
            if r.status in ("FAILED", "REVIEW_REQUIRED")
        ]
    triggered = [r.model_dump() for r in triggered_models]
    triggered_ids = sorted({r.rule_id for r in triggered_models})

    report = {
        "supplier_id": supplier_id,
        "supplier_name": state.get("supplier_name", ""),
        "final_decision": decision,
        "triggered_count": len(triggered),
        "triggered_rule_ids": triggered_ids,
        "triggered_rules": triggered,
        "pack_identification": state.get("pack_identification", {}),
        "association_confidence": state.get("association_confidence", 1.0),
        "evidence_verified": state.get("evidence_verified", True),
        "evidence_issues": state.get("evidence_issues", []),
        "contract_compliance_results": state.get("contract_compliance_results", []),
        "financial_validation_results": state.get("financial_validation_results", []),
        "is_scanned": state.get("is_scanned", False),
        "ocr_confidence": state.get("ocr_confidence", 1.0)
    }

    return {
        "final_report": report,
        "triggered_rule_ids": triggered_ids,
        "status": "WORKFLOW_COMPLETED"
    }

# --- CONDITIONAL ROUTING ---

def check_ingestion_edge(state: VerificationWorkflowState) -> str:
    if state.get("extraction_errors"):
        return "route_to_human_review"
    return "extract_document_text"

def check_quality_edge(state: VerificationWorkflowState) -> str:
    if state.get("extraction_quality_score", 1.0) < 0.5:
        return "route_to_human_review"
    return "extract_structured_data"

def check_evidence_edge(state: VerificationWorkflowState) -> str:
    if not state.get("evidence_verified", True):
        return "evaluate_rules"
    return "compare_purchase_request"

def route_to_human_review(state: VerificationWorkflowState) -> Dict[str, Any]:
    return {
        "final_decision": "NEEDS_HUMAN_REVIEW",
        "status": "ESCALATED_TO_HUMAN_REVIEW"
    }

# --- WORKFLOW GRAPH COMPILATION ---

def build_verification_workflow() -> Any:
    workflow = StateGraph(VerificationWorkflowState)

    workflow.add_node("ingest_documents", node_ingest_documents)
    workflow.add_node("identify_supplier_pack", node_identify_supplier_pack)
    workflow.add_node("extract_document_text", node_extract_document_text)
    workflow.add_node("assess_extraction_quality", node_assess_extraction_quality)
    workflow.add_node("extract_structured_data", node_extract_structured_data)
    workflow.add_node("validate_extracted_data", node_validate_extracted_data)
    workflow.add_node("verify_evidence", node_verify_evidence)
    workflow.add_node("compare_purchase_request", node_compare_purchase_request)
    workflow.add_node("validate_contract", node_validate_contract)
    workflow.add_node("validate_financials", node_validate_financials)
    workflow.add_node("evaluate_rules", node_evaluate_rules)
    workflow.add_node("generate_report", node_generate_report)
    workflow.add_node("route_to_human_review", route_to_human_review)

    workflow.set_entry_point("ingest_documents")

    workflow.add_conditional_edges(
        "ingest_documents",
        check_ingestion_edge,
        {
            "extract_document_text": "extract_document_text",
            "route_to_human_review": "route_to_human_review"
        }
    )

    workflow.add_edge("extract_document_text", "assess_extraction_quality")

    workflow.add_conditional_edges(
        "assess_extraction_quality",
        check_quality_edge,
        {
            "extract_structured_data": "extract_structured_data",
            "route_to_human_review": "route_to_human_review"
        }
    )

    workflow.add_edge("extract_structured_data", "identify_supplier_pack")
    workflow.add_edge("identify_supplier_pack", "validate_extracted_data")
    workflow.add_edge("validate_extracted_data", "verify_evidence")

    workflow.add_conditional_edges(
        "verify_evidence",
        check_evidence_edge,
        {
            "evaluate_rules": "evaluate_rules",
            "compare_purchase_request": "compare_purchase_request"
        }
    )

    workflow.add_edge("compare_purchase_request", "validate_contract")
    workflow.add_edge("validate_contract", "validate_financials")
    workflow.add_edge("validate_financials", "evaluate_rules")
    workflow.add_edge("evaluate_rules", "generate_report")
    workflow.add_edge("generate_report", END)
    workflow.add_edge("route_to_human_review", END)

    return workflow.compile()
