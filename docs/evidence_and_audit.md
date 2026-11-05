# Evidence and Audit Trail Specification

Every decision produced by the Aamar Garments Ltd verification engine is anchored to verifiable source evidence extracted from the original PDF documents.

## 1. Evidence Record Schema

```json
{
  "rule_id": "R01",
  "document": "pack-02_quotation.pdf",
  "page_number": 1,
  "exact_text": "ITEM-A Cotton twill fabric, 280 gsm 12,000 metre 510.00 6,120,000.00",
  "extracted_value": "BDT 510.00 (+6.25%)",
  "expected_condition": "Not more than BDT 494.40 (<= +3.0%)",
  "calculation": "((510.00 - 480.00) / 480.00) * 100 = +6.25%",
  "status": "FAILED",
  "decision_effect": "REJECT"
}
```

## 2. Evidence Verification Integrity Rules

1. **Exact Quoted String:** The text snippet must appear verbatim in the source document text layer or OCR blocks. Fabricating placeholder text is strictly prohibited.
2. **Page Location:** The 1-indexed page number where the clause or line item appears must be recorded.
3. **Calculation Traceability:** When financial or percentage formulas are applied, the exact formula and step-by-step numbers are preserved.
4. **Human Review Immutability:** Human auditor notes, sign-offs, and override justifications are stored as `HumanReview` records. `Verification.overall_decision` (the machine decision) is never overwritten; API responses expose `machine_decision`, `human_review_decision`, and the computed `effective_decision`.
5. **Evidence Gate:** The workflow confirms that item snippets occur in the extracted text and that page citations are within range. A failure produces H08 and prevents the pack from being approved.
