# Known Limitations & Continuous Improvement

1. **OCR Requires a Local Engine:** Tesseract is preferred when its binary is installed; EasyOCR is the fallback. If neither is available, low-text/scanned PDFs are marked low-confidence and escalated to human review. The application does not fabricate OCR confidence.
2. **OCR Quality on Handwriting:** The OCR chain is tuned for printed text. Complex cursive handwriting may still require manual keying and review (`H08`).
3. **Gemini Is Optional:** Gemini gap-fill runs only when `GEMINI_API_KEY` is configured and core deterministic extraction is incomplete. Every value must appear verbatim in the source text, so fields genuinely absent from a document (for example a missing TIN) remain absent and trigger the corresponding rule.
4. **Currency Conversions:** Current procurement rules assume Bangladeshi Taka (BDT). Foreign-currency quotations require manual exchange-rate conversion.
5. **Multi-Part Shipments:** Delivery validation measures a single scheduled completion. Staggered partial shipments require commercial review approval.
6. **Bespoke Legal Riders:** Specialized indemnification clauses outside standard procurement articles are routed to human commercial review to prevent AI over-reach.
7. **PR Reference Aliases:** Only the documented alias pair `PR-2026-114` / `PR-2026-AGL-0089` is accepted automatically. New aliases must be added explicitly in `app/services/pr_service.py`.
