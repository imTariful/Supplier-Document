# Document Inventory — Aamar Garments Ltd Procurement System

**Inspection Date:** 2026-11-03  
**Purchase Request Reference:** PR-2026-114 (documents use accepted alias PR-2026-AGL-0089)  
**Total Documents Ingested:** 20 documents across 10 supplier packs (10 quotations, 10 supply agreements)  
**Authoritative Purchase Request:** `data/reference/purchase-request.csv`  

---

## 1. Document Inventory Table

| Document ID | Filename | Document Type | Supplier Identity | Page Count | Extraction Method | Document Pairing Status | Missing or Unreadable Information | Inspection Status |
|---|---|---|---|---|---|---|---|---|
| DOC-01-Q | `pack-01_quotation.pdf` | Quotation | Vertex Textiles & Trims Ltd | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-01_contract.pdf`) | None. Complete specifications, prices, validity, TIN & BIN present. | VERIFIED_INSPECTED |
| DOC-01-C | `pack-01_contract.pdf` | Contract | Vertex Textiles & Trims Ltd | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-01_quotation.pdf`) | None. Compliant delivery, payment (15% adv, 45d), 0.5% penalty. | VERIFIED_INSPECTED |
| DOC-02-Q | `pack-02_quotation.pdf` | Quotation | Apex Apparel Accessories Ltd | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-02_contract.pdf`) | Excessive unit price on ITEM-A (৳510 vs max ৳480; +6.25%). | VERIFIED_INSPECTED |
| DOC-02-C | `pack-02_contract.pdf` | Contract | Apex Apparel Accessories Ltd | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-02_quotation.pdf`) | Contract terms consistent with quotation. | VERIFIED_INSPECTED |
| DOC-03-Q | `pack-03_quotation.pdf` | Quotation | Bengal Stitch & Pack Solutions | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-03_contract.pdf`) | 25% advance payment stipulated. | VERIFIED_INSPECTED |
| DOC-03-C | `pack-03_contract.pdf` | Contract | Bengal Stitch & Pack Solutions | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-03_quotation.pdf`) | Article 3 demands 25% advance payment (> 20% limit). | VERIFIED_INSPECTED |
| DOC-04-Q | `pack-04_quotation.pdf` | Quotation | Meghna Fasteners & Accessories Ltd | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-04_contract.pdf`) | None on quotation side. | VERIFIED_INSPECTED |
| DOC-04-C | `pack-04_contract.pdf` | Contract | Meghna Fasteners & Accessories Ltd | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-04_quotation.pdf`) | Article 4 specifies insufficient late penalty rate of 0.25%/wk (< 0.5%). | VERIFIED_INSPECTED |
| DOC-05-Q | `pack-05_quotation.pdf` | Quotation | Padma Packaging & Labeling Corp | 1 | PyMuPDF (embedded text; raster image detected, OCR not required) | CONFIRMED_PAIRED (with `pack-05_contract.pdf`) | Missing Supplier TIN and BIN ("UNREGISTERED/PENDING"). | VERIFIED_INSPECTED |
| DOC-05-C | `pack-05_contract.pdf` | Contract | Padma Packaging & Labeling Corp | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-05_quotation.pdf`) | Article 1 missing statutory TIN and BIN numbers. | VERIFIED_INSPECTED |
| DOC-06-Q | `pack-06_quotation.pdf` | Quotation | Jamuna Yarn & Thread Mills | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-06_contract.pdf`) | Delivery promised in 52 days (> 45 days limit). | VERIFIED_INSPECTED |
| DOC-06-C | `pack-06_contract.pdf` | Contract | Jamuna Yarn & Thread Mills | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-06_quotation.pdf`) | Article 2 delivery schedule states 52 days. | VERIFIED_INSPECTED |
| DOC-07-Q | `pack-07_quotation.pdf` | Quotation | Rupsha Trims & Poly Industries | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-07_contract.pdf`) | Quoted price for ITEM-A is ৳488 (+1.67% above max ৳480). Delivery 38d. | VERIFIED_INSPECTED |
| DOC-07-C | `pack-07_contract.pdf` | Contract | Rupsha Trims & Poly Industries | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-07_quotation.pdf`) | Delivery 38 days (31-45 days window requires human review). | VERIFIED_INSPECTED |
| DOC-08-Q | `pack-08_quotation.pdf` | Quotation | Karnafuli Zipper & Button Co | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-08_contract.pdf`) | ITEM-A quoted qty is 10,000 m (deviation -16.67% > 5%). | VERIFIED_INSPECTED |
| DOC-08-C | `pack-08_contract.pdf` | Contract | Karnafuli Zipper & Button Co | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-08_quotation.pdf`) | Contract terms consistent with quotation. | VERIFIED_INSPECTED |
| DOC-09-Q | `pack-09_quotation.pdf` | Quotation | Shitalakshya Dyeing & Trims Ltd | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-09_contract.pdf`) | Quotation validity is only 20 days (< 30 days requirement). | VERIFIED_INSPECTED |
| DOC-09-C | `pack-09_contract.pdf` | Contract | Shitalakshya Dyeing & Trims Ltd | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-09_quotation.pdf`) | Remaining payment scheduled 75 days after delivery (> 60 days). | VERIFIED_INSPECTED |
| DOC-10-Q | `pack-10_quotation.pdf` | Quotation | Surma Carton & Packaging Works | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-10_contract.pdf`) | VAT not separately itemized at 15%; Subtotal has arithmetic discrepancy (+৳120,000). | VERIFIED_INSPECTED |
| DOC-10-C | `pack-10_contract.pdf` | Contract | Surma Carton & Packaging Works | 1 | PyMuPDF (Digital Text) | CONFIRMED_PAIRED (with `pack-10_quotation.pdf`) | Article 5 explicitly states VAT is not separately shown. | VERIFIED_INSPECTED |

---

## 2. Ingestion & Pairing Summary

- **Total Supplier Packs:** 10
- **Pairing Strategy:** Multi-key deterministic pairing using:
  1. Purchase Request reference token (`PR-2026-114` or accepted alias `PR-2026-AGL-0089`)
  2. Supplier Name matching (normalized string comparison)
  3. Supplier Pack ID correlation (`PACK-01` through `PACK-10`)
  4. Cross-document financial total correlation
- **Unpaired / Ambiguous Packs:** 0 (all 10 packs successfully resolved and confirmed).
