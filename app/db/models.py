"""
SQLAlchemy ORM models for Supplier Document Verification.
"""
from datetime import datetime
import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from app.db.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id = Column(String(64), primary_key=True)  # e.g., 'PR-2026-AGL-0089'
    company_name = Column(String(255), nullable=False, default="Aamar Garments Ltd")
    department = Column(String(255), nullable=False, default="Procurement Directorate")
    created_date = Column(String(32), nullable=False, default="2026-10-15")
    currency = Column(String(16), nullable=False, default="BDT")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    items = relationship("PurchaseRequestItem", back_populates="purchase_request", cascade="all, delete-orphan")
    verifications = relationship("Verification", back_populates="purchase_request")

class PurchaseRequestItem(Base):
    __tablename__ = "purchase_request_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pr_id = Column(String(64), ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False)
    line_number = Column(Integer, nullable=False, default=1)
    item_code = Column(String(64), nullable=False)
    item_description = Column(String(255), nullable=False)
    specification = Column(Text, nullable=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(32), nullable=False)
    max_unit_price = Column(Float, nullable=False)
    target_delivery_days = Column(Integer, nullable=False, default=30)
    required_vat_rate = Column(Float, nullable=False, default=15.0)
    max_advance_pct = Column(Float, nullable=False, default=20.0)

    # Relationships
    purchase_request = relationship("PurchaseRequest", back_populates="items")

    __table_args__ = (
        Index("ix_pr_item_pr_code", "pr_id", "item_code"),
    )

class Verification(Base):
    __tablename__ = "verifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    supplier_id = Column(String(64), nullable=False, index=True)
    supplier_name = Column(String(255), nullable=False, default="Unknown Supplier")
    purchase_request_id = Column(String(64), ForeignKey("purchase_requests.id"), nullable=False, default="PR-2026-AGL-0089")
    
    # Decisions & Status
    overall_decision = Column(String(32), nullable=False, default="NEEDS_HUMAN_REVIEW")  # APPROVED, REJECTED, NEEDS_HUMAN_REVIEW
    processing_status = Column(String(32), nullable=False, default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    
    # Timestamps
    submission_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    completion_timestamp = Column(DateTime, nullable=True)
    
    # Rule evaluation counts
    passed_checks_count = Column(Integer, default=0, nullable=False)
    failed_checks_count = Column(Integer, default=0, nullable=False)
    review_checks_count = Column(Integer, default=0, nullable=False)
    
    # Detailed payloads
    triggered_rule_ids = Column(Text, default="[]", nullable=False)  # JSON list
    verification_notes = Column(Text, default="", nullable=False)
    comparison_results = Column(Text, default="[]", nullable=False)  # JSON list
    quotation_details = Column(Text, default="{}", nullable=False)   # JSON logical section A
    contract_terms = Column(Text, default="{}", nullable=False)      # JSON logical section B
    error_message = Column(Text, nullable=True)

    # Relationships
    purchase_request = relationship("PurchaseRequest", back_populates="verifications")
    documents = relationship("Document", back_populates="verification", cascade="all, delete-orphan")
    validation_results = relationship("ValidationResult", back_populates="verification", cascade="all, delete-orphan")
    human_reviews = relationship("HumanReview", back_populates="verification", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_verification_decision", "overall_decision"),
        Index("ix_verification_submitted", "submission_timestamp"),
    )

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    verification_id = Column(String(36), ForeignKey("verifications.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    document_type = Column(String(128), nullable=False, default="Combined Supplier Document (Quotation + Terms & Conditions)")
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(64), nullable=False, default="application/pdf")
    file_size = Column(Integer, nullable=False, default=0)
    page_count = Column(Integer, nullable=False, default=1)
    upload_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    extraction_status = Column(String(32), nullable=False, default="PENDING")  # PENDING, SUCCESS, FAILED

    # Relationships
    verification = relationship("Verification", back_populates="documents")

class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    verification_id = Column(String(36), ForeignKey("verifications.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(16), nullable=False)
    rule_name = Column(String(128), nullable=False)
    result = Column(String(32), nullable=False)  # PASS, FAIL, REVIEW, NOT_EVALUABLE
    severity = Column(String(32), nullable=False, default="REJECT")  # REJECT, HUMAN_REVIEW, INFO
    actual_value = Column(Text, default="", nullable=False)
    expected_value = Column(Text, default="", nullable=False)
    document = Column(String(64), default="", nullable=False)
    page = Column(Integer, default=1, nullable=False)
    evidence_text = Column(Text, default="", nullable=False)
    explanation = Column(Text, default="", nullable=False)

    # Relationships
    verification = relationship("Verification", back_populates="validation_results")

    __table_args__ = (
        Index("ix_val_result_rule", "verification_id", "rule_id"),
    )

class HumanReview(Base):
    __tablename__ = "human_reviews"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    verification_id = Column(String(36), ForeignKey("verifications.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_name = Column(String(128), nullable=False)
    reviewer_role = Column(String(128), nullable=False, default="Procurement Auditor")
    review_decision = Column(String(64), nullable=False)  # APPROVED_WITH_DISPENSATION, REJECTED, ESCALATED
    comments = Column(Text, default="", nullable=False)
    dispensation_reason = Column(Text, default="", nullable=False)
    reviewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    verification = relationship("Verification", back_populates="human_reviews")
