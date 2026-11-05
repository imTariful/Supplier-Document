"""Tests for immutable machine decisions, effective decisions and reset cleanup."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import service as service_module
from app.db.models import Base, Document, Verification


@pytest.fixture()
def db_env(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    uploaded_file = uploads_dir / "verification-1_combined.pdf"
    uploaded_file.write_bytes(b"%PDF-1.4 test")

    monkeypatch.setattr(service_module, "SessionLocal", TestingSession)
    monkeypatch.setattr(service_module, "UPLOADS_DIR", uploads_dir)

    session = TestingSession()
    session.add(Verification(
        id="verification-1",
        supplier_id="PACK-TEST",
        supplier_name="Test Supplier Ltd",
        purchase_request_id="PR-2026-114",
        overall_decision="NEEDS_HUMAN_REVIEW",
        processing_status="COMPLETED",
        submission_timestamp=datetime.utcnow(),
        passed_checks_count=8,
        failed_checks_count=0,
        review_checks_count=1,
        triggered_rule_ids=json.dumps(["H01"]),
        verification_notes="Minor price deviation.",
        comparison_results="[]",
        quotation_details="{}",
        contract_terms="{}",
    ))
    session.add(Document(
        id="document-1",
        verification_id="verification-1",
        original_filename="supplier.pdf",
        document_type="Combined Supplier Document (Quotation + Terms & Conditions)",
        file_path=str(uploaded_file),
        mime_type="application/pdf",
        file_size=uploaded_file.stat().st_size,
        page_count=1,
        upload_timestamp=datetime.utcnow(),
        extraction_status="SUCCESS",
    ))
    session.commit()
    session.close()

    yield uploaded_file, TestingSession
    engine.dispose()


def test_human_review_does_not_overwrite_machine_decision(db_env):
    uploaded_file, _ = db_env

    before = service_module.VerificationDBService.get_dashboard_summary()
    assert before["machine_needs_human_review"] == 1
    assert before["pending_reviews"] == 1

    outcome = service_module.VerificationDBService.submit_human_review(
        verification_id="verification-1",
        reviewer_name="Auditor One",
        reviewer_role="Procurement Auditor",
        review_decision="APPROVED_WITH_DISPENSATION",
        comments="Acceptable minor deviation.",
        dispensation_reason="Within commercial tolerance.",
    )

    assert outcome["machine_decision"] == "NEEDS_HUMAN_REVIEW"
    assert outcome["effective_decision"] == "APPROVED"

    detail = service_module.VerificationDBService.get_verification_by_id("verification-1")
    assert detail["overall_decision"] == "NEEDS_HUMAN_REVIEW"
    assert detail["machine_decision"] == "NEEDS_HUMAN_REVIEW"
    assert detail["human_review_decision"] == "APPROVED_WITH_DISPENSATION"
    assert detail["effective_decision"] == "APPROVED"
    assert detail["human_review"]["reviewer_name"] == "Auditor One"

    after = service_module.VerificationDBService.get_dashboard_summary()
    assert after["machine_needs_human_review"] == 1
    assert after["needs_human_review"] == 0
    assert after["approved"] == 1
    assert after["pending_reviews"] == 0
    assert service_module.VerificationDBService.get_pending_reviews() == []
    assert uploaded_file.exists()


def test_reset_removes_database_rows_and_uploaded_files(db_env):
    uploaded_file, _ = db_env

    result = service_module.VerificationDBService.reset_all_data(preserve_pr=True)

    assert result["success"] is True
    assert result["uploads_deleted"] == 1
    assert not uploaded_file.exists()
    assert uploaded_file.parent.exists()
    assert service_module.VerificationDBService.get_verification_by_id("verification-1") is None
    assert service_module.VerificationDBService.get_dashboard_summary()["total_verifications"] == 0
