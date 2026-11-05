"""
Typed state for the LangGraph supplier document verification workflow.
Supports single combined supplier document (Quotation + Terms & Conditions)
with backwards compatibility for separate inputs.
"""

from typing import Dict, List, Optional, Any, TypedDict
from app.schemas.models import (
    ExtractedQuotation,
    ExtractedContract,
    PurchaseRequestItem,
    RuleResult,
    EvidenceRecord,
    VerificationResult
)

class VerificationWorkflowState(TypedDict, total=False):
    # Pack identity & files
    supplier_id: str
    supplier_name: str
    document_path: str  # Combined document path
    quotation_path: str  # Kept for compatibility
    contract_path: str   # Kept for compatibility

    # Document identification & association
    pack_identification: Dict[str, Any]
    association_confidence: float

    # Raw document extraction
    document_doc_info: Optional[Dict[str, Any]]
    quotation_doc_info: Optional[Dict[str, Any]]
    contract_doc_info: Optional[Dict[str, Any]]
    extraction_quality_score: float
    is_scanned: bool
    ocr_confidence: float

    # Structured extraction into two logical sections
    quotation_details: Optional[ExtractedQuotation]
    contract_terms: Optional[ExtractedContract]
    structured_quotation: Optional[ExtractedQuotation]
    structured_contract: Optional[ExtractedContract]
    extraction_errors: List[str]

    # Reference data
    purchase_request_items: Dict[str, PurchaseRequestItem]

    # Intermediate verification steps
    evidence_verified: bool
    evidence_issues: List[str]
    comparison_results: List[Dict[str, Any]]
    contract_compliance_results: List[Dict[str, Any]]
    contract_validation_passed: bool
    financial_validation_results: List[Dict[str, Any]]
    financial_validation_passed: bool

    # Final outcomes
    rule_results: List[RuleResult]
    triggered_rules: List[RuleResult]
    triggered_rule_ids: List[str]
    evidence_records: List[EvidenceRecord]
    final_decision: str  # "APPROVE" | "REJECT" | "NEEDS_HUMAN_REVIEW"
    final_report: Dict[str, Any]
    status: str
