# Aamar Garments Ltd — Supplier Document Verification System

A production-grade, deterministic document intelligence platform designed to automate supplier quotation and contract verification against company procurement policies, ensuring 100% decision accuracy with comprehensive audit trails.

> **Engineering Principle:**
> *Structured extraction. Deterministic verification. Orchestrated workflow. Human oversight for uncertainty.*

---

## 1. Problem Statement & Business Context

Aamar Garments Ltd receives commercial quotations and supply agreements from textile, trims, packaging, and accessory suppliers across Bangladesh. Employees previously needed to manually cross-check item specifications, delivery timelines, payment terms, statutory tax registrations (TIN/BIN), 15% VAT breakdown, and liquidated damage penalty clauses against purchase request **PR-2026-114** (legacy documents may use the accepted alias `PR-2026-AGL-0089`).

This system automates the multi-document extraction, verification, policy rule validation, and ground-truth evaluation, achieving **100% decision accuracy** with **0% false approvals**.

---

## 2. Key Architecture & Design Highlights

- **Deterministic 12-Node LangGraph Workflow:** Sequential orchestration with explicit typed state (`VerificationWorkflowState`) and conditional escalation edges.
- **Independent Python Business Rule Engine:** Strict Decimal precision calculations for all unit prices, quantity deviations, advances, delivery schedules, and tax arithmetic.
- **Deterministic Extraction Only:** Document parsing uses pattern-based extraction with full traceability. The final procurement determination (`REJECT > NEEDS_HUMAN_REVIEW > APPROVE`) is strictly enforced by Python logic.
- **Traceable Evidence Audit Trail:** Every failed rule preserves the source document filename, 1-indexed page number, and verbatim quotation snippet.
- **Full-Stack Procurement Suite:** Interactive enterprise dashboard on port 3000 featuring Executive KPIs, Document Management, Purchase Request Item Comparison, Compliance Rule Matrix, Human Review Workspace, and Report Generator.

---

## 3. Technology Stack

- **Workflow Orchestration:** `LangGraph 1.2.19` (Sequential StateGraph)
- **Document Intelligence:** `PyMuPDF` for digital text extraction with comprehensive pattern matching
- **Structured Schema Validation:** `Pydantic 2.14.2` with Python `Decimal`
- **Audit Reports & Visualizations:** `ReportLab 5.1.0`, `Matplotlib 3.11.2`, `Pandas 3.1.0`
- **Backend API & Dev Server:** Node.js v22, `Express 4.21.2`, `TypeScript 7.0`
- **Frontend Dashboard:** `React 19`, `Vite 8.3`, `Tailwind CSS v4`, `Lucide Icons`
- **Automated Testing:** `pytest 8.4.2` (49 unit, workflow, extraction, DB, and validation tests)

---

## 4. 10-Document Challenge Evaluation Results

| Supplier Pack | Supplier Name | Expected Decision | Actual Decision | Triggered Rules | Status |
|---|---|---|---|---|---|
| **PACK-01** | Vertex Textiles & Trims Ltd | **APPROVE** | **APPROVE** | *None (All passed)* | **CORRECT** |
| **PACK-02** | Apex Apparel Accessories Ltd | **REJECT** | **REJECT** | `R01` (Excessive price +6.25%) | **CORRECT** |
| **PACK-03** | Bengal Stitch & Pack Solutions | **REJECT** | **REJECT** | `R02` (25% advance payment &gt; 20%) | **CORRECT** |
| **PACK-04** | Meghna Fasteners & Accessories Ltd | **REJECT** | **REJECT** | `R07` (Penalty 0.25%/wk &lt; 0.5%) | **CORRECT** |
| **PACK-05** | Padma Packaging & Labeling Corp | **REJECT** | **REJECT** | `R04`, `R05` (Missing TIN/BIN) | **CORRECT** |
| **PACK-06** | Jamuna Yarn & Thread Mills | **REJECT** | **REJECT** | `R06` (Delivery 52d &gt; 45d) | **CORRECT** |
| **PACK-07** | Rupsha Trims & Poly Industries | **NEEDS_HUMAN_REVIEW** | **NEEDS_HUMAN_REVIEW** | `H01`, `H04` (Minor price dev +1.67%, 38d del) | **CORRECT** |
| **PACK-08** | Karnafuli Zipper & Button Co | **NEEDS_HUMAN_REVIEW** | **NEEDS_HUMAN_REVIEW** | `H02` (Quantity dev -16.67% &gt; 5%) | **CORRECT** |
| **PACK-09** | Shitalakshya Dyeing & Trims Ltd | **NEEDS_HUMAN_REVIEW** | **NEEDS_HUMAN_REVIEW** | `H03`, `H07` (Payment 75d &gt; 60d, validity 20d) | **CORRECT** |
| **PACK-10** | Surma Carton & Packaging Works | **NEEDS_HUMAN_REVIEW** | **NEEDS_HUMAN_REVIEW** | `H05`, `H06` (VAT not separate, arithmetic error) | **CORRECT** |

- **Total Supplier Packs Evaluated:** 10
- **Correct Predictions:** 10 / 10
- **Overall Decision Accuracy:** **100.0%**
- **False Approval Rate:** **0.0%**

---

## 5. Execution Instructions

### A. Run Automated Pytest Suite
```bash
python3 run.py test
# or
python3 -m pytest tests/ -v
```
*Executes all 49 tests, including price, advance, quantity, delivery, payment, penalty, arithmetic boundaries, layout-tolerant extraction, H08/H09/H10 evidence rules, immutable human-review decisions, reset cleanup, and OCR/Gemini guard rails.*

### B. Run 10-Document Challenge Evaluation
```bash
python3 run.py evaluate
```
*Generates `outputs/reports/evaluation_report.pdf`, `outputs/reports/evaluation_results.csv`, `outputs/reports/confusion_matrix.png`, and `outputs/reports/evaluation_summary.json`.*

### C. Launch Web Application & Dashboard
```bash
npm run dev
# Serves interactive procurement dashboard on http://localhost:3000
```

The application never fabricates a machine decision: human review records the auditor outcome separately and `effective_decision` is computed from the immutable `machine_decision`.

### E. Real HTTP API Surface
- `GET /api/dashboard/summary`
- `GET /api/verifications` and `GET /api/verifications/:id`
- `GET /api/verifications/:id/results`
- `GET /api/verifications/:id/documents`
- `GET /api/verifications/:id/document` (streams the stored source PDF)
- `POST /api/documents/upload` (alias `POST /api/verifications`)
- `GET /api/reviews` and `POST /api/reviews/:id/decision` (alias `POST /api/human-review`)
- `GET /api/purchase-request`
- `POST /api/admin/reset` (clears DB rows and files under `data/uploads/`)
- `GET /api/download/individual-pdf?supplier_id=...`
- `GET /api/raw-document/:filename` (legacy filename-based preview)

---

## 6. Generated Deliverables & Documentation Index

- `docs/document_inventory.md`: Cryptographic inventory of all 20 ingested documents.
- `docs/architecture.md`: LangGraph 12-node workflow diagrams and data contracts.
- `docs/business_rules.md`: Complete business rules source of truth (`R01`–`R07`, `H01`–`H10`).
- `docs/technical_design.md`: Schemas, extraction fallback, and REST API definitions.
- `docs/evidence_and_audit.md`: Verifiable source citation and audit trail rules.
- `docs/testing_report.md`: Pytest 49-test execution records.
- `docs/evaluation_methodology.md`: Ground truth confusion matrix and classification metrics.
- `docs/limitations.md`: Documented constraints and prospective enhancements.
- `outputs/reports/evaluation_report.pdf`: Consolidated executive audit PDF report.
- `outputs/reports/individual/*.pdf`: Individual PDF audit certificates for all 10 packs.
