# Business Rules Specification & Source of Truth

**Company:** Aamar Garments Ltd  
**Version:** 2.1.0-deterministic  
**Governing Standard:** Procurement Policy Manual 2026  

---

## 1. Decision Precedence

The evaluation engine enforces the following non-negotiable priority:
$$\text{REJECT} > \text{NEEDS\_HUMAN\_REVIEW} > \text{APPROVE}$$

All rules are evaluated simultaneously, preserving all findings even if an earlier failure has already been detected.

---

## 2. Rejection Rules (R01–R07)

### R01 — Excessive Unit Price
- **Formula:** $\text{price\_deviation} = \frac{\text{quoted\_price} - \text{maximum\_price}}{\text{maximum\_price}} \times 100$
- **Condition:** $\text{price\_deviation} > 3.0\%$
- **Boundary:**
  - $\le 0.0\%$: PASS
  - $0.0\% < \text{dev} \le 3.0\%$: HUMAN REVIEW (H01)
  - $> 3.0\%$: REJECT (R01)
- **Severity:** REJECT

### R02 — Excessive Advance Payment
- **Condition:** $\text{advance\_pct} > 20.0\%$
- **Boundary:**
  - $20.0\%$: PASS
  - $20.01\%$: REJECT
- **Severity:** REJECT

### R03 — Missing Late-Delivery Penalty Clause
- **Condition:** Contract agreement contains no clause stipulating liquidated damages or penalty for delayed shipment.
- **Severity:** REJECT

### R04 — Missing Supplier TIN
- **Condition:** 12-digit Taxpayer Identification Number missing or listed as unregistered/pending.
- **Severity:** REJECT

### R05 — Missing Supplier BIN
- **Condition:** 9-digit Business Identification Number (VAT registration) missing or unregistered.
- **Severity:** REJECT

### R06 — Excessive Delivery Period
- **Condition:** Promised delivery $> 45$ calendar days from purchase order date.
- **Boundary:**
  - $\le 30$ days: PASS
  - $31$ to $45$ days: HUMAN REVIEW (H04)
  - $> 45$ days: REJECT (R06)
- **Severity:** REJECT

### R07 — Insufficient Late-Delivery Penalty Rate
- **Condition:** Penalty rate $< 0.5\%$ of total order value per week of unexcused delay.
- **Boundary:**
  - $\ge 0.5\% / \text{week}$: PASS
  - $< 0.5\% / \text{week}$: REJECT
  - Ambiguous basis or timeline: HUMAN REVIEW (H08)
- **Severity:** REJECT

---

## 3. Human Review Rules (H01–H10)

| Rule ID | Name | Trigger Condition | Boundary | Severity |
|---|---|---|---|---|
| **H01** | Minor Price Deviation | Quoted unit price exceeds maximum price by $\le 3.0\%$ | $0\% < \text{dev} \le 3.0\%$ | HUMAN_REVIEW |
| **H02** | Quantity Deviation | Quoted quantity diverges from requested quantity by $> 5.0\%$ | $\text{abs}(\text{quo} - \text{req}) / \text{req} \times 100 > 5.0\%$ | HUMAN_REVIEW |
| **H03** | Payment Terms Outside Window | Remaining payment deadline $< 30$ days or $> 60$ days after delivery, or unmeasured from delivery event | $< 30\text{d}$ or $> 60\text{d}$ | HUMAN_REVIEW |
| **H04** | Delivery Period Review | Promised delivery within $31$ to $45$ days | $31 \le \text{days} \le 45$ | HUMAN_REVIEW |
| **H05** | VAT Non-Compliant Presentation | VAT not separately itemized at statutory 15% | Not shown separately or rate $\ne 15\%$ | HUMAN_REVIEW |
| **H06** | Financial Arithmetic Inconsistency | $\text{Line Total} \ne \text{Qty} \times \text{Unit Price}$ or $\text{Subtotal} \ne \sum \text{Line Totals}$ or $\text{Grand Total} \ne \text{Subtotal} + \text{VAT}$ | Difference $> \text{BDT } 0.05$ | HUMAN_REVIEW |
| **H07** | Quotation Validity Inadequate | Validity period $< 30$ calendar days | $< 30$ days | HUMAN_REVIEW |
| **H08** | Uncertain or Missing Evidence | Critical field absent, illegible, or unanchored to source text; validation fails if a snippet is not in the PDF, a page citation is out of range, or an identifier cannot be anchored | Any failed evidence check | HUMAN_REVIEW |
| **H09** | Conflicting Document Terms | Quotation and Contract contradict on delivery, advance, remaining payment, supplier identity, VAT treatment, or purchase-request reference; an unrecognised PR reference also triggers this rule | Discrepancy or invalid reference detected | HUMAN_REVIEW |
| **H10** | Ambiguous Document Association | Quotation and Contract cannot be paired with high confidence | Association confidence $< 0.8$ | HUMAN_REVIEW |

---

## 4. Approval Rule

A supplier pack is granted **APPROVE** status strictly when:
1. All mandatory fields have verified source text and page references.
2. All 5 requested items match with 100% item code coverage.
3. Every quoted unit price $\le \text{maximum price}$.
4. Every quoted quantity deviation $\le 5.0\%$.
5. Advance payment $\le 20.0\%$.
6. Remaining payment clearly payable within $30$–$60$ days after delivery.
7. Delivery promised within $\le 30$ calendar days.
8. Statutory 15% VAT is separately itemized.
9. Valid TIN and BIN numbers are verified.
10. Penalty clause provides $\ge 0.5\%$ per week on order value.
11. Quotation validity is $\ge 30$ days.
12. All financial calculations balance to within BDT 0.05.
13. The document references `PR-2026-114` or its accepted legacy alias `PR-2026-AGL-0089`.
14. No rejection condition (R01–R07) is triggered.
15. No human review condition (H01–H10) is triggered.
