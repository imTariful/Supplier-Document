"""
Command Line Interface for Database Management & Service Queries.
Produces clean JSON stdout for Node.js / Express backend consumption and admin scripts.
"""
import sys
import os
import json
from decimal import Decimal

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.init_db import init_db
from app.db.service import VerificationDBService

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing command. Available: init, summary, list, get, reviews, review, verify, reset, pr"}))
        sys.exit(1)

    cmd = sys.argv[1].lower()

    try:
        if cmd == "init":
            init_db(seed_pr=True)
            print(json.dumps({"success": True, "message": "Database initialized successfully"}))

        elif cmd == "summary":
            init_db(seed_pr=True)
            summary = VerificationDBService.get_dashboard_summary()
            print(json.dumps(summary, default=decimal_default))

        elif cmd == "list":
            init_db(seed_pr=True)
            search = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "null" else None
            decision = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "null" else None
            limit = int(sys.argv[4]) if len(sys.argv) > 4 else 50
            offset = int(sys.argv[5]) if len(sys.argv) > 5 else 0
            res = VerificationDBService.get_verifications(search=search, decision=decision, limit=limit, offset=offset)
            print(json.dumps(res, default=decimal_default))

        elif cmd == "get":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: get <verification_id>"}))
                sys.exit(1)
            init_db(seed_pr=True)
            v = VerificationDBService.get_verification_by_id(sys.argv[2])
            if not v:
                print(json.dumps({"error": "Verification not found"}))
                sys.exit(1)
            print(json.dumps(v, default=decimal_default))

        elif cmd == "reviews":
            init_db(seed_pr=True)
            revs = VerificationDBService.get_pending_reviews()
            print(json.dumps({"reviews": revs, "total": len(revs)}, default=decimal_default))

        elif cmd == "review":
            if len(sys.argv) < 6:
                print(json.dumps({"error": "Usage: review <id> <name> <role> <decision> [comments] [dispensation]"}))
                sys.exit(1)
            v_id = sys.argv[2]
            name = sys.argv[3]
            role = sys.argv[4]
            decision = sys.argv[5]
            comments = sys.argv[6] if len(sys.argv) > 6 else ""
            dispensation = sys.argv[7] if len(sys.argv) > 7 else ""
            out = VerificationDBService.submit_human_review(
                verification_id=v_id,
                reviewer_name=name,
                reviewer_role=role,
                review_decision=decision,
                comments=comments,
                dispensation_reason=dispensation
            )
            print(json.dumps(out, default=decimal_default))

        elif cmd == "verify":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Usage: verify <document_path> [supplier_id] [supplier_name] [original_filename]"}))
                sys.exit(1)
            init_db(seed_pr=True)
            first_path = sys.argv[2]
            
            # Check if third argument is another PDF (legacy 2-file mode)
            is_legacy = len(sys.argv) > 3 and sys.argv[3].lower().endswith(".pdf")
            if is_legacy:
                c_path = sys.argv[3]
                s_id = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "null" else None
                s_name = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != "null" else None
                orig_name = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] != "null" else None
                result = VerificationDBService.run_and_persist_verification(
                    document_src_path=first_path,
                    supplier_id=s_id,
                    supplier_name=s_name,
                    original_filename=orig_name,
                    contract_src_path=c_path
                )
            else:
                s_id = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "null" else None
                s_name = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "null" else None
                orig_name = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != "null" else None
                result = VerificationDBService.run_and_persist_verification(
                    document_src_path=first_path,
                    supplier_id=s_id,
                    supplier_name=s_name,
                    original_filename=orig_name
                )

            print(json.dumps({"success": True, "result": result}, default=decimal_default))

        elif cmd == "reset":
            out = VerificationDBService.reset_all_data(preserve_pr=True)
            print(json.dumps(out))

        elif cmd == "pr":
            init_db(seed_pr=True)
            pr = VerificationDBService.get_purchase_request()
            print(json.dumps(pr, default=decimal_default))

        else:
            print(json.dumps({"error": f"Unknown command: {cmd}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
