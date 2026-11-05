"""Tests for H08 evidence anchoring, H09 conflicts, and H10 association."""

from decimal import Decimal

import pytest

from app.extraction.pdf_extractor import PDFExtractor
from app.extraction.llm_extractor import StructuredExtractor
from app.rules.rule_engine import DecisionEngine
from app.services.pr_service import PurchaseRequestService


@pytest.fixture(scope="module")
def pack_01():
    info = PDFExtractor.extract_document("data/input/pack-01_combined.pdf")
    quotation, contract = StructuredExtractor.extract_combined_document(info)
    pr_items = PurchaseRequestService.load_purchase_request()
    return quotation, contract, pr_items


def _rules(result):
    return {r.rule_id for r in result.all_rule_results if r.status in ("FAILED", "REVIEW_REQUIRED")}


def test_pr_alias_is_accepted(pack_01):
    quotation, contract, pr_items = pack_01
    quotation = quotation.model_copy(update={"pr_reference": "PR-2026-AGL-0089"})
    contract = contract.model_copy(update={"pr_reference": "PR-2026-AGL-0089"})

    result = DecisionEngine.evaluate_supplier_pack(
        "PACK-01", "Vertex Textiles & Trims Ltd", quotation, contract, pr_items
    )

    assert "H09" not in _rules(result)
    assert result.final_decision == "APPROVE"


def test_unknown_pr_reference_triggers_h09(pack_01):
    quotation, contract, pr_items = pack_01
    quotation = quotation.model_copy(update={"pr_reference": "PR-2026-9999"})
    contract = contract.model_copy(update={"pr_reference": "PR-2026-9999"})

    result = DecisionEngine.evaluate_supplier_pack(
        "PACK-01", "Vertex Textiles & Trims Ltd", quotation, contract, pr_items
    )

    assert "H09" in _rules(result)
    assert result.final_decision == "NEEDS_HUMAN_REVIEW"


def test_conflicting_advance_terms_trigger_h09(pack_01):
    quotation, contract, pr_items = pack_01
    contract = contract.model_copy(update={"advance_pct": Decimal("10")})

    result = DecisionEngine.evaluate_supplier_pack(
        "PACK-01", "Vertex Textiles & Trims Ltd", quotation, contract, pr_items
    )

    assert "H09" in _rules(result)
    assert result.final_decision == "NEEDS_HUMAN_REVIEW"


def test_low_association_confidence_triggers_h10(pack_01):
    quotation, contract, pr_items = pack_01

    result = DecisionEngine.evaluate_supplier_pack(
        "PACK-01",
        "Vertex Textiles & Trims Ltd",
        quotation,
        contract,
        pr_items,
        association_confidence=0.5,
    )

    assert "H10" in _rules(result)
    assert result.final_decision == "NEEDS_HUMAN_REVIEW"


def test_unverified_evidence_triggers_h08(pack_01):
    quotation, contract, pr_items = pack_01

    result = DecisionEngine.evaluate_supplier_pack(
        "PACK-01",
        "Vertex Textiles & Trims Ltd",
        quotation,
        contract,
        pr_items,
        evidence_verified=False,
    )

    assert "H08" in _rules(result)
    assert result.final_decision == "NEEDS_HUMAN_REVIEW"
