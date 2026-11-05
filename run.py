#!/usr/bin/env python3
"""
Aamar Garments Ltd — Master CLI & Application Runner.
Commands:
  python3 run.py verify    # Runs LangGraph verification across all 10 supplier packs
  python3 run.py evaluate  # Runs 10-document ground truth evaluation and generates reports
  python3 run.py test      # Executes pytest automated test suite
"""

import sys
import subprocess

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == "verify":
        from app.services.generate_all_reports import generate_all
        print("Executing verification workflow on all supplier packs...")
        generate_all()
        print("Completed successfully!")
    elif cmd == "evaluate":
        from evaluation.evaluate import run_evaluation
        run_evaluation()
    elif cmd == "test":
        subprocess.run(["python3", "-m", "pytest", "tests/", "-v"], check=True)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)

if __name__ == "__main__":
    main()
