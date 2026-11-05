"""
Comprehensive unit test suite for business rules and mandatory boundary tests.
All boundary conditions specified in Section 20 are systematically tested with Decimal precision.
"""

import pytest
from decimal import Decimal
from app.schemas.models import QuotationLineItem, PurchaseRequestItem
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

@pytest.fixture
def sample_pr_item():
    return PurchaseRequestItem(
        item_code="ITEM-A",
        item_description="Cotton twill fabric, 280 gsm",
        specification="280 gsm",
        quantity=Decimal("12000"),
        unit="metre",
        max_unit_price=Decimal("480.00"),
        target_delivery_days=30,
        required_vat_rate=Decimal("15.0"),
        max_advance_pct=Decimal("20.0")
    )

# --- 1. PRICE BOUNDARY TESTS ---
def test_price_at_exact_maximum(sample_pr_item):
    """Quoted price exactly equal to maximum (৳480.00) -> PASS"""
    item = QuotationLineItem(
        item_code="ITEM-A", description="Fabric", quantity=Decimal("12000"),
        unit="metre", unit_price=Decimal("480.00"), line_total=Decimal("5760000.00")
    )
    res = evaluate_price_rules([item], {"ITEM-A": sample_pr_item})
    assert len(res) == 1
    assert res[0].status == "PASS"

def test_price_slightly_above_maximum(sample_pr_item):
    """Quoted price slightly above max (৳485.00, +1.04% <= 3%) -> HUMAN_REVIEW (H01)"""
    item = QuotationLineItem(
        item_code="ITEM-A", description="Fabric", quantity=Decimal("12000"),
        unit="metre", unit_price=Decimal("485.00"), line_total=Decimal("5820000.00")
    )
    res = evaluate_price_rules([item], {"ITEM-A": sample_pr_item})
    assert len(res) == 1
    assert res[0].rule_id == "H01"
    assert res[0].status == "REVIEW_REQUIRED"
    assert res[0].severity == "HUMAN_REVIEW"

def test_price_exactly_3_percent_above(sample_pr_item):
    """Quoted price exactly 3.0% above maximum (480 * 1.03 = ৳494.40) -> HUMAN_REVIEW (H01)"""
    item = QuotationLineItem(
        item_code="ITEM-A", description="Fabric", quantity=Decimal("12000"),
        unit="metre", unit_price=Decimal("494.40"), line_total=Decimal("5932800.00")
    )
    res = evaluate_price_rules([item], {"ITEM-A": sample_pr_item})
    assert len(res) == 1
    assert res[0].rule_id == "H01"
    assert res[0].status == "REVIEW_REQUIRED"

def test_price_above_3_percent(sample_pr_item):
    """Quoted price above 3.0% (৳495.00, +3.125%) -> REJECT (R01)"""
    item = QuotationLineItem(
        item_code="ITEM-A", description="Fabric", quantity=Decimal("12000"),
        unit="metre", unit_price=Decimal("495.00"), line_total=Decimal("5940000.00")
    )
    res = evaluate_price_rules([item], {"ITEM-A": sample_pr_item})
    assert len(res) == 1
    assert res[0].rule_id == "R01"
    assert res[0].status == "FAILED"
    assert res[0].severity == "REJECT"

# --- 2. ADVANCE PAYMENT BOUNDARY TESTS ---
def test_advance_exactly_20_percent():
    """Advance payment exactly 20.0% -> PASS"""
    res = evaluate_advance_rules(Decimal("20.0"))
    assert res.status == "PASS"

def test_advance_20_point_01_percent():
    """Advance payment 20.01% -> REJECT (R02)"""
    res = evaluate_advance_rules(Decimal("20.01"))
    assert res.rule_id == "R02"
    assert res.status == "FAILED"
    assert res.severity == "REJECT"

def test_advance_missing():
    """Advance payment missing / None -> HUMAN_REVIEW (H08)"""
    res = evaluate_advance_rules(None)
    assert res.status == "REVIEW_REQUIRED"
    assert res.severity == "HUMAN_REVIEW"

# --- 3. QUANTITY BOUNDARY TESTS ---
def test_quantity_exact_5_percent_deviation(sample_pr_item):
    """Quantity deviation exactly 5.0% (12,000 * 0.95 = 11,400) -> PASS (no review)"""
    item = QuotationLineItem(
        item_code="ITEM-A", description="Fabric", quantity=Decimal("11400"),
        unit="metre", unit_price=Decimal("470.00"), line_total=Decimal("5358000.00")
    )
    res = evaluate_quantity_rules([item], {"ITEM-A": sample_pr_item})
    assert res[0].status == "PASS"

def test_quantity_greater_than_5_percent_deviation(sample_pr_item):
    """Quantity deviation > 5.0% (10,000 vs 12,000 = -16.67%) -> HUMAN_REVIEW (H02)"""
    item = QuotationLineItem(
        item_code="ITEM-A", description="Fabric", quantity=Decimal("10000"),
        unit="metre", unit_price=Decimal("470.00"), line_total=Decimal("4700000.00")
    )
    res = evaluate_quantity_rules([item], {"ITEM-A": sample_pr_item})
    assert res[0].rule_id == "H02"
    assert res[0].status == "REVIEW_REQUIRED"
    assert res[0].severity == "HUMAN_REVIEW"

# --- 4. DELIVERY PERIOD BOUNDARY TESTS ---
def test_delivery_30_days():
    """Delivery promised in 30 days -> PASS"""
    res = evaluate_delivery_rules(30)
    assert res.status == "PASS"

def test_delivery_31_days():
    """Delivery promised in 31 days -> HUMAN_REVIEW (H04)"""
    res = evaluate_delivery_rules(31)
    assert res.rule_id == "H04"
    assert res.status == "REVIEW_REQUIRED"

def test_delivery_45_days():
    """Delivery promised in exactly 45 days -> HUMAN_REVIEW (H04)"""
    res = evaluate_delivery_rules(45)
    assert res.rule_id == "H04"
    assert res.status == "REVIEW_REQUIRED"

def test_delivery_46_days():
    """Delivery promised in 46 days -> REJECT (R06)"""
    res = evaluate_delivery_rules(46)
    assert res.rule_id == "R06"
    assert res.status == "FAILED"
    assert res.severity == "REJECT"

# --- 5. PAYMENT TERMS BOUNDARY TESTS ---
def test_payment_exactly_30_days():
    """Payment 30 days after delivery -> PASS"""
    res = evaluate_payment_terms_rules(30)
    assert res.status == "PASS"

def test_payment_exactly_60_days():
    """Payment 60 days after delivery -> PASS"""
    res = evaluate_payment_terms_rules(60)
    assert res.status == "PASS"

def test_payment_less_than_30_days():
    """Payment 20 days after delivery -> HUMAN_REVIEW (H03)"""
    res = evaluate_payment_terms_rules(20)
    assert res.rule_id == "H03"
    assert res.status == "REVIEW_REQUIRED"

def test_payment_greater_than_60_days():
    """Payment 75 days after delivery -> HUMAN_REVIEW (H03)"""
    res = evaluate_payment_terms_rules(75)
    assert res.rule_id == "H03"
    assert res.status == "REVIEW_REQUIRED"

def test_payment_missing_reference_date():
    """Payment missing / unclear -> HUMAN_REVIEW (H03)"""
    res = evaluate_payment_terms_rules(None)
    assert res.rule_id == "H03"
    assert res.status == "REVIEW_REQUIRED"

# --- 6. PENALTY CLAUSE TESTS ---
def test_penalty_missing_clause():
    """No penalty clause in contract -> REJECT (R03)"""
    res = evaluate_penalty_rules(None, None, None)
    assert res.rule_id == "R03"
    assert res.status == "FAILED"
    assert res.severity == "REJECT"

def test_penalty_insufficient_rate_0_25():
    """Penalty rate 0.25% per week (< 0.5%) -> REJECT (R07)"""
    res = evaluate_penalty_rules("0.25% per week", Decimal("0.25"), "order_value")
    assert res.rule_id == "R07"
    assert res.status == "FAILED"
    assert res.severity == "REJECT"

def test_penalty_compliant_rate_0_5():
    """Penalty rate 0.5% per week -> PASS"""
    res = evaluate_penalty_rules("0.5% per week", Decimal("0.5"), "order_value")
    assert res.status == "PASS"

def test_penalty_rate_greater_than_0_5():
    """Penalty rate 0.75% per week -> PASS"""
    res = evaluate_penalty_rules("0.75% per week", Decimal("0.75"), "order_value")
    assert res.status == "PASS"

# --- 7. TAX IDENTITY & VAT TESTS ---
def test_tax_identity_missing_tin_and_bin():
    """Missing both TIN and BIN -> REJECT (R04 and R05)"""
    res = evaluate_tax_identity_rules(None, None)
    rule_ids = [r.rule_id for r in res if r.status == "FAILED"]
    assert "R04" in rule_ids
    assert "R05" in rule_ids

def test_vat_not_separate():
    """VAT not separately itemized -> HUMAN_REVIEW (H05)"""
    res = evaluate_vat_rules(False, Decimal("100000.00"), None)
    assert res.rule_id == "H05"
    assert res.status == "REVIEW_REQUIRED"

# --- 8. ARITHMETIC TESTS ---
def test_arithmetic_subtotal_mismatch():
    """Stated subtotal does not match sum of items -> HUMAN_REVIEW (H06)"""
    item = QuotationLineItem(
        item_code="ITEM-A", description="Fabric", quantity=Decimal("100"),
        unit="metre", unit_price=Decimal("10.00"), line_total=Decimal("1000.00")
    )
    res = evaluate_arithmetic_rules([item], stated_subtotal=Decimal("1500.00"), stated_vat=Decimal("225.00"), stated_grand_total=Decimal("1725.00"))
    rule_ids = [r.rule_id for r in res if r.status == "REVIEW_REQUIRED"]
    assert "H06" in rule_ids

def test_validity_less_than_30_days():
    """Quotation validity 20 days -> HUMAN_REVIEW (H07)"""
    res = evaluate_validity_rules(20)
    assert res.rule_id == "H07"
    assert res.status == "REVIEW_REQUIRED"

def test_validity_compliant():
    """Quotation validity 45 days -> PASS"""
    res = evaluate_validity_rules(45)
    assert res.status == "PASS"
