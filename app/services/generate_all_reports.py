"""
Batch generates individual PDF verification audit reports for all 10 supplier packs.
"""

import sys
sys.path.insert(0, ".")
import os
from app.workflow.graph import build_verification_workflow
from app.services.pr_service import PurchaseRequestService
from app.services.report_generator import SupplierReportGenerator
from app.rules.rule_engine import DecisionEngine

OUTPUT_REPORTS_DIR = "outputs/reports/individual"
os.makedirs(OUTPUT_REPORTS_DIR, exist_ok=True)

def generate_all():
    pr_items = PurchaseRequestService.load_purchase_request()
    workflow = build_verification_workflow()
    
    for i in range(1, 11):
        sid = f"PACK-{i:02d}"
        q_path = f"data/input/{sid.lower()}_quotation.pdf"
        c_path = f"data/input/{sid.lower()}_contract.pdf"
        
        out = workflow.invoke({
            "supplier_id": sid,
            "quotation_path": q_path,
            "contract_path": c_path,
            "purchase_request_items": pr_items
        })
        
        # Build VerificationResult
        res = DecisionEngine.evaluate_supplier_pack(
            supplier_id=sid,
            supplier_name=out.get("supplier_name", sid),
            quotation=out["structured_quotation"],
            contract=out["structured_contract"],
            pr_items=pr_items
        )
        
        pdf_out = f"{OUTPUT_REPORTS_DIR}/{sid.lower()}_verification_report.pdf"
        SupplierReportGenerator.generate_single_report(res, pdf_out)

if __name__ == "__main__":
    generate_all()
