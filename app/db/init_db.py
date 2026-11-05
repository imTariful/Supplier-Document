"""
Database initialization and reference data loader.
Initializes SQLite tables and loads genuine Purchase Request from data/reference/purchase-request.csv.
Never seeds mock supplier records or fake verifications.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from app.db.session import engine, SessionLocal
from app.db.models import Base, PurchaseRequest, PurchaseRequestItem, Verification
from app.services.pr_service import PurchaseRequestService

def init_db(seed_pr: bool = True):
    """
    Creates database schema in SQLite.
    Optionally seeds reference Purchase Request specifications.
    Leaves verifications and validation results strictly empty.
    """
    Base.metadata.create_all(bind=engine)

    # Perform lightweight migration for newly added columns if table already existed
    with engine.connect() as conn:
        from sqlalchemy import text
        try:
            res = conn.execute(text("PRAGMA table_info(verifications)")).fetchall()
            cols = [r[1] for r in res]
            if cols:
                if "quotation_details" not in cols:
                    conn.execute(text("ALTER TABLE verifications ADD COLUMN quotation_details TEXT DEFAULT '{}' NOT NULL"))
                    conn.commit()
                if "contract_terms" not in cols:
                    conn.execute(text("ALTER TABLE verifications ADD COLUMN contract_terms TEXT DEFAULT '{}' NOT NULL"))
                    conn.commit()
        except Exception as mig_err:
            print(f"[DB Migration Info] {mig_err}", file=sys.stderr)

    if seed_pr:
        session = SessionLocal()
        try:
            # One-time repair for historical rows written before the workflow
            # exposed triggered IDs.  Existing decisions are never changed.
            for verification in session.query(Verification).all():
                if (verification.triggered_rule_ids or "[]").strip() not in ("", "[]"):
                    continue
                triggered_ids = sorted({
                    result.rule_id
                    for result in verification.validation_results
                    if result.result in ("FAIL", "REVIEW")
                })
                if triggered_ids:
                    verification.triggered_rule_ids = json.dumps(triggered_ids)
            session.commit()

            # Check PR metadata from CSV
            meta = PurchaseRequestService.get_pr_metadata()
            pr_id = meta.get("pr_number", "PR-2026-114")

            # Check if reference PR already exists
            existing_pr = session.query(PurchaseRequest).filter_by(id=pr_id).first()
            if not existing_pr:
                # Also delete older PR if different ID exists to keep it cleanly synced
                session.query(PurchaseRequestItem).delete()
                session.query(PurchaseRequest).delete()
                session.commit()

                pr = PurchaseRequest(
                    id=pr_id,
                    company_name=meta.get("company", "Aamar Garments Ltd"),
                    department=meta.get("department", "Procurement Directorate"),
                    created_date=meta.get("date", "2026-10-15"),
                    currency=meta.get("currency", "BDT"),
                    created_at=datetime.utcnow()
                )
                session.add(pr)
                session.flush()

                items_list = PurchaseRequestService.get_all_items_list()
                for idx, row in enumerate(items_list, start=1):
                    item = PurchaseRequestItem(
                        pr_id=pr.id,
                        line_number=idx,
                        item_code=row.get("item_code", f"ITEM-{idx}"),
                        item_description=row.get("item_description", "").strip(),
                        specification=row.get("specification", "").strip(),
                        quantity=float(row.get("quantity", 0)),
                        unit=row.get("unit", "").strip(),
                        max_unit_price=float(row.get("max_unit_price", 0)),
                        target_delivery_days=int(row.get("target_delivery_days", 30)),
                        required_vat_rate=float(row.get("required_vat_rate", 15.0)),
                        max_advance_pct=float(row.get("max_advance_pct", 20.0))
                    )
                    session.add(item)
                session.commit()
                print(f"[DB] Initialized database and seeded reference {pr_id}.", file=sys.stderr)
            else:
                print(f"[DB] Database schema verified. Reference {pr_id} exists.", file=sys.stderr)
        except Exception as e:
            session.rollback()
            print(f"[DB Error] Failed to seed reference PR: {e}", file=sys.stderr)
            raise
        finally:
            session.close()

if __name__ == "__main__":
    init_db()
