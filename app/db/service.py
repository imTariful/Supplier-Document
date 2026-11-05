"""
Database service functions for Supplier Document Verification.
Implements complete CRUD, dashboard aggregation, and LangGraph workflow persistence.
"""
import os
import json
import shutil
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, Any, List

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import pymupdf as fitz
from sqlalchemy import or_, desc
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, UPLOADS_DIR
from app.db.models import (
    PurchaseRequest,
    PurchaseRequestItem,
    Verification,
    Document,
    ValidationResult,
    HumanReview,
)
from app.workflow.graph import build_verification_workflow
from app.services.pr_service import PurchaseRequestService

def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


APPROVING_REVIEW_DECISIONS = {"APPROVED", "APPROVE", "APPROVED_WITH_DISPENSATION"}
REJECTING_REVIEW_DECISIONS = {"REJECTED", "REJECT"}


def _effective_decision(machine_decision: str, review_decision: Optional[str]) -> str:
    """
    Resolve the business outcome without ever mutating the machine decision.

    A recorded auditor approval/rejection becomes the effective outcome; an
    escalation (or no review) leaves the machine decision in force.
    """
    decision = (review_decision or "").strip().upper()
    if decision in APPROVING_REVIEW_DECISIONS:
        return "APPROVED"
    if decision in REJECTING_REVIEW_DECISIONS:
        return "REJECTED"
    return machine_decision


def _review_payload(review: Optional[HumanReview]) -> Optional[Dict[str, Any]]:
    if review is None:
        return None
    return {
        "reviewer_name": review.reviewer_name,
        "reviewer_role": review.reviewer_role,
        "review_decision": review.review_decision,
        "comments": review.comments,
        "dispensation_reason": review.dispensation_reason,
        "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
    }


def _decision_fields(machine_decision: str, review: Optional[HumanReview]) -> Dict[str, Any]:
    review_decision = review.review_decision if review else None
    return {
        "machine_decision": machine_decision,
        "human_review_decision": review_decision,
        "effective_decision": _effective_decision(machine_decision, review_decision),
    }

class VerificationDBService:

    @staticmethod
    def get_dashboard_summary() -> Dict[str, Any]:
        """
        Returns aggregated summary statistics and recent verifications from SQLite.
        """
        session = SessionLocal()
        try:
            total = session.query(Verification).count()
            recent = (
                session.query(Verification)
                .order_by(desc(Verification.submission_timestamp))
                .limit(5)
                .all()
            )

            # Machine counts are retained for auditability; effective counts
            # reflect recorded human decisions without changing the machine ones.
            machine_approved = session.query(Verification).filter(Verification.overall_decision == "APPROVED").count()
            machine_rejected = session.query(Verification).filter(Verification.overall_decision == "REJECTED").count()
            machine_needs_review = session.query(Verification).filter(Verification.overall_decision == "NEEDS_HUMAN_REVIEW").count()

            effective_counts = {"APPROVED": 0, "REJECTED": 0, "NEEDS_HUMAN_REVIEW": 0}
            pending_reviews = 0
            for v in session.query(Verification).all():
                latest_review = (
                    session.query(HumanReview)
                    .filter_by(verification_id=v.id)
                    .order_by(desc(HumanReview.reviewed_at))
                    .first()
                )
                effective = _effective_decision(
                    v.overall_decision,
                    latest_review.review_decision if latest_review else None,
                )
                effective_counts[effective] = effective_counts.get(effective, 0) + 1
                if effective == "NEEDS_HUMAN_REVIEW" and (
                    latest_review is None
                    or (latest_review.review_decision or "").upper() == "ESCALATED"
                ):
                    pending_reviews += 1

            recent_list = []
            for v in recent:
                latest_review = (
                    session.query(HumanReview)
                    .filter_by(verification_id=v.id)
                    .order_by(desc(HumanReview.reviewed_at))
                    .first()
                )
                recent_list.append({
                    "id": v.id,
                    "supplier_id": v.supplier_id,
                    "supplier_name": v.supplier_name,
                    "purchase_request_id": v.purchase_request_id,
                    "overall_decision": v.overall_decision,
                    **_decision_fields(v.overall_decision, latest_review),
                    "processing_status": v.processing_status,
                    "submission_timestamp": v.submission_timestamp.isoformat() if v.submission_timestamp else None,
                    "completion_timestamp": v.completion_timestamp.isoformat() if v.completion_timestamp else None,
                    "passed_checks_count": v.passed_checks_count,
                    "failed_checks_count": v.failed_checks_count,
                    "review_checks_count": v.review_checks_count,
                    "triggered_rule_ids": json.loads(v.triggered_rule_ids or "[]"),
                    "documents_count": len(v.documents),
                    "has_human_review": latest_review is not None,
                    "human_review": _review_payload(latest_review),
                })

            return {
                "total_verifications": total,
                "approved": effective_counts.get("APPROVED", 0),
                "rejected": effective_counts.get("REJECTED", 0),
                "needs_human_review": effective_counts.get("NEEDS_HUMAN_REVIEW", 0),
                "machine_approved": machine_approved,
                "machine_rejected": machine_rejected,
                "machine_needs_human_review": machine_needs_review,
                "pending_reviews": pending_reviews,
                "recent_verifications": recent_list
            }
        finally:
            session.close()

    @staticmethod
    def get_verifications(search: Optional[str] = None, decision: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Lists verifications with optional search and decision filter.
        """
        session = SessionLocal()
        try:
            query = session.query(Verification)

            if search and search.strip():
                s = f"%{search.strip()}%"
                query = query.filter(or_(
                    Verification.supplier_id.ilike(s),
                    Verification.supplier_name.ilike(s),
                    Verification.id.ilike(s)
                ))

            rows = query.order_by(desc(Verification.submission_timestamp)).all()

            requested_decision = None
            if decision and decision.upper() != "ALL":
                requested_decision = decision.upper()
                if requested_decision == "APPROVE":
                    requested_decision = "APPROVED"
                elif requested_decision == "REJECT":
                    requested_decision = "REJECTED"

            serialized = []
            for v in rows:
                latest_review = (
                    session.query(HumanReview)
                    .filter_by(verification_id=v.id)
                    .order_by(desc(HumanReview.reviewed_at))
                    .first()
                )
                fields = _decision_fields(v.overall_decision, latest_review)
                if requested_decision and fields["effective_decision"] != requested_decision:
                    continue
                serialized.append({
                    "id": v.id,
                    "supplier_id": v.supplier_id,
                    "supplier_name": v.supplier_name,
                    "purchase_request_id": v.purchase_request_id,
                    "overall_decision": v.overall_decision,
                    **fields,
                    "processing_status": v.processing_status,
                    "submission_timestamp": v.submission_timestamp.isoformat() if v.submission_timestamp else None,
                    "completion_timestamp": v.completion_timestamp.isoformat() if v.completion_timestamp else None,
                    "passed_checks_count": v.passed_checks_count,
                    "failed_checks_count": v.failed_checks_count,
                    "review_checks_count": v.review_checks_count,
                    "triggered_rule_ids": json.loads(v.triggered_rule_ids or "[]"),
                    "documents_count": len(v.documents),
                    "has_human_review": latest_review is not None,
                    "human_review": _review_payload(latest_review),
                })

            total_count = len(serialized)
            results = serialized[offset:offset + limit]

            return {
                "verifications": results,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
        finally:
            session.close()

    @staticmethod
    def get_verification_by_id(verification_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves full details of a single verification by UUID or supplier_id.
        """
        session = SessionLocal()
        try:
            v = session.query(Verification).filter(
                or_(Verification.id == verification_id, Verification.supplier_id == verification_id)
            ).first()

            if not v:
                return None

            docs = [
                {
                    "id": d.id,
                    "verification_id": d.verification_id,
                    "original_filename": d.original_filename,
                    "document_type": d.document_type,
                    "file_path": d.file_path,
                    "mime_type": d.mime_type,
                    "file_size": d.file_size,
                    "page_count": d.page_count,
                    "upload_timestamp": d.upload_timestamp.isoformat() if d.upload_timestamp else None,
                    "extraction_status": d.extraction_status
                }
                for d in v.documents
            ]

            results = [
                {
                    "id": r.id,
                    "verification_id": r.verification_id,
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "result": r.result,
                    "severity": r.severity,
                    "actual_value": r.actual_value,
                    "expected_value": r.expected_value,
                    "document": r.document,
                    "page": r.page,
                    "evidence_text": r.evidence_text,
                    "explanation": r.explanation
                }
                for r in sorted(v.validation_results, key=lambda x: x.rule_id)
            ]

            reviews = [
                {
                    "id": h.id,
                    "verification_id": h.verification_id,
                    "reviewer_name": h.reviewer_name,
                    "reviewer_role": h.reviewer_role,
                    "review_decision": h.review_decision,
                    "comments": h.comments,
                    "dispensation_reason": h.dispensation_reason,
                    "reviewed_at": h.reviewed_at.isoformat() if h.reviewed_at else None
                }
                for h in sorted(v.human_reviews, key=lambda x: x.reviewed_at, reverse=True)
            ]

            comparison_results = []
            try:
                comparison_results = json.loads(v.comparison_results or "[]")
            except Exception:
                comparison_results = []

            quotation_details = {}
            try:
                quotation_details = json.loads(v.quotation_details or "{}")
            except Exception:
                quotation_details = {}

            contract_terms = {}
            try:
                contract_terms = json.loads(v.contract_terms or "{}")
            except Exception:
                contract_terms = {}

            latest_review = (
                max(v.human_reviews, key=lambda h: h.reviewed_at)
                if v.human_reviews else None
            )
            return {
                "id": v.id,
                "supplier_id": v.supplier_id,
                "supplier_name": v.supplier_name,
                "purchase_request_id": v.purchase_request_id,
                "overall_decision": v.overall_decision,
                **_decision_fields(v.overall_decision, latest_review),
                "processing_status": v.processing_status,
                "submission_timestamp": v.submission_timestamp.isoformat() if v.submission_timestamp else None,
                "completion_timestamp": v.completion_timestamp.isoformat() if v.completion_timestamp else None,
                "passed_checks_count": v.passed_checks_count,
                "failed_checks_count": v.failed_checks_count,
                "review_checks_count": v.review_checks_count,
                "triggered_rule_ids": json.loads(v.triggered_rule_ids or "[]"),
                "verification_notes": v.verification_notes or "",
                "comparison_results": comparison_results,
                "quotation_details": quotation_details,
                "contract_terms": contract_terms,
                "documents": docs,
                "document": docs[0] if docs else None,
                "validation_results": results,
                "human_reviews": reviews,
                "latest_human_review": reviews[0] if reviews else None,
                "human_review": reviews[0] if reviews else None,
                "error_message": v.error_message
            }
        finally:
            session.close()

    @staticmethod
    def get_pending_reviews() -> List[Dict[str, Any]]:
        """
        Returns all verifications requiring human review.
        """
        session = SessionLocal()
        try:
            verifications = (
                session.query(Verification)
                .filter(Verification.overall_decision == "NEEDS_HUMAN_REVIEW")
                .order_by(desc(Verification.submission_timestamp))
                .all()
            )

            out = []
            for v in verifications:
                latest_review = (
                    session.query(HumanReview)
                    .filter_by(verification_id=v.id)
                    .order_by(desc(HumanReview.reviewed_at))
                    .first()
                )
                latest_decision = (latest_review.review_decision or "").upper() if latest_review else ""
                if latest_review is not None and latest_decision not in ("ESCALATED", "NEEDS_HUMAN_REVIEW"):
                    continue

                # Fetch rule results that caused review
                review_rules = [
                    {
                        "rule_id": r.rule_id,
                        "rule_name": r.rule_name,
                        "result": r.result,
                        "severity": r.severity,
                        "evidence_text": r.evidence_text,
                        "explanation": r.explanation,
                        "document": r.document,
                        "page": r.page
                    }
                    for r in v.validation_results
                    if r.result in ("REVIEW", "FAIL")
                ]

                out.append({
                    "id": v.id,
                    "supplier_id": v.supplier_id,
                    "supplier_name": v.supplier_name,
                    "overall_decision": v.overall_decision,
                    **_decision_fields(v.overall_decision, latest_review),
                    "submission_timestamp": v.submission_timestamp.isoformat() if v.submission_timestamp else None,
                    "review_checks_count": v.review_checks_count,
                    "failed_checks_count": v.failed_checks_count,
                    "verification_notes": v.verification_notes,
                    "flagged_issues": review_rules,
                    "has_review": latest_review is not None,
                    "latest_review": _review_payload(latest_review)
                })
            return out
        finally:
            session.close()

    @staticmethod
    def submit_human_review(
        verification_id: str,
        reviewer_name: str,
        reviewer_role: str,
        review_decision: str,
        comments: str = "",
        dispensation_reason: str = ""
    ) -> Dict[str, Any]:
        """
        Saves a human auditor review decision in SQLite.
        """
        session = SessionLocal()
        try:
            v = session.query(Verification).filter(
                or_(Verification.id == verification_id, Verification.supplier_id == verification_id)
            ).first()

            if not v:
                raise ValueError(f"Verification {verification_id} not found.")

            review = HumanReview(
                id=str(uuid.uuid4()),
                verification_id=v.id,
                reviewer_name=reviewer_name.strip(),
                reviewer_role=reviewer_role.strip() or "Procurement Auditor",
                review_decision=review_decision.strip(),
                comments=comments.strip(),
                dispensation_reason=dispensation_reason.strip(),
                reviewed_at=datetime.utcnow()
            )
            session.add(review)

            # The machine decision is immutable.  Human outcomes are recorded
            # separately and exposed as effective_decision by the serializers.
            effective_decision = _effective_decision(v.overall_decision, review.review_decision)

            session.commit()

            return {
                "success": True,
                "review_id": review.id,
                "verification_id": v.id,
                "reviewer_name": review.reviewer_name,
                "review_decision": review.review_decision,
                "machine_decision": v.overall_decision,
                "human_review_decision": review.review_decision,
                "effective_decision": effective_decision,
                "reviewed_at": review.reviewed_at.isoformat()
            }
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def run_and_persist_verification(
        document_src_path: str,
        supplier_id: Optional[str] = None,
        supplier_name: Optional[str] = None,
        original_filename: Optional[str] = None,
        contract_src_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes LangGraph verification workflow on a single combined supplier document PDF,
        safely stores file in ./data/uploads/, and persists all records and logical sections to SQLite.
        """
        session = SessionLocal()
        v_id = str(uuid.uuid4())
        now = datetime.utcnow()

        try:
            # 1. Prepare target file path in ./data/uploads/
            UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            combined_clean_name = f"{v_id}_combined.pdf"
            target_path = str(UPLOADS_DIR / combined_clean_name)

            # If two files were passed (legacy), merge them into one combined PDF
            if contract_src_path and os.path.exists(contract_src_path) and contract_src_path != document_src_path:
                merged_doc = fitz.open()
                with fitz.open(document_src_path) as d1:
                    merged_doc.insert_pdf(d1)
                with fitz.open(contract_src_path) as d2:
                    merged_doc.insert_pdf(d2)
                merged_doc.save(target_path)
                merged_doc.close()
            else:
                shutil.copyfile(document_src_path, target_path)

            doc_size = os.path.getsize(target_path)
            doc_pages = 1
            try:
                with fitz.open(target_path) as doc:
                    doc_pages = len(doc)
            except Exception:
                pass

            # Auto-generate supplier ID if not provided
            effective_supplier_id = (supplier_id or "").strip()
            if not effective_supplier_id:
                effective_supplier_id = f"SUP-{now.strftime('%y%m%d')}-{v_id[:6].upper()}"

            # Determine active purchase request ID
            active_pr = session.query(PurchaseRequest).first()
            active_pr_id = active_pr.id if active_pr else "PR-2026-114"

            # 2. Create Initial Verification record
            v = Verification(
                id=v_id,
                supplier_id=effective_supplier_id,
                supplier_name=supplier_name.strip() if supplier_name else "Extracting...",
                purchase_request_id=active_pr_id,
                overall_decision="NEEDS_HUMAN_REVIEW",
                processing_status="PROCESSING",
                submission_timestamp=now,
                passed_checks_count=0,
                failed_checks_count=0,
                review_checks_count=0,
                triggered_rule_ids="[]",
                verification_notes="Processing verification workflow...",
                comparison_results="[]",
                quotation_details="{}",
                contract_terms="{}"
            )
            session.add(v)
            session.flush()

            # 3. Create ONE Document record for the combined document
            doc_record = Document(
                id=str(uuid.uuid4()),
                verification_id=v_id,
                original_filename=original_filename or Path(document_src_path).name,
                document_type="Combined Supplier Document (Quotation + Terms & Conditions)",
                file_path=target_path,
                mime_type="application/pdf",
                file_size=doc_size,
                page_count=doc_pages,
                upload_timestamp=now,
                extraction_status="PENDING"
            )
            session.add(doc_record)
            session.commit()

            # 4. Invoke LangGraph Verification Engine with single combined document
            workflow = build_verification_workflow()
            pr_items = PurchaseRequestService.load_purchase_request()

            state_input = {
                "supplier_id": effective_supplier_id,
                "document_path": target_path,
                "quotation_path": target_path,
                "contract_path": target_path,
                "purchase_request_items": pr_items
            }

            workflow_result = workflow.invoke(state_input)

            # 5. Interpret results
            raw_decision = workflow_result.get("final_decision", "NEEDS_HUMAN_REVIEW")
            if raw_decision == "APPROVE":
                final_decision = "APPROVED"
            elif raw_decision == "REJECT":
                final_decision = "REJECTED"
            else:
                final_decision = "NEEDS_HUMAN_REVIEW"

            extracted_supplier_name = workflow_result.get("supplier_name") or supplier_name or "Unknown Supplier"
            rule_results = workflow_result.get("rule_results", [])
            comparison_results = workflow_result.get("comparison_results", [])
            triggered_rules = workflow_result.get("triggered_rule_ids") or sorted({
                r.rule_id for r in rule_results
                if r.status in ("FAILED", "REVIEW_REQUIRED")
            })

            structured_q = workflow_result.get("quotation_details") or workflow_result.get("structured_quotation")
            structured_c = workflow_result.get("contract_terms") or workflow_result.get("structured_contract")

            passed_count = sum(1 for r in rule_results if r.status == "PASS")
            failed_count = sum(1 for r in rule_results if r.status == "FAILED")
            review_count = sum(1 for r in rule_results if r.status == "REVIEW_REQUIRED")

            notes_list = [r.explanation for r in rule_results if r.status in ("FAILED", "REVIEW_REQUIRED")]
            verification_notes = "; ".join(notes_list) if notes_list else "All verification checks passed successfully."

            # Update Document extraction status
            doc_record.extraction_status = "SUCCESS" if (structured_q and structured_c) else "FAILED"

            # 6. Save ValidationResult rows referencing the combined document
            for r in rule_results:
                status_str = r.status
                if status_str == "FAILED":
                    result_str = "FAIL"
                elif status_str == "REVIEW_REQUIRED":
                    result_str = "REVIEW"
                elif status_str == "PASS":
                    result_str = "PASS"
                else:
                    result_str = "NOT_EVALUABLE"

                val_res = ValidationResult(
                    id=str(uuid.uuid4()),
                    verification_id=v_id,
                    rule_id=r.rule_id,
                    rule_name=r.rule_name,
                    result=result_str,
                    severity=r.severity,
                    actual_value=str(r.actual_value or ""),
                    expected_value=str(r.expected_value or ""),
                    document=doc_record.original_filename,
                    page=int(r.page or 1),
                    evidence_text=str(r.evidence or ""),
                    explanation=str(r.explanation or "")
                )
                session.add(val_res)

            # 7. Update Verification record with logical sections and decision
            v.supplier_name = extracted_supplier_name
            v.overall_decision = final_decision
            v.processing_status = "COMPLETED"
            v.completion_timestamp = datetime.utcnow()
            v.passed_checks_count = passed_count
            v.failed_checks_count = failed_count
            v.review_checks_count = review_count
            v.triggered_rule_ids = json.dumps(triggered_rules)
            v.verification_notes = verification_notes
            v.comparison_results = json.dumps(comparison_results, default=decimal_serializer)
            v.quotation_details = json.dumps(structured_q.model_dump() if structured_q else {}, default=decimal_serializer)
            v.contract_terms = json.dumps(structured_c.model_dump() if structured_c else {}, default=decimal_serializer)
            session.commit()

            # Return serialized detail
            return VerificationDBService.get_verification_by_id(v_id)

        except Exception as e:
            session.rollback()
            try:
                # Mark verification as failed
                v_fail = session.query(Verification).filter_by(id=v_id).first()
                if v_fail:
                    v_fail.processing_status = "FAILED"
                    v_fail.error_message = str(e)
                    session.commit()
            except Exception:
                pass
            raise e
        finally:
            session.close()

    @staticmethod
    def reset_all_data(preserve_pr: bool = True) -> Dict[str, Any]:
        """
        Deletes all verification records, documents, validation results, and human reviews.
        Preserves reference Purchase Request items.
        Leaves SQLite database in completely clean state.
        """
        session = SessionLocal()
        try:
            session.query(HumanReview).delete()
            session.query(ValidationResult).delete()
            session.query(Document).delete()
            session.query(Verification).delete()
            if not preserve_pr:
                session.query(PurchaseRequestItem).delete()
                session.query(PurchaseRequest).delete()
            session.commit()

            # Remove uploaded PDFs as well, keeping the directory structure.
            uploads_deleted = 0
            upload_failures: List[str] = []
            if UPLOADS_DIR.exists():
                for path in UPLOADS_DIR.rglob("*"):
                    if not path.is_file() or path.name == ".gitkeep":
                        continue
                    try:
                        path.unlink()
                        uploads_deleted += 1
                    except OSError as exc:
                        upload_failures.append(f"{path.name}: {exc}")

            message = "All supplier verification data reset to clean zero state."
            if upload_failures:
                message += f" {len(upload_failures)} uploaded file(s) could not be removed."
            return {
                "success": True,
                "message": message,
                "uploads_deleted": uploads_deleted,
                "upload_failures": upload_failures,
            }
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def get_purchase_request(pr_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves reference Purchase Request and items from SQLite.
        """
        session = SessionLocal()
        try:
            if pr_id:
                pr = session.query(PurchaseRequest).filter_by(id=pr_id).first()
            else:
                pr = session.query(PurchaseRequest).first()

            if not pr:
                # Fallback to direct service parse if DB not yet seeded
                meta = PurchaseRequestService.get_pr_metadata()
                items = PurchaseRequestService.get_all_items_list()
                return {
                    "pr_number": meta.get("pr_number", "PR-2026-114"),
                    "company": meta.get("company", "Aamar Garments Ltd"),
                    "department": meta.get("department", "Procurement Directorate"),
                    "date": meta.get("date", "2026-10-15"),
                    "currency": meta.get("currency", "BDT"),
                    "items": items
                }

            items = [
                {
                    "pr_number": pr.id,
                    "item_code": it.item_code,
                    "item_description": it.item_description,
                    "specification": it.specification,
                    "quantity": it.quantity,
                    "unit": it.unit,
                    "max_unit_price": it.max_unit_price,
                    "target_delivery_days": it.target_delivery_days,
                    "required_vat_rate": it.required_vat_rate,
                    "max_advance_pct": it.max_advance_pct
                }
                for it in sorted(pr.items, key=lambda x: x.line_number)
            ]

            return {
                "pr_number": pr.id,
                "company": pr.company_name,
                "department": pr.department,
                "date": pr.created_date,
                "currency": pr.currency,
                "items": items
            }
        finally:
            session.close()
