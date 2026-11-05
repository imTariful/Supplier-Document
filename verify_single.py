#!/usr/bin/env python3
"""
Single Combined Supplier Document LangGraph verification runner.
Takes single combined PDF path (or separate quotation & contract paths),
invokes LangGraph workflow, and outputs complete JSON result to stdout.
"""

import sys
import os
import json
from decimal import Decimal

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.workflow.graph import build_verification_workflow
from app.services.pr_service import PurchaseRequestService

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)

def run_single(document_path: str, contract_path: str = None, supplier_id: str = "UPLOADED-PACK"):
    workflow = build_verification_workflow()
    pr_items = PurchaseRequestService.load_purchase_request()

    if contract_path and os.path.exists(contract_path) and contract_path != document_path:
        state_input = {
            "supplier_id": supplier_id,
            "quotation_path": document_path,
            "contract_path": contract_path,
            "purchase_request_items": pr_items
        }
    else:
        state_input = {
            "supplier_id": supplier_id,
            "document_path": document_path,
            "quotation_path": document_path,
            "contract_path": document_path,
            "purchase_request_items": pr_items
        }

    result = workflow.invoke(state_input)

    structured_q = result.get("quotation_details") or result.get("structured_quotation")
    structured_c = result.get("contract_terms") or result.get("structured_contract")

    triggered_rule_ids = result.get("triggered_rule_ids")
    if triggered_rule_ids is None:
        triggered_rule_ids = sorted({
            r.rule_id for r in result.get("rule_results", [])
            if r.status in ("FAILED", "REVIEW_REQUIRED")
        })

    output = {
        "supplier_id": supplier_id,
        "supplier_name": result.get("supplier_name", "Unknown Supplier"),
        "actual_decision": result.get("final_decision", "NEEDS_HUMAN_REVIEW"),
        "triggered_rule_ids": triggered_rule_ids,
        "association_confidence": result.get("association_confidence", 1.0),
        "pack_identification": result.get("pack_identification", {}),
        "evidence_verified": result.get("evidence_verified", True),
        "evidence_count": len(result.get("evidence_records", [])),
        "comparison_results": result.get("comparison_results", []),
        "quotation_details": structured_q.model_dump() if structured_q else {},
        "contract_terms": structured_c.model_dump() if structured_c else {},
        "evidence_records": [
            {
                "rule_id": e.rule_id,
                "document": e.document,
                "page_number": e.page_number,
                "exact_text": e.exact_text,
                "extracted_value": e.extracted_value,
                "expected_condition": e.expected_condition,
                "calculation": e.calculation,
                "status": e.status,
                "decision_effect": e.decision_effect
            } for e in result.get("evidence_records", [])
        ],
        "all_rule_results": [
            {
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "status": r.status,
                "actual_value": r.actual_value,
                "expected_value": r.expected_value,
                "severity": r.severity,
                "document": r.document,
                "page": r.page,
                "evidence": r.evidence,
                "explanation": r.explanation
            } for r in result.get("rule_results", [])
        ],
        "verification_notes": "; ".join([r.explanation for r in result.get("rule_results", []) if r.status in ("FAILED", "REVIEW_REQUIRED")]),
        "structured_quotation": {
            "supplier_name": structured_q.supplier_name if structured_q else "",
            "items_count": len(structured_q.items) if structured_q else 0
        }
    }

    print(json.dumps(output, default=decimal_default))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python3 verify_single.py <combined_document_path> [supplier_id]"}))
        sys.exit(1)

    first_arg = sys.argv[1]
    second_arg = sys.argv[2] if len(sys.argv) > 2 else None
    third_arg = sys.argv[3] if len(sys.argv) > 3 else None

    # Check if second argument is another PDF (legacy 2-file mode)
    if second_arg and second_arg.lower().endswith(".pdf"):
        run_single(document_path=first_arg, contract_path=second_arg, supplier_id=third_arg or "UPLOADED-PACK")
    else:
        run_single(document_path=first_arg, supplier_id=second_arg or "UPLOADED-PACK")
