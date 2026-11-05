"""
Regression tests for document-layout tolerant extraction.

The generated assessment packs use labels such as ``Quotation Reference:`` and
``ITEM-A``.  Real supplier PDFs commonly use separate label/value lines and
single-letter item codes.  Both layouts must extract the same structured data.
"""

from decimal import Decimal

from app.extraction.llm_extractor import StructuredExtractor
from app.extraction.pdf_extractor import PDFExtractor
from app.services.pr_service import PurchaseRequestService
from app.workflow.graph import build_verification_workflow


REAL_WORLD_QUOTATION = """Padma Textile Mills Ltd
QUOTATION
Quotation no.
QT-2026-901
Date
2026-10-21
To
Aamar Garments Ltd (fictional)
Reference
PR-2026-114
Item
Description
Qty
Unit
Unit price (BDT)
Amount (BDT)
A
Cotton twill fabric, 280 gsm
12,000
metre
472.00
5,664,000.00
Subtotal
5,664,000.00
VAT 15%
849,600.00
Total
6,513,600.00
Supplier TIN: 101458013391 BIN: 000170141-0101
TERMS AND CONDITIONS
1. Payment. 10% advance payable with the purchase order. Balance payable within 45 days after delivery and
acceptance of goods.
2. Delivery. Delivery within 24 days of receiving the purchase order.
3. Delay. Late delivery penalty: 1% of order value for each full week of delay.
4. Validity. This quotation is valid for 45 days from the date above.
"""


def _doc_info(text: str):
    return {
        "full_text": text,
        "pages_text": [text],
        "filename": "supplier-quotation.pdf",
        "doc_hash": "a" * 64,
        "page_count": 1,
    }


def test_real_world_layout_extracts_all_fields():
    quotation, contract = StructuredExtractor.extract_combined_document(
        _doc_info(REAL_WORLD_QUOTATION)
    )

    assert quotation.supplier_name == "Padma Textile Mills Ltd"
    assert quotation.quotation_no == "QT-2026-901"
    assert quotation.pr_reference == "PR-2026-114"
    assert quotation.date_str == "2026-10-21"
    assert quotation.tin == "101458013391"
    assert quotation.bin == "000170141-0101"

    assert len(quotation.items) == 1
    item = quotation.items[0]
    assert item.item_code == "ITEM-A"
    assert item.description == "Cotton twill fabric, 280 gsm"
    assert item.quantity == Decimal("12000")
    assert item.unit == "metre"
    assert item.unit_price == Decimal("472.00")
    assert item.line_total == Decimal("5664000.00")

    assert quotation.subtotal == Decimal("5664000.00")
    assert quotation.vat_amount == Decimal("849600.00")
    assert quotation.vat_separate is True
    assert quotation.grand_total == Decimal("6513600.00")
    assert quotation.validity_days == 45
    assert quotation.delivery_days == 24
    assert quotation.advance_pct == Decimal("10")
    assert quotation.remaining_days == 45

    assert contract.supplier_name == "Padma Textile Mills Ltd"
    assert contract.delivery_days == 24
    assert contract.advance_pct == Decimal("10")
    assert contract.remaining_days == 45
    assert contract.penalty_rate_pct == Decimal("1")
    assert contract.penalty_basis == "order_value_per_week"
    assert contract.vat_separate is True


def test_generated_pack_layout_still_extracts():
    info = PDFExtractor.extract_document("data/input/pack-01_combined.pdf")
    quotation, contract = StructuredExtractor.extract_combined_document(info)

    assert quotation.supplier_name == "Vertex Textiles & Trims Ltd"
    assert quotation.quotation_no == "QUO-PACK-01-2026"
    assert len(quotation.items) == 5
    assert quotation.subtotal == Decimal("7140000.00")
    assert quotation.vat_amount == Decimal("1071000.00")
    assert quotation.grand_total == Decimal("8211000.00")
    assert contract.penalty_rate_pct == Decimal("0.5")
    assert contract.penalty_basis == "order_value_per_week"


def test_pack_10_wrapped_total_is_extracted_and_reviewed():
    pr_items = PurchaseRequestService.load_purchase_request()
    workflow = build_verification_workflow()
    out = workflow.invoke({
        "supplier_id": "PACK-10",
        "document_path": "data/input/pack-10_combined.pdf",
        "purchase_request_items": pr_items,
    })

    quotation = out["quotation_details"]
    assert quotation.grand_total == Decimal("7260000.00")
    assert quotation.vat_amount is None
    assert quotation.vat_separate is False
    assert out["final_decision"] == "NEEDS_HUMAN_REVIEW"
    triggered = {r.rule_id for r in out["rule_results"] if r.status in ("FAILED", "REVIEW_REQUIRED")}
    assert {"H05", "H06"}.issubset(triggered)
