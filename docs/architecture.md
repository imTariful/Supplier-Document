# Architecture Documentation — Aamar Garments Ltd

## 1. System Architecture Overview

The Aamar Garments Ltd Supplier Document Verification System is a document intelligence platform designed to eliminate procurement risk. Built on the core principle:

> **"Structured extraction. Deterministic verification. Orchestrated workflow. Human oversight for uncertainty."**

The system uses deterministic pattern-based extraction with PyMuPDF, completely independent of any external AI services. A Python decision engine evaluates deterministic business rules with `Decimal` arithmetic to ensure 100% reproducibility and auditability.

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

The machine decision is persisted separately from any auditor decision. A human review can change the **effective** outcome but never rewrites the rule-engine result.

---

## 2. LangGraph 12-Node Sequential Workflow

The workflow is orchestrated via `langgraph.graph.StateGraph` using a typed state:

1. **`ingest_documents`**: Validates file existence and loads the authoritative purchase request.
2. **`extract_document_text`**: PyMuPDF extraction. Low-text PDFs run real OCR through Tesseract or EasyOCR; otherwise the embedded text layer is used.
3. **`assess_extraction_quality`**: Evaluates text density and routes unreadable documents to human review.
4. **`extract_structured_data`**: Pydantic models capture supplier details, validity, delivery, line items, totals, and T&C clauses. Optional Gemini values must be source-grounded.
5. **`identify_supplier_pack`**: Computes association confidence from document kind, supplier identity, and PR reference agreement. Below 0.8 produces H10.
6. **`validate_extracted_data`**: Strict schema validation with null safety.
7. **`verify_evidence`**: Confirms item snippets occur in the source text, page citations are in range, and identifiers are anchored. Failure produces H08 and short-circuits to rule evaluation.
8. **`compare_purchase_request`**: Calculates price and quantity deviations against `purchase-request.csv`.
9. **`validate_contract`**: Verifies agreement reference, identity, delivery, advance, balance payment, penalty, tax identity, and PR reference.
10. **`validate_financials`**: Recomputes line totals, subtotal, 15% VAT, and grand total independently.
11. **`evaluate_rules`**: Enforces decision priority (`REJECT > NEEDS_HUMAN_REVIEW > APPROVE`) and emits `triggered_rule_ids`.
12. **`generate_report`**: Produces the audit payload with evidence, association confidence, contract checks, and financial checks.

---

## 3. Error Routing & Safety Boundaries

- **Zero Silent Approvals:** Any unextractable, unanchored, or contradictory field escalates to `NEEDS_HUMAN_REVIEW`.
- **Hard Decision Precedence:** A rejection rule (`R01`–`R07`) always overrides review conditions (`H01`–`H10`).
- **LLM Guard Rails:** Gemini output is accepted only when it appears verbatim in the source text. Missing values stay missing; they are not inferred.
- **Audit Immutability:** `Verification.overall_decision` is the machine decision and is never overwritten by human review. `effective_decision` is computed from the latest auditor record.
- **Storage Cleanup:** Database reset deletes uploaded PDFs as well as verification rows, while preserving directory structure.
