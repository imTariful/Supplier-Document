# Testing Execution Report

**Date of Execution:** 2026-11-05  
**Test Framework:** pytest 9.2.0 (Python 3.11.2)  
**Total Tests:** 49  
**Passed:** 49  
**Failed:** 0  
**Test Execution Duration:** 5.64 seconds  

---

## 1. Test Suite Summary

| Test Module | Coverage Area | Tests Run | Result |
|---|---|---|---|
| `tests/test_rules_boundary.py` | Price, quantity, advance, delivery, payment, penalty, tax ID, VAT, validity, arithmetic boundaries | 27 | 27 / 27 PASSED |
| `tests/test_workflow_e2e.py` | PyMuPDF extraction, OCR flag, LangGraph pipeline, PACK-01/02/03/04/07, combined documents, triggered IDs and pack identification | 10 | 10 / 10 PASSED |
| `tests/test_extraction_layouts.py` | Real-world layout, generated pack layout, PACK-10 wrapped total | 3 | 3 / 3 PASSED |
| `tests/test_rule_evidence_association.py` | PR alias matching, H08 evidence failure, H09 conflicts/reference mismatch, H10 low association confidence | 5 | 5 / 5 PASSED |
| `tests/test_optional_extraction.py` | Real OCR fallback invocation and Gemini source-grounding guard rails | 2 | 2 / 2 PASSED |
| `tests/test_review_and_reset.py` | Immutable machine decision, effective decision, pending queue, upload cleanup on reset | 2 | 2 / 2 PASSED |

---

## 2. Mandatory Boundary Tests Verification

1. **Price Boundary:**
   - Quoted BDT 480.00 (exact maximum) -> **PASS**
   - Quoted BDT 485.00 (+1.04% <= 3%) -> **HUMAN_REVIEW (H01)**
   - Quoted BDT 494.40 (exactly +3.0%) -> **HUMAN_REVIEW (H01)**
   - Quoted BDT 495.00 (+3.125% > 3%) -> **REJECT (R01)**

2. **Advance Payment Boundary:**
   - Exactly 20.0% advance -> **PASS**
   - 20.01% advance -> **REJECT (R02)**
   - Missing advance terms -> **HUMAN_REVIEW (H08)**

3. **Quantity Boundary:**
   - Exactly 5.0% deviation (11,400 vs 12,000) -> **PASS**
   - Greater than 5.0% deviation (10,000 vs 12,000; -16.67%) -> **HUMAN_REVIEW (H02)**

4. **Delivery Schedule Boundary:**
   - 30 days -> **PASS**
   - 31 days -> **HUMAN_REVIEW (H04)**
   - Exactly 45 days -> **HUMAN_REVIEW (H04)**
   - 46 days -> **REJECT (R06)**

5. **Payment Terms Boundary:**
   - Exactly 30 days after delivery -> **PASS**
   - Exactly 60 days after delivery -> **PASS**
   - Less than 30 days after delivery -> **HUMAN_REVIEW (H03)**
   - Greater than 60 days after delivery (75 days) -> **HUMAN_REVIEW (H03)**
   - Missing reference delivery milestone -> **HUMAN_REVIEW (H03)**

6. **Penalty Clause Boundary:**
   - Missing penalty clause -> **REJECT (R03)**
   - Insufficient rate 0.25% per week -> **REJECT (R07)**
   - Exactly 0.5% per week on order value -> **PASS**
   - 0.75% per week -> **PASS**

---

## 3. New Regression Coverage

- **PACK-10 wrapped total:** the label `Total Quoted Value (All-inclusive, VAT not\nseparated):` extracts `BDT 7,260,000.00`; rules emit `H05|H06`.
- **Layout tolerance:** ordinary supplier quotations with next-line values and short item codes (`A`) extract the same fields as generated packs (`ITEM-A`).
- **PR aliases:** `PR-2026-AGL-0089` is accepted against the authoritative `PR-2026-114`; unknown references trigger H09.
- **Evidence routing:** `evidence_verified=False` produces H08 and still reaches rule evaluation.
- **Association routing:** `association_confidence < 0.8` produces H10.
- **Human review immutability:** after `APPROVED_WITH_DISPENSATION`, `overall_decision` and `machine_decision` remain `NEEDS_HUMAN_REVIEW`, while `effective_decision` is `APPROVED`.
- **Reset cleanup:** database rows and `data/uploads/` files are removed while directories remain.

---

## 4. 10-Document Challenge Evaluation

`python evaluation/evaluate.py` produces:

- Correct decisions: **10 / 10**
- Accuracy: **100.0%**
- False approvals: **0**
- PACK-10 triggered rules: **H05, H06**

| Pack | Expected | Actual | Triggered Rules |
|---|---|---|---|
| PACK-01 | APPROVE | APPROVE | — |
| PACK-02 | REJECT | REJECT | R01 |
| PACK-03 | REJECT | REJECT | R02 |
| PACK-04 | REJECT | REJECT | R07 |
| PACK-05 | REJECT | REJECT | R04, R05 |
| PACK-06 | REJECT | REJECT | R06 |
| PACK-07 | NEEDS_HUMAN_REVIEW | NEEDS_HUMAN_REVIEW | H01, H04 |
| PACK-08 | NEEDS_HUMAN_REVIEW | NEEDS_HUMAN_REVIEW | H02 |
| PACK-09 | NEEDS_HUMAN_REVIEW | NEEDS_HUMAN_REVIEW | H03, H07 |
| PACK-10 | NEEDS_HUMAN_REVIEW | NEEDS_HUMAN_REVIEW | H05, H06 |
