"""
Pydantic data models for structured supplier document verification.
Strict schema validation with exact evidence tracking and Decimal arithmetic.
"""

from decimal import Decimal
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator

class QuotationLineItem(BaseModel):
    item_code: str = Field(..., description="Item code matching purchase request, e.g. ITEM-A")
    description: str = Field(..., description="Normalized item description")
    quantity: Decimal = Field(..., description="Quoted quantity as exact Decimal")
    unit: str = Field(..., description="Measurement unit (metre, piece, cone, etc.)")
    unit_price: Decimal = Field(..., description="Quoted unit price in BDT as exact Decimal")
    line_total: Decimal = Field(..., description="Quoted line total in BDT as exact Decimal")
    source_text: str = Field(default="", description="Exact source text snippet from document")
    page_number: int = Field(default=1, description="Page number where item was found")

class ExtractedQuotation(BaseModel):
    supplier_name: str
    quotation_no: str
    pr_reference: str
    date_str: str
    tin: Optional[str] = None
    bin: Optional[str] = None
    validity_days: Optional[int] = None
    delivery_days: Optional[int] = None
    advance_pct: Optional[Decimal] = None
    remaining_days: Optional[int] = None
    items: List[QuotationLineItem] = Field(default_factory=list)
    subtotal: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = None
    vat_separate: bool = True
    grand_total: Optional[Decimal] = None
    raw_text: str = ""
    page_count: int = 1
    doc_hash: str = ""
    source_filename: str = ""

class ExtractedContract(BaseModel):
    agreement_no: str
    supplier_name: str
    pr_reference: str
    tin: Optional[str] = None
    bin: Optional[str] = None
    delivery_days: Optional[int] = None
    advance_pct: Optional[Decimal] = None
    remaining_days: Optional[int] = None
    penalty_clause: Optional[str] = None
    penalty_rate_pct: Optional[Decimal] = None
    penalty_basis: Optional[str] = None
    vat_separate: bool = True
    raw_text: str = ""
    page_count: int = 1
    doc_hash: str = ""
    source_filename: str = ""

class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    status: Literal["PASS", "FAILED", "REVIEW_REQUIRED", "NOT_EVALUABLE"]
    actual_value: str
    expected_value: str
    severity: Literal["REJECT", "HUMAN_REVIEW", "INFO"]
    document: str
    page: int
    evidence: str
    explanation: str

class EvidenceRecord(BaseModel):
    rule_id: str
    document: str
    page_number: int
    exact_text: str
    extracted_value: str
    expected_condition: str
    calculation: Optional[str] = None
    status: str
    decision_effect: Literal["REJECT", "NEEDS_HUMAN_REVIEW", "APPROVE", "NONE"]

class PurchaseRequestItem(BaseModel):
    item_code: str
    item_description: str
    specification: str
    quantity: Decimal
    unit: str
    max_unit_price: Decimal
    target_delivery_days: int
    required_vat_rate: Decimal
    max_advance_pct: Decimal

class SupplierPack(BaseModel):
    id: str
    supplier_name: str
    document_path: str = ""
    quotation_path: str = ""
    contract_path: str = ""
    is_paired: bool = True
    pairing_confidence: float = 1.0
    inspection_notes: str = ""

class CombinedDocumentExtraction(BaseModel):
    document_id: str = ""
    source_filename: str = ""
    doc_hash: str = ""
    page_count: int = 1
    supplier_name: str = ""
    pr_reference: str = ""
    tin: Optional[str] = None
    bin: Optional[str] = None
    quotation_details: ExtractedQuotation
    contract_terms: ExtractedContract
    raw_text: str = ""

class VerificationResult(BaseModel):
    supplier_id: str
    supplier_name: str
    final_decision: Literal["APPROVE", "REJECT", "NEEDS_HUMAN_REVIEW"]
    triggered_rules: List[RuleResult] = Field(default_factory=list)
    all_rule_results: List[RuleResult] = Field(default_factory=list)
    evidence_records: List[EvidenceRecord] = Field(default_factory=list)
    quotation_data: Optional[ExtractedQuotation] = None
    contract_data: Optional[ExtractedContract] = None
    timestamp: str = ""
    human_override: Optional[Dict[str, Any]] = None
