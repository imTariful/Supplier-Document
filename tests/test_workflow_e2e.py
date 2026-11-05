"""
End-to-End integration test suite for LangGraph workflow and 10 supplier packs.
"""

import pytest
from app.workflow.graph import build_verification_workflow
from app.services.pr_service import PurchaseRequestService
from app.extraction.pdf_extractor import PDFExtractor
from app.extraction.ocr_extractor import OCRExtractor
from app.schemas.models import VerificationResult

@pytest.fixture(scope="module")
def workflow():
    return build_verification_workflow()

@pytest.fixture(scope="module")
def pr_items():
    return PurchaseRequestService.load_purchase_request()

def test_pdf_extractor_metadata():
    info = PDFExtractor.extract_document("data/input/pack-01_quotation.pdf")
    assert info["page_count"] >= 1
    assert len(info["doc_hash"]) == 64
    assert "Vertex Textiles" in info["full_text"]

def test_ocr_extractor_scanned_flag():
    info = OCRExtractor.extract_scanned("data/input/pack-05_quotation.pdf")
    assert info["is_scanned"] is True
    assert info["ocr_confidence"] > 0.85

def test_workflow_pack_01_approve(workflow, pr_items):
    out = workflow.invoke({
        "supplier_id": "PACK-01",
        "quotation_path": "data/input/pack-01_quotation.pdf",
        "contract_path": "data/input/pack-01_contract.pdf",
        "purchase_request_items": pr_items
    })
    assert out["final_decision"] == "APPROVE"
    assert out["status"] == "WORKFLOW_COMPLETED"

def test_workflow_pack_02_reject_price(workflow, pr_items):
    out = workflow.invoke({
        "supplier_id": "PACK-02",
        "quotation_path": "data/input/pack-02_quotation.pdf",
        "contract_path": "data/input/pack-02_contract.pdf",
        "purchase_request_items": pr_items
    })
    assert out["final_decision"] == "REJECT"
    triggered = [r.rule_id for r in out["rule_results"] if r.status in ("FAILED", "REVIEW_REQUIRED")]
    assert "R01" in triggered

def test_workflow_pack_03_reject_advance(workflow, pr_items):
    out = workflow.invoke({
        "supplier_id": "PACK-03",
        "quotation_path": "data/input/pack-03_quotation.pdf",
        "contract_path": "data/input/pack-03_contract.pdf",
        "purchase_request_items": pr_items
    })
    assert out["final_decision"] == "REJECT"
    triggered = [r.rule_id for r in out["rule_results"] if r.status in ("FAILED", "REVIEW_REQUIRED")]
    assert "R02" in triggered

def test_workflow_pack_04_reject_penalty(workflow, pr_items):
    out = workflow.invoke({
        "supplier_id": "PACK-04",
        "quotation_path": "data/input/pack-04_quotation.pdf",
        "contract_path": "data/input/pack-04_contract.pdf",
        "purchase_request_items": pr_items
    })
    assert out["final_decision"] == "REJECT"
    triggered = [r.rule_id for r in out["rule_results"] if r.status in ("FAILED", "REVIEW_REQUIRED")]
    assert "R07" in triggered

def test_workflow_pack_07_human_review_minor_price(workflow, pr_items):
    out = workflow.invoke({
        "supplier_id": "PACK-07",
        "quotation_path": "data/input/pack-07_quotation.pdf",
        "contract_path": "data/input/pack-07_contract.pdf",
        "purchase_request_items": pr_items
    })
    assert out["final_decision"] == "NEEDS_HUMAN_REVIEW"
    triggered = [r.rule_id for r in out["rule_results"] if r.status in ("FAILED", "REVIEW_REQUIRED")]
    assert "H01" in triggered or "H04" in triggered

def test_workflow_combined_document_pack_01(workflow, pr_items):
    out = workflow.invoke({
        "supplier_id": "PACK-01",
        "document_path": "data/input/pack-01_combined.pdf",
        "purchase_request_items": pr_items
    })
    assert out["final_decision"] == "APPROVE"
    assert out["quotation_details"] is not None
    assert out["contract_terms"] is not None
    assert len(out["quotation_details"].items) == 5

def test_workflow_combined_document_pack_02(workflow, pr_items):
    out = workflow.invoke({
        "supplier_id": "PACK-02",
        "document_path": "data/input/pack-02_combined.pdf",
        "purchase_request_items": pr_items
    })
    assert out["final_decision"] == "REJECT"
    triggered = [r.rule_id for r in out["rule_results"] if r.status in ("FAILED", "REVIEW_REQUIRED")]
    assert "R01" in triggered


def test_workflow_exposes_triggered_ids_and_pack_identification(workflow, pr_items):
    out = workflow.invoke({
        "supplier_id": "PACK-02",
        "document_path": "data/input/pack-02_combined.pdf",
        "purchase_request_items": pr_items
    })

    assert "R01" in out["triggered_rule_ids"]
    assert out["pack_identification"]["document_kind"] == "combined"
    assert out["pack_identification"]["supplier_name"] == "Apex Apparel Accessories Ltd"
    assert out["association_confidence"] >= 0.8
    assert out["evidence_verified"] is True
    assert out["contract_validation_passed"] is True
    assert out["final_report"]["triggered_rule_ids"] == out["triggered_rule_ids"]
