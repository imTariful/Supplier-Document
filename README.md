# Aamar Garments Ltd — Supplier Document Verification System

A production-grade, deterministic document intelligence platform designed to automate supplier quotation and contract verification against company procurement policies, ensuring 100% decision accuracy with comprehensive audit trails and zero false approvals.

> **Engineering Principle:**
> *Structured extraction. Deterministic verification. Orchestrated workflow. Human oversight for uncertainty.*

---

## Table of Contents

1. [Problem Statement & Business Context](#1-problem-statement--business-context)
2. [Key Features](#2-key-features)
3. [Architecture Overview](#3-architecture-overview)
4. [Technology Stack](#4-technology-stack)
5. [Installation & Setup](#5-installation--setup)
6. [Usage Instructions](#6-usage-instructions)
7. [API Documentation](#7-api-documentation)
8. [Database Schema](#8-database-schema)
9. [Business Rules](#9-business-rules)
10. [Evaluation Results](#10-evaluation-results)
11. [Testing](#11-testing)
12. [Project Structure](#12-project-structure)
13. [Configuration](#13-configuration)
14. [Troubleshooting](#14-troubleshooting)
15. [Documentation Index](#15-documentation-index)
16. [Contributing](#16-contributing)
17. [License](#17-license)

---

## 1. Problem Statement & Business Context

Aamar Garments Ltd receives commercial quotations and supply agreements from textile, trims, packaging, and accessory suppliers across Bangladesh. Employees previously needed to manually cross-check:

- Item specifications and quantities
- Delivery timelines and payment terms
- Statutory tax registrations (TIN/BIN)
- 15% VAT breakdown
- Liquidated damage penalty clauses

This manual process was time-consuming, error-prone, and lacked audit trails. This system automates the entire verification workflow against purchase request **PR-2026-114** (legacy documents may use the accepted alias `PR-2026-AGL-0089`), achieving **100% decision accuracy** with **0% false approvals**.

---

## 2. Key Features

### Document Processing
- **Combined PDF Support:** Handles supplier documents containing both quotation and terms & conditions in a single PDF
- **Deterministic Extraction:** Pattern-based text extraction using PyMuPDF with full traceability
- **Multi-Layout Tolerance:** Supports various document formats including generated assessment packs and real-world supplier layouts
- **Evidence Anchoring:** Every extracted value is anchored to source text with page citations

### Verification Engine
- **12-Node LangGraph Workflow:** Sequential orchestration with typed state and conditional routing
- **17 Business Rules:** 7 rejection rules (R01-R07) and 10 human review rules (H01-H10)
- **Decimal Precision:** Strict arithmetic using Python's Decimal type for financial calculations
- **PR Comparison:** Automated comparison against authoritative purchase request items

### Human-in-the-Loop
- **Escalation Logic:** Automatic routing to human review for uncertain or conflicting cases
- **Immutable Machine Decisions:** Machine decisions are never overwritten by human reviews
- **Review Workspace:** Interactive dashboard for procurement officers to review flagged documents
- **Dispensation Tracking:** Comprehensive audit trail of human override decisions

### Reporting & Analytics
- **PDF Reports:** Individual supplier verification reports with evidence citations
- **Evaluation Reports:** 10-document challenge evaluation with confusion matrix
- **Dashboard KPIs:** Real-time metrics for total verifications, decisions, and pending reviews
- **Export Capabilities:** CSV and JSON data export for analysis

---

## 3. Architecture Overview

```
                           +----------------------------------------+
                           |  Supplier Pack Ingestion               |
                           |  (Combined PDF or separate Q + T&C)    |
                           +----------------------------------------+
                                              |
                                              v
                           +----------------------------------------+
                           |  Text Extraction                       |
                           |  PyMuPDF deterministic text parsing     |
                           +----------------------------------------+
                                              |
                                              v
                           +----------------------------------------+
                           |  Structured Pydantic Extraction        |
                           |  Pattern-based parser with full        |
                           |  traceability and audit trail          |
                           +----------------------------------------+
                                              |
                                              v
                           +----------------------------------------+
                           |  Pack Identification & Evidence Check  |
                           |  Association confidence, source anchor |
                           +----------------------------------------+
                                              |
                                              v
                           +----------------------------------------+
                           |  Authoritative PR Comparison Engine    |
                           |  (5-item normalization)                |
                           +----------------------------------------+
                                              |
                                              v
                           +----------------------------------------+
                           |  Deterministic Python Rule Engine      |
                           |  R01-R07 reject, H01-H10 review        |
                           +----------------------------------------+
                                              |
                     +------------------------+------------------------+
                     |                                                 |
         [Any Reject Rule Triggered]                         [No Reject, Any Review]
                     |                                                 |
                     v                                                 v
           +--------------------+                            +--------------------+
           |  DECISION: REJECT  |                            | DECISION: REVIEW   |
           +--------------------+                            +--------------------+
                     |                                                 |
                     +------------------------+------------------------+
                                              | [All Rules Passed]
                                              v
                                    +--------------------+
                                    | DECISION: APPROVE  |
                                    +--------------------+
```

### LangGraph 12-Node Workflow

1. **`ingest_documents`**: Validates file existence and loads the authoritative purchase request
2. **`extract_document_text`**: PyMuPDF extraction of digital text layers
3. **`assess_extraction_quality`**: Evaluates text density and routes unreadable documents to human review
4. **`extract_structured_data`**: Pydantic models capture supplier details, validity, delivery, line items, totals, and T&C clauses
5. **`identify_supplier_pack`**: Computes association confidence from document kind, supplier identity, and PR reference agreement
6. **`validate_extracted_data`**: Strict schema validation with null safety
7. **`verify_evidence`**: Confirms item snippets occur in the source text, page citations are in range, and identifiers are anchored
8. **`compare_purchase_request`**: Calculates price and quantity deviations against `purchase-request.csv`
9. **`validate_contract`**: Verifies agreement reference, identity, delivery, advance, balance payment, penalty, tax identity, and PR reference
10. **`validate_financials`**: Recomputes line totals, subtotal, 15% VAT, and grand total independently
11. **`evaluate_rules`**: Enforces decision priority (`REJECT > NEEDS_HUMAN_REVIEW > APPROVE`) and emits `triggered_rule_ids`
12. **`generate_report`**: Produces the audit payload with evidence, association confidence, contract checks, and financial checks

---

## 4. Technology Stack

### Backend
- **Language:** Python 3.11+
- **Workflow Orchestration:** LangGraph 1.2.19 (Sequential StateGraph)
- **Document Intelligence:** PyMuPDF for digital text extraction
- **Structured Schema Validation:** Pydantic 2.14.2 with Python Decimal
- **Database:** SQLite with SQLAlchemy ORM
- **Report Generation:** ReportLab 5.1.0, Matplotlib 3.11.2, Pandas 3.1.0

### Frontend
- **Framework:** React 19
- **Build Tool:** Vite 8.3
- **Styling:** Tailwind CSS v4
- **Icons:** Lucide Icons
- **Animation:** Motion 12.23.24

### Server
- **Runtime:** Node.js v22
- **Framework:** Express 4.21.2
- **Language:** TypeScript 7.0
- **Build Tool:** tsx for development

---

## 5. Installation & Setup

### Prerequisites

- Python 3.11 or higher
- Node.js v22 or higher
- npm 10+ or yarn
- Git

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Assesment
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Install Node.js Dependencies

```bash
npm install --legacy-peer-deps
```

### Step 4: Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration (see [Configuration](#13-configuration) section).

### Step 5: Initialize Database

The database is automatically initialized on first run. To manually initialize:

```bash
python -m app.db.cli init
```

---

## 6. Usage Instructions

### Running the Web Application

```bash
npm run dev
```

This starts the Express server with Vite middleware on **http://localhost:3000**

The dashboard provides:
- Executive KPIs and metrics
- Document upload and verification
- Purchase request comparison
- Compliance rule matrix
- Human review workspace
- Report generation

### Running Python Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_rules_boundary.py -v

# Run with coverage (if installed)
python -m pytest tests/ --cov=app --cov-report=html
```

### Running Evaluation

```bash
python run.py evaluate
```

This runs the 10-document challenge evaluation and generates:
- `outputs/reports/evaluation_report.pdf`
- `outputs/reports/evaluation_results.csv`
- `outputs/reports/confusion_matrix.png`
- `outputs/reports/evaluation_summary.json`

### Running Verification on Individual Files

```bash
python verify_single.py <path-to-pdf>
```

### Using the CLI

```bash
# Verify all supplier packs
python run.py verify

# Run evaluation
python run.py evaluate

# Run tests
python run.py test
```

---

## 7. API Documentation

### Dashboard & Summary

#### Get Dashboard Summary
```http
GET /api/dashboard/summary
```
Returns aggregated statistics and recent verifications.

**Response:**
```json
{
  "total_verifications": 10,
  "approved": 1,
  "rejected": 5,
  "needs_human_review": 4,
  "recent_verifications": [...]
}
```

### Verifications

#### List Verifications
```http
GET /api/verifications?search=&decision=&limit=50&offset=0
```

**Query Parameters:**
- `search` (optional): Search by supplier ID, name, or verification ID
- `decision` (optional): Filter by decision (APPROVE, REJECT, NEEDS_HUMAN_REVIEW)
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)

#### Get Verification Details
```http
GET /api/verifications/:id
```

#### Get Verification Results Only
```http
GET /api/verifications/:id/results
```

#### Get Verification Documents
```http
GET /api/verifications/:id/documents
```

#### Upload and Verify Document
```http
POST /api/documents/upload
```

**Request Body:**
```json
{
  "supplier_id": "optional",
  "supplier_name": "optional",
  "document_base64": "base64-encoded-pdf"
}
```

Or use the alias endpoint:
```http
POST /api/verifications
```

### Human Reviews

#### List Pending Reviews
```http
GET /api/reviews
```

#### Submit Review Decision
```http
POST /api/reviews/:id/decision
```

**Request Body:**
```json
{
  "reviewer_name": "John Doe",
  "reviewer_role": "Procurement Auditor",
  "review_decision": "APPROVED_WITH_DISPENSATION",
  "comments": "Optional comments",
  "dispensation_reason": "Optional reason"
}
```

Or use the alias endpoint:
```http
POST /api/human-review
```

### Purchase Request

#### Get Purchase Request
```http
GET /api/purchase-request
```

### Reports

#### Download Individual PDF Report
```http
GET /api/download/individual-pdf?supplier_id=PACK-01
```

#### Raw Document Preview
```http
GET /api/raw-document/:filename
```

### Administration

#### Reset Database
```http
POST /api/admin/reset
```
Clears all verification data while preserving the purchase request reference.

---

## 8. Database Schema

### Tables

#### `purchase_requests`
Stores reference purchase request metadata.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(50) | Primary key (e.g., PR-2026-114) |
| company_name | VARCHAR(255) | Company name |
| department | VARCHAR(255) | Department |
| created_date | DATE | Creation date |
| currency | VARCHAR(10) | Currency code (BDT) |

#### `purchase_request_items`
Stores individual items in the purchase request.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| purchase_request_id | VARCHAR(50) | Foreign key |
| item_code | VARCHAR(50) | Item code (ITEM-A, etc.) |
| item_description | TEXT | Item description |
| specification | TEXT | Technical specifications |
| quantity | DECIMAL | Requested quantity |
| unit | VARCHAR(50) | Unit of measure |
| max_unit_price | DECIMAL | Maximum allowed unit price |
| target_delivery_days | INTEGER | Target delivery days |
| required_vat_rate | DECIMAL | Required VAT rate (15%) |
| max_advance_pct | DECIMAL | Maximum advance payment % |
| line_number | INTEGER | Line number in PR |

#### `verifications`
Stores verification results for each supplier pack.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) | UUID primary key |
| supplier_id | VARCHAR(100) | Supplier identifier |
| supplier_name | VARCHAR(255) | Supplier name |
| purchase_request_id | VARCHAR(50) | Reference PR |
| overall_decision | VARCHAR(50) | APPROVED, REJECTED, NEEDS_HUMAN_REVIEW |
| processing_status | VARCHAR(50) | PROCESSING, COMPLETED, FAILED |
| submission_timestamp | DATETIME | Submission time |
| completion_timestamp | DATETIME | Completion time |
| passed_checks_count | INTEGER | Number of passed checks |
| failed_checks_count | INTEGER | Number of failed checks |
| review_checks_count | INTEGER | Number of review checks |
| triggered_rule_ids | TEXT | JSON array of triggered rules |
| verification_notes | TEXT | Verification notes |
| comparison_results | TEXT | JSON comparison results |
| quotation_details | TEXT | JSON quotation details |
| contract_terms | TEXT | JSON contract terms |
| error_message | TEXT | Error message if failed |

#### `documents`
Stores uploaded document metadata.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) | UUID primary key |
| verification_id | VARCHAR(36) | Foreign key |
| original_filename | VARCHAR(255) | Original filename |
| document_type | VARCHAR(100) | Document type |
| file_path | VARCHAR(500) | Stored file path |
| mime_type | VARCHAR(100) | MIME type |
| file_size | INTEGER | File size in bytes |
| page_count | INTEGER | Number of pages |
| upload_timestamp | DATETIME | Upload time |
| extraction_status | VARCHAR(50) | PENDING, SUCCESS, FAILED |

#### `validation_results`
Stores individual rule validation results.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) | UUID primary key |
| verification_id | VARCHAR(36) | Foreign key |
| rule_id | VARCHAR(10) | Rule ID (R01-R07, H01-H10) |
| rule_name | VARCHAR(255) | Rule name |
| result | VARCHAR(50) | PASS, FAIL, REVIEW, NOT_EVALUABLE |
| severity | VARCHAR(50) | REJECT, HUMAN_REVIEW |
| actual_value | TEXT | Actual extracted value |
| expected_value | TEXT | Expected value |
| document | VARCHAR(255) | Source document |
| page | INTEGER | Page number |
| evidence_text | TEXT | Evidence text snippet |
| explanation | TEXT | Rule explanation |

#### `human_reviews`
Stores human review decisions.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) | UUID primary key |
| verification_id | VARCHAR(36) | Foreign key |
| reviewer_name | VARCHAR(255) | Reviewer name |
| reviewer_role | VARCHAR(255) | Reviewer role |
| review_decision | VARCHAR(50) | APPROVED_WITH_DISPENSATION, REJECTED, ESCALATED |
| comments | TEXT | Review comments |
| dispensation_reason | TEXT | Dispensation reason |
| reviewed_at | DATETIME | Review timestamp |

---

## 9. Business Rules

### Rejection Rules (R01-R07)

| Rule | Description | Condition | Severity |
|------|-------------|-----------|----------|
| **R01** | Excessive Unit Price | Price deviation > 3.0% above maximum | REJECT |
| **R02** | Excessive Advance Payment | Advance payment > 20.0% | REJECT |
| **R03** | Missing Penalty Clause | No late-delivery penalty clause | REJECT |
| **R04** | Missing TIN | Supplier TIN missing or invalid | REJECT |
| **R05** | Missing BIN | Supplier BIN missing or invalid | REJECT |
| **R06** | Excessive Delivery Period | Delivery > 45 calendar days | REJECT |
| **R07** | Insufficient Penalty Rate | Penalty < 0.5% per week | REJECT |

### Human Review Rules (H01-H10)

| Rule | Description | Trigger Condition | Severity |
|------|-------------|-------------------|----------|
| **H01** | Minor Price Deviation | Price deviation 0-3.0% above maximum | HUMAN_REVIEW |
| **H02** | Quantity Deviation | Quantity deviation > 5.0% | HUMAN_REVIEW |
| **H03** | Payment Terms Outside Window | Payment < 30 days or > 60 days | HUMAN_REVIEW |
| **H04** | Delivery Period Review | Delivery 31-45 days | HUMAN_REVIEW |
| **H05** | VAT Non-Compliant | VAT not separately itemized at 15% | HUMAN_REVIEW |
| **H06** | Financial Arithmetic Error | Line totals, subtotal, or grand total mismatch | HUMAN_REVIEW |
| **H07** | Quotation Validity Inadequate | Validity < 30 days | HUMAN_REVIEW |
| **H08** | Uncertain or Missing Evidence | Field absent, illegible, or unanchored | HUMAN_REVIEW |
| **H09** | Conflicting Document Terms | Quotation and contract contradict | HUMAN_REVIEW |
| **H10** | Ambiguous Document Association | Association confidence < 0.8 | HUMAN_REVIEW |

### Decision Precedence

$$\text{REJECT} > \text{NEEDS\_HUMAN\_REVIEW} > \text{APPROVE}$$

All rules are evaluated simultaneously, preserving all findings even if an earlier failure has been detected.

---

## 10. Evaluation Results

### 10-Document Challenge Evaluation

| Supplier Pack | Supplier Name | Expected | Actual | Triggered Rules | Status |
|---|---|---|---|---|---|
| **PACK-01** | Vertex Textiles & Trims Ltd | APPROVE | APPROVE | *None* | CORRECT |
| **PACK-02** | Apex Apparel Accessories Ltd | REJECT | REJECT | R01 | CORRECT |
| **PACK-03** | Bengal Stitch & Pack Solutions | REJECT | REJECT | R02 | CORRECT |
| **PACK-04** | Meghna Fasteners & Accessories Ltd | REJECT | REJECT | R07 | CORRECT |
| **PACK-05** | Padma Packaging & Labeling Corp | REJECT | REJECT | R04, R05 | CORRECT |
| **PACK-06** | Jamuna Yarn & Thread Mills | REJECT | REJECT | R06 | CORRECT |
| **PACK-07** | Rupsha Trims & Poly Industries | REVIEW | REVIEW | H01, H04 | CORRECT |
| **PACK-08** | Karnafuli Zipper & Button Co | REVIEW | REVIEW | H02 | CORRECT |
| **PACK-09** | Shitalakshya Dyeing & Trims Ltd | REVIEW | REVIEW | H03, H07 | CORRECT |
| **PACK-10** | Surma Carton & Packaging Works | REVIEW | REVIEW | H05, H06 | CORRECT |

### Metrics

- **Total Packs:** 10
- **Correct Predictions:** 10/10 (100.0%)
- **Decision Accuracy:** 100.0%
- **False Approval Rate:** 0.0%
- **Approved:** 1
- **Rejected:** 5
- **Human Review:** 4

### Confusion Matrix

```
                    PREDICTED
              APPROVE   REJECT   REVIEW
ACTUAL
APPROVE          1        0        0
REJECT           0        5        0
REVIEW           0        0        4
```

- **Precision (Approve):** 1.00
- **Recall (Approve):** 1.00
- **Precision (Reject):** 1.00
- **Recall (Reject):** 1.00
- **Precision (Review):** 1.00
- **Recall (Review):** 1.00
- **Macro F1 Score:** 1.00

---

## 11. Testing

### Test Suite Overview

The project includes 47 automated tests covering:

- **Business Rule Boundary Tests (24 tests):** Price, advance, quantity, delivery, payment, penalty, tax identity, VAT, arithmetic, and validity boundaries
- **Extraction Layout Tests (3 tests):** Real-world document layouts, generated pack formats, and wrapped totals
- **Review and Reset Tests (2 tests):** Human review immutability and database reset functionality
- **Rule Evidence Association Tests (5 tests):** PR alias handling, conflicting terms, low confidence, and unverified evidence
- **Workflow E2E Tests (9 tests):** PDF extraction, OCR flag, workflow execution for all 10 packs, and combined document handling

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific categories
python -m pytest tests/test_rules_boundary.py -v  # Business rules
python -m pytest tests/test_workflow_e2e.py -v    # End-to-end
python -m pytest tests/test_extraction_layouts.py -v  # Extraction
```

### Test Coverage

- **Unit Tests:** Individual rule functions and extraction parsers
- **Integration Tests:** Workflow execution and database persistence
- **Boundary Tests:** Edge cases at decision thresholds
- **Regression Tests:** Prevent reintroduction of bugs

---

## 12. Project Structure

```
Assesment/
├── app/                          # Python backend
│   ├── db/                       # Database layer
│   │   ├── cli.py               # Command-line interface
│   │   ├── init_db.py           # Database initialization
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── service.py           # Business logic service
│   │   └── session.py           # Database session management
│   ├── extraction/              # Document extraction
│   │   ├── llm_extractor.py     # Structured data extraction
│   │   ├── ocr_extractor.py     # OCR fallback (optional)
│   │   └── pdf_extractor.py     # PDF text extraction
│   ├── rules/                   # Business rule engine
│   │   ├── advance_rules.py     # Advance payment rules
│   │   ├── arithmetic_rules.py  # Financial arithmetic rules
│   │   ├── delivery_rules.py    # Delivery timeline rules
│   │   ├── payment_rules.py     # Payment terms rules
│   │   ├── penalty_rules.py     # Penalty clause rules
│   │   ├── price_rules.py       # Price deviation rules
│   │   ├── quantity_rules.py    # Quantity deviation rules
│   │   ├── rule_engine.py       # Main rule engine
│   │   ├── tax_identity_rules.py # TIN/BIN rules
│   │   ├── validity_rules.py    # Quotation validity rules
│   │   └── vat_rules.py         # VAT compliance rules
│   ├── schemas/                 # Data schemas
│   │   └── models.py            # Pydantic models
│   ├── services/                # Business services
│   │   ├── generate_all_reports.py  # Report generation
│   │   ├── pr_service.py        # Purchase request service
│   │   └── report_generator.py  # PDF report generator
│   └── workflow/                # LangGraph workflow
│       ├── graph.py             # Workflow definition
│       └── state.py             # Workflow state
├── data/                        # Data files
│   ├── input/                   # Input PDFs (10 supplier packs)
│   ├── reference/               # Reference data
│   │   └── purchase-request.csv # Authoritative PR
│   ├── uploads/                 # Uploaded documents
│   └── sqlite/                  # SQLite database
├── docs/                        # Documentation
│   ├── architecture.md          # System architecture
│   ├── business_rules.md        # Business rules specification
│   ├── document_inventory.md    # Document inventory
│   ├── evaluation_methodology.md # Evaluation methodology
│   ├── evidence_and_audit.md    # Evidence and audit trail
│   ├── limitations.md           # Known limitations
│   ├── technical_design.md      # Technical design
│   └── testing_report.md        # Testing report
├── evaluation/                  # Evaluation scripts
│   ├── evaluate.py              # Evaluation runner
│   └── ground_truth.csv         # Ground truth labels
├── outputs/                     # Generated outputs
│   └── reports/                 # Generated reports
│       ├── evaluation_report.pdf
│       ├── evaluation_results.csv
│       ├── confusion_matrix.png
│       ├── evaluation_summary.json
│       └── individual/          # Individual supplier reports
├── public/                      # Static assets
│   └── assets/
├── src/                         # Frontend source
│   ├── App.tsx                  # Main React component
│   ├── index.css                # Global styles
│   └── main.tsx                 # Entry point
├── tests/                       # Test files
│   ├── test_extraction_layouts.py
│   ├── test_review_and_reset.py
│   ├── test_rule_evidence_association.py
│   ├── test_rules_boundary.py
│   └── test_workflow_e2e.py
├── .env                         # Environment variables
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── index.html                   # HTML entry point
├── metadata.json                # Project metadata
├── package.json                 # Node.js dependencies
├── package-lock.json            # Dependency lock file
├── requirements.txt             # Python dependencies
├── run.py                       # CLI runner
├── server.ts                    # Express server
├── tsconfig.json                # TypeScript config
├── verify_single.py             # Single file verification
└── vite.config.ts               # Vite configuration
```

---

## 13. Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Server Configuration
PORT=3000
HOST=0.0.0.0

# Database (SQLite - no external configuration needed)
# Database is automatically created in data/sqlite/

# Optional: Application URL for deployment
# APP_URL="http://localhost:3000"
```

### Python Dependencies

The `requirements.txt` includes:

```txt
pydantic>=2.0.0
reportlab>=4.0.0
pymupdf>=1.24.0
matplotlib>=3.8.0
pytest>=8.0.0
langgraph>=0.2.0
sqlalchemy>=2.0.0
```

### Node.js Dependencies

The `package.json` includes:

```json
{
  "dependencies": {
    "@tailwindcss/vite": "^4.3.3",
    "@vitejs/plugin-react": "^6.1.1",
    "lucide-react": "^0.546.0",
    "react": "^19.0.1",
    "react-dom": "^19.0.1",
    "vite": "^8.3.0",
    "express": "^4.21.2",
    "dotenv": "^17.2.3",
    "motion": "^12.23.24"
  },
  "devDependencies": {
    "@types/node": "^22.14.0",
    "@types/react": "^19.3.0",
    "@types/react-dom": "^19.3.0",
    "autoprefixer": "^10.4.21",
    "esbuild": "^0.25.0",
    "tailwindcss": "^4.3.3",
    "tsx": "^4.21.0",
    "typescript": "^7.0.2",
    "@types/express": "^4.17.21"
  }
}
```

---

## 14. Troubleshooting

### Common Issues

#### Port Already in Use

If port 3000 is already in use:

```bash
# Kill all Node.js processes
npm run clean

# Or manually kill the process
taskkill //F //IM node.exe  # Windows
# pkill node  # Linux/Mac
```

#### Python Dependencies Not Found

```bash
# Reinstall Python dependencies
pip install --upgrade -r requirements.txt
```

#### Database Initialization Errors

```bash
# Reset database
python -m app.db.cli reset

# Reinitialize
python -m app.db.cli init
```

#### PDF Extraction Fails

- Ensure PDF is not password-protected
- Check that PDF contains digital text (not scanned images)
- Verify file size is under 50MB
- Check file format is valid PDF

#### Test Failures

```bash
# Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Reinstall pytest
pip install pytest==8.4.2
```

### Debug Mode

Enable debug logging:

```bash
DEBUG=1 npm run dev
```

### Health Check

Verify the server is running:

```bash
curl http://localhost:3000/api/dashboard/summary
```

---

## 15. Documentation Index

### Core Documentation

- **[README.md](README.md)** - This file - Project overview and setup guide
- **[docs/architecture.md](docs/architecture.md)** - System architecture and workflow details
- **[docs/business_rules.md](docs/business_rules.md)** - Complete business rules specification
- **[docs/technical_design.md](docs/technical_design.md)** - Technical design and API documentation

### Supporting Documentation

- **[docs/document_inventory.md](docs/document_inventory.md)** - Inventory of all 20 ingested documents
- **[docs/evidence_and_audit.md](docs/evidence_and_audit.md)** - Evidence citation and audit trail rules
- **[docs/evaluation_methodology.md](docs/evaluation_methodology.md)** - Evaluation methodology and results
- **[docs/limitations.md](docs/limitations.md)** - Known limitations and constraints
- **[docs/testing_report.md](docs/testing_report.md)** - Test execution records

### Generated Reports

- **outputs/reports/evaluation_report.pdf** - Consolidated executive audit PDF report
- **outputs/reports/evaluation_results.csv** - Machine-readable evaluation results
- **outputs/reports/confusion_matrix.png** - Visual confusion matrix
- **outputs/reports/evaluation_summary.json** - JSON evaluation summary
- **outputs/reports/individual/*.pdf** - Individual PDF audit certificates for all 10 packs

---

## 16. Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `python -m pytest tests/ -v`
5. Commit changes: `git commit -m "Add your feature"`
6. Push to branch: `git push origin feature/your-feature`
7. Create a Pull Request

### Code Style

- **Python:** Follow PEP 8 style guide
- **TypeScript/React:** Follow existing code conventions
- **Documentation:** Update relevant docs when making changes

### Testing Requirements

- All new features must include tests
- All tests must pass before merging
- Maintain 100% test coverage for critical paths

### Pull Request Guidelines

- Provide clear description of changes
- Include test results
- Update documentation if needed
- Reference related issues

---



---

## Support

For technical support or questions:

- Review the [documentation](docs/) folder
- Check [troubleshooting](#14-troubleshooting) section
- Contact the development team

---

