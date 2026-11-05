"""
Pydantic Schemas for validation and serialization in Supplier Document Verification.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class PurchaseRequestItemSchema(BaseModel):
    id: Optional[int] = None
    pr_id: str
    line_number: int
    item_code: str
    item_description: str
    specification: Optional[str] = None
    quantity: float
    unit: str
    max_unit_price: float
    target_delivery_days: int = 30
    required_vat_rate: float = 15.0
    max_advance_pct: float = 20.0

class PurchaseRequestSchema(BaseModel):
    id: str
    company_name: str
    department: str
    created_date: str
    currency: str
    items: List[PurchaseRequestItemSchema] = []

class DocumentSchema(BaseModel):
    id: str
    verification_id: str
    original_filename: str
    document_type: str
    file_path: str
    mime_type: str
    file_size: int
    page_count: int
    upload_timestamp: datetime
    extraction_status: str

class ValidationResultSchema(BaseModel):
    id: str
    verification_id: str
    rule_id: str
    rule_name: str
    result: str  # PASS, FAIL, REVIEW, NOT_EVALUABLE
    severity: str
    actual_value: str
    expected_value: str
    document: str
    page: int
    evidence_text: str
    explanation: str

class HumanReviewCreateSchema(BaseModel):
    reviewer_name: str
    reviewer_role: str = "Procurement Auditor"
    review_decision: str  # APPROVED_WITH_DISPENSATION, REJECTED, ESCALATED
    comments: str = ""
    dispensation_reason: str = ""

class HumanReviewSchema(HumanReviewCreateSchema):
    id: str
    verification_id: str
    reviewed_at: datetime

class ComparisonItemSchema(BaseModel):
    item_code: str
    item_description: str
    specification: Optional[str] = ""
    requested_qty: float
    quoted_qty: float
    unit: str
    qty_deviation_pct: float
    max_unit_price: float
    quoted_unit_price: float
    price_deviation_pct: float

class VerificationListItemSchema(BaseModel):
    id: str
    supplier_id: str
    supplier_name: str
    purchase_request_id: str
    overall_decision: str
    processing_status: str
    submission_timestamp: datetime
    completion_timestamp: Optional[datetime] = None
    passed_checks_count: int
    failed_checks_count: int
    review_checks_count: int
    triggered_rule_ids: List[str] = []
    documents_count: int = 0
    has_human_review: bool = False
    human_review: Optional[HumanReviewSchema] = None

class VerificationDetailSchema(VerificationListItemSchema):
    verification_notes: str = ""
    comparison_results: List[ComparisonItemSchema] = []
    quotation_details: Optional[Dict[str, Any]] = None
    contract_terms: Optional[Dict[str, Any]] = None
    documents: List[DocumentSchema] = []
    validation_results: List[ValidationResultSchema] = []
    human_reviews: List[HumanReviewSchema] = []
    error_message: Optional[str] = None

class DashboardSummarySchema(BaseModel):
    total_verifications: int
    approved: int
    rejected: int
    needs_human_review: int
    recent_verifications: List[VerificationListItemSchema] = []
