# Technical Design Specification

## 1. Document Extraction & OCR Strategy

- **Digital PDFs:** Extracted with PyMuPDF (`pymupdf`). The extractor records page text, page blocks, page count, and a SHA-256 document hash.
- **Layout-tolerant parsing:** `StructuredExtractor` supports generated packs (`ITEM-A`, `Subtotal (Excl. VAT):`) and ordinary supplier layouts where labels and values are on separate lines (for example `Quotation no.` followed by `QT-2026-901`). Wrapped totals labels, short item codes (`A`, `C`), and wrapped descriptions are handled.
- **Scanned fallback:** `OCRExtractor` measures the embedded text layer and raster-image presence. OCR is attempted only when the text layer is below 120 characters.
  - Tesseract is used when the `tesseract` binary is installed (`pytesseract`).
  - EasyOCR is used when Tesseract is unavailable but EasyOCR is installed.
  - If neither engine can run, the document is marked low-confidence and the workflow escalates it. The application does not claim OCR success without a real engine result.
  - `OCR_MAX_PAGES` (default 10) and `OCR_DPI` (default 200) bound processing cost.
- **Source preservation:** Raw PDFs are immutable. The database stores a copy under `data/uploads/`; extracted text never replaces the source file.

## 2. LLM Extraction & Pydantic Validation

- **Deterministic extraction first:** Regex/layout parsing is the default and fully offline. Missing fields default to explicit `None`; nothing is fabricated by the parser.
- **Optional Gemini gap-fill:** `google-genai` is called only when `GEMINI_API_KEY` is present, the deterministic parser is missing core fields (e.g. no items/totals or missing contract terms), and the run is not a pytest run. The default model is `gemini-2.5-flash`.
  - Every returned scalar value must appear literally in the source text.
  - Every returned item must include a `source_text` snippet present in the PDF.
  - Values that fail these checks are discarded, so the LLM cannot invent TIN/BIN numbers or prices.
  - `DISABLE_GEMINI_EXTRACTION=1` forces fully offline operation.
- **Schema enforcement:** `ExtractedQuotation`, `ExtractedContract`, and `QuotationLineItem` use strict Pydantic v2 models with `Decimal` monetary fields.

## 3. LangGraph Workflow

The compiled graph executes in this order:

1. `ingest_documents` — validates file paths and loads the purchase request.
2. `extract_document_text` — PyMuPDF, with real OCR fallback for low-text PDFs.
3. `assess_extraction_quality` — routes unreadable documents to human review.
4. `extract_structured_data` — quotation and T&C sections into Pydantic models.
5. `identify_supplier_pack` — computes supplier/pack association confidence from document kind, supplier identity, and PR reference agreement.
6. `validate_extracted_data` — checks that line items exist.
7. `verify_evidence` — confirms every item `source_text` occurs in the document text, page citations are in range, and supplier/quotation identifiers are anchored.
8. `compare_purchase_request` — computes price and quantity deviations. If evidence verification failed, this step and the next two are skipped and the workflow goes directly to rule evaluation so H08 is recorded.
9. `validate_contract` — checks agreement reference, supplier identity, delivery, advance, balance payment, penalty, tax identity, and PR reference.
10. `validate_financials` — independently recomputes line totals, subtotal, 15% VAT, and grand total.
11. `evaluate_rules` — deterministic `DecisionEngine` with `REJECT > NEEDS_HUMAN_REVIEW > APPROVE`.
12. `generate_report` — emits `triggered_rule_ids`, evidence records, association confidence, contract checks, and financial checks.

Relevant workflow state fields:

```python
class VerificationWorkflowState(TypedDict, total=False):
    pack_identification: Dict[str, Any]
    association_confidence: float
    evidence_verified: bool
    evidence_issues: List[str]
    comparison_results: List[Dict[str, Any]]
    contract_compliance_results: List[Dict[str, Any]]
    contract_validation_passed: bool
    financial_validation_results: List[Dict[str, Any]]
    financial_validation_passed: bool
    rule_results: List[RuleResult]
    triggered_rules: List[RuleResult]
    triggered_rule_ids: List[str]
    evidence_records: List[EvidenceRecord]
    final_decision: str
    final_report: Dict[str, Any]
    status: str
```

## 4. Rule Evidence & Association Behaviour

- **H08:** raised when evidence verification fails (missing/unmatched source snippets, out-of-range page citations, unanchored supplier or quotation identifiers) or when a required field is absent/ambiguous.
- **H09:** raised for conflicting delivery, advance, remaining-payment, supplier identity, VAT treatment, or purchase-request references, and for an unrecognised PR reference.
- **H10:** raised when `association_confidence < 0.8`.
- **PR aliases:** the authoritative CSV/UI reference is `PR-2026-114`. Generated assessment documents use `PR-2026-AGL-0089`, which is accepted as an alias for the same request. Any other reference triggers H09.

## 5. Persistence & Human Review

- `Verification.overall_decision` stores the machine decision and is never changed by `submit_human_review`.
- `triggered_rule_ids` is persisted from the workflow result. Historical rows with an empty value are repaired from their existing validation results during database initialisation without changing decisions.
- Serializers expose:
  - `machine_decision` — immutable rule-engine outcome.
  - `human_review_decision` — latest auditor outcome (`APPROVED_WITH_DISPENSATION`, `REJECTED`, `ESCALATED`, or null).
  - `effective_decision` — auditor approval/rejection when recorded; otherwise the machine decision. `ESCALATED` leaves the machine decision in force.
- `reset_all_data` clears verification/review rows and deletes files under `data/uploads/` while keeping the directory structure.

## 6. API Endpoints (implemented in `server.ts`)

- `GET /api/dashboard/summary`
- `GET /api/verifications?search=&decision=&limit=&offset=`
- `GET /api/verifications/:id`
- `GET /api/verifications/:id/results`
- `GET /api/verifications/:id/documents`
- `GET /api/verifications/:id/document` — streams the stored PDF, resolving legacy `file_path` values by basename when necessary
- `POST /api/documents/upload` and `POST /api/verifications` — upload and run the workflow
- `GET /api/reviews`
- `POST /api/reviews/:id/decision` and `POST /api/human-review`
- `GET /api/purchase-request`
- `POST /api/admin/reset`
- `GET /api/download/individual-pdf?supplier_id=...`
- `GET /api/raw-document/:filename` — legacy filename-based preview fallback
