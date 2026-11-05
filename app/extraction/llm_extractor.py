"""
Structured information extraction module.
Provides deterministic document parsing for supplier quotations and contracts.

The deterministic parser intentionally supports both the generated assessment
packs (e.g. ``ITEM-A``, ``Subtotal (Excl. VAT):``) and ordinary supplier
quotations where labels and values are on separate lines (e.g. ``Quotation no.``
followed by ``QT-2026-901`` and item codes such as ``A``/``C``).
"""

import json
import os
import re
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, Tuple, List
from app.schemas.models import ExtractedQuotation, ExtractedContract, QuotationLineItem

# ---------------------------------------------------------------------------
# Generic parsing helpers
# ---------------------------------------------------------------------------

_PURE_NUMBER_RE = re.compile(r"^[0-9][0-9,]*(?:\.[0-9]{1,4})?$")
_UNIT_RE = re.compile(r"^[A-Za-z][A-Za-z./\- ]{0,24}$")

_CURRENCY = r"(?:BDT|Tk\.?|৳)?"
# A monetary amount.  The lookahead prevents a VAT/penalty percentage from
# being mistaken for an amount (e.g. "VAT rate of 15%").
_AMOUNT = r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)(?!\s*%)"

_VAT_NOT_SEPARATE_PHRASES = (
    "vat not separately itemized",
    "vat not separately itemised",
    "vat not separately shown",
    "vat is not separately shown",
    "vat not separately stated",
    "vat not separately charged",
    "vat not itemized",
    "vat not itemised",
    "prices inclusive of all local taxes",
    "prices are inclusive of all taxes",
    "all contractual prices are inclusive",
    "vat inclusive",
)


def _normalize_ws(text: str) -> str:
    """Collapse all whitespace (including line breaks) into single spaces."""
    return re.sub(r"\s+", " ", text or "").strip()


def _to_decimal(value: Optional[str]) -> Optional[Decimal]:
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    if not cleaned or cleaned in (".", "-", "-."):
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _clean_label_value(value: str) -> str:
    value = value.split("|")[0]
    value = re.split(r"\bContact\s*:", value, flags=re.IGNORECASE)[0]
    return re.sub(r"\s+", " ", value).strip(" \t\r\n:-|")


def _extract_labeled_value(
    text: str,
    labels: List[str],
    value_pattern: str = r"[^\n\r|]+",
) -> str:
    """Find a label and its value, whether on the same line or the next line."""
    # Preferred: label starts a line (matches both "Label: value" and
    # "Label\nvalue" layouts).
    for label in labels:
        match = re.search(
            rf"(?:^|\n)[ \t]*(?:{label})[ \t]*[:#.]?[ \t]*(?:\r?\n[ \t]*)?({value_pattern})",
            text,
            re.IGNORECASE,
        )
        if match:
            value = _clean_label_value(match.group(1))
            if value:
                return value

    # Fallback: label appears inline after a separator such as "|".
    for label in labels:
        match = re.search(
            rf"(?<![A-Za-z0-9])(?:{label})[ \t]*[:#.]?[ \t]*(?:\r?\n[ \t]*)?({value_pattern})",
            text,
            re.IGNORECASE,
        )
        if match:
            value = _clean_label_value(match.group(1))
            if value:
                return value
    return ""


def _extract_supplier_name(text: str) -> str:
    match = re.search(r"Supplier\s*:\s*([^\n\r|]+)", text, re.IGNORECASE)
    if match:
        value = _clean_label_value(match.group(1))
        if value:
            return value

    # No explicit label (common on real supplier letterheads): use the first
    # company-looking line near the top of the document.
    company_hint = re.compile(
        r"\b(?:Ltd|Limited|LLC|L\.L\.C|Inc|Corp|Corporation|Company|Co\.|"
        r"Traders?|Trading|Mills?|Works|Industries|Enterprise|Enterprises|"
        r"Textiles?|Group|PLC|Pvt|Packaging|Garments?|Fashions?|Apparels?)\b",
        re.IGNORECASE,
    )
    skip_prefix = re.compile(
        r"^(?:to|buyer|address|date|reference|quotation|quote|item|description|"
        r"qty|quantity|unit|subtotal|vat|total|terms|payment|delivery|quality|"
        r"disputes|for\s+and\s+on|authori[sz]ed|article|agreement|contract|"
        r"commercial|supply\s+agreement)\b",
        re.IGNORECASE,
    )
    for line in text.splitlines()[:40]:
        candidate = line.strip()
        if not candidate or len(candidate) > 120 or ":" in candidate:
            continue
        if skip_prefix.match(candidate):
            continue
        if company_hint.search(candidate):
            return _clean_label_value(candidate)
    return "Unknown Supplier"


def _extract_quotation_no(text: str) -> str:
    return _extract_labeled_value(
        text,
        [
            r"Quotation\s+(?:Reference|No\.?|Number|Ref\.?)",
            r"Quote\s+(?:No\.?|Number|Ref\.?)",
        ],
        value_pattern=r"[A-Za-z0-9][A-Za-z0-9\-/_.]*",
    )


def _extract_pr_reference(text: str) -> str:
    value = _extract_labeled_value(
        text,
        [
            r"Purchase\s+Request\s+(?:Reference|No\.?|Number)",
            r"Reference\s+PR",
            r"PR\s+(?:No\.?|Number|Reference)",
        ],
        value_pattern=r"[A-Za-z0-9][A-Za-z0-9\-/_.]*",
    )
    if value:
        return value

    # Real documents often use a bare "Reference" label.
    match = re.search(
        r"(?:^|\n)[ \t]*Reference[ \t]*[:#.]?[ \t]*(?:\r?\n[ \t]*)?"
        r"([A-Za-z0-9][A-Za-z0-9\-/_.]*)",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    match = re.search(
        r"[|;][ \t]*Reference[ \t]*[:#.]?[ \t]*([A-Za-z0-9][A-Za-z0-9\-/_.]*)",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def _extract_date(text: str) -> str:
    match = re.search(
        r"(?:^|\n)[ \t]*Date[ \t]*[:#.]?[ \t]*(?:\r?\n[ \t]*)?([^\n\r|]+)",
        text,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"[|;][ \t]*Date[ \t]*[:#.]?[ \t]*([^\n\r|]+)",
            text,
            re.IGNORECASE,
        )
    if match:
        return _clean_label_value(match.group(1))
    return ""


def _extract_tin(text: str) -> Optional[str]:
    match = re.search(
        r"\b(?:Supplier\s+)?TIN\b\s*(?:No\.?|Number)?\s*[:#]?\s*([0-9][0-9\-]*)",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _extract_bin(text: str) -> Optional[str]:
    match = re.search(
        r"\b(?:Supplier\s+)?BIN\b\s*(?:No\.?|Number)?\s*[:#]?\s*([0-9][0-9\-]*)",
        text,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _extract_validity_days(text: str) -> Optional[int]:
    patterns = [
        r"validity(?:\s+is|\s*[:=])?\s*(\d+)\s*(?:calendar\s+)?days",
        r"valid\s+(?:for\s+)?(\d+)\s*(?:calendar\s+)?days",
        r"(\d+)\s*days?\s+(?:of\s+)?validity",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_delivery_days(text: str) -> Optional[int]:
    patterns = [
        r"deliver(?:y|ies)?(?:\s+the\s+complete\s+order)?\s+within\s+"
        r"(\d+)\s*(?:calendar\s+)?days",
        r"delivery\s+(?:schedule|period|timeframe|terms)?\s*[:of]?\s*"
        r"(\d+)\s*(?:calendar\s+)?days",
        r"promised\s+delivery\s+(?:within\s+)?(\d+)\s*(?:calendar\s+)?days",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_advance_pct(text: str) -> Optional[Decimal]:
    patterns = [
        r"(\d+(?:\.\d+)?)\s*%\s*advance",
        r"advance(?:\s+payment)?(?:\s+of)?\s*[:=]?\s*(\d+(?:\.\d+)?)\s*%",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return Decimal(match.group(1))
    return None


def _extract_remaining_days(text: str) -> Optional[int]:
    patterns = [
        r"(?:remainder|remaining|balance)[^.\n]{0,120}?(\d+)\s*days\s+"
        r"(?:after|from|of)\s+delivery",
        r"(?:settled|paid|payable|due)[^.\n]{0,60}?(\d+)\s*days\s+"
        r"(?:after|from|of)\s+delivery",
        r"(\d+)\s*days\s+after\s+delivery",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text or "")
    return [part.strip() for part in parts if part.strip()]


def _extract_penalty_rate(text: str) -> Optional[Decimal]:
    patterns = [
        r"(\d+(?:\.\d+)?)\s*%[^.;\n]{0,120}?"
        r"(?:per|each|every|for\s+each|for\s+every)\s+(?:full\s+)?week",
        r"(\d+(?:\.\d+)?)\s*%\s*(?:of\s+[^.]{0,80}?)?per\s+week",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return Decimal(match.group(1))
    return None


def _extract_penalty(text: str) -> Tuple[Optional[str], Optional[Decimal]]:
    # Preferred layout: an ARTICLE 4 liquidated-damages clause.
    match = re.search(
        r"ARTICLE\s+4\s*:.*?(?=\n+\s*ARTICLE\s+5\b|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        clause = match.group(0).strip()
        rate = _extract_penalty_rate(clause)
        if rate is not None:
            return clause, rate

    # Generic fallback: any sentence mentioning a late/delayed-delivery penalty.
    for sentence in _split_sentences(text):
        lowered = sentence.lower()
        if "penalt" not in lowered:
            continue
        if "late" not in lowered and "delay" not in lowered:
            continue
        rate = _extract_penalty_rate(sentence)
        if rate is not None:
            return sentence, rate

    # Keep an ambiguous penalty clause as evidence (rate remains None -> H08).
    for sentence in _split_sentences(text):
        lowered = sentence.lower()
        if "penalt" in lowered and ("late" in lowered or "delay" in lowered):
            return sentence, None

    if match:
        return match.group(0).strip(), None
    return None, None


def _has_negative_vat_phrase(text: str) -> bool:
    lowered = _normalize_ws(text).lower()
    return any(phrase in lowered for phrase in _VAT_NOT_SEPARATE_PHRASES)


def _quotation_vat_is_separate(text: str, vat_amount: Optional[Decimal]) -> bool:
    if _has_negative_vat_phrase(text):
        return False
    lowered = _normalize_ws(text).lower()
    if vat_amount is not None:
        return True
    return (
        "separately shown" in lowered
        or "separately itemized" in lowered
        or "separately itemised" in lowered
        or "15% vat separately" in lowered
    )


def _contract_vat_is_separate(text: str) -> bool:
    # Absence of a VAT statement in the contract should not contradict a
    # quotation that presents VAT separately; only explicit contradictions do.
    return not _has_negative_vat_phrase(text)


# ---------------------------------------------------------------------------
# Line-item parsing
# ---------------------------------------------------------------------------

def _load_pr_item_codes() -> List[str]:
    try:
        from app.services.pr_service import PurchaseRequestService
        return list(PurchaseRequestService.load_purchase_request().keys())
    except Exception:
        return []


def _parse_item_block(
    block: List[str],
) -> Optional[Tuple[str, Decimal, str, Decimal, Decimal]]:
    """Parse qty/unit/price/total from the lines belonging to one item row."""
    if not block:
        return None

    qty_idx = None
    for idx, line in enumerate(block):
        if _PURE_NUMBER_RE.match(line):
            qty_idx = idx
            break

    if qty_idx is not None and qty_idx + 3 < len(block):
        unit = block[qty_idx + 1].strip()
        if _UNIT_RE.match(unit):
            qty = _to_decimal(block[qty_idx])
            price = _to_decimal(block[qty_idx + 2])
            total = _to_decimal(block[qty_idx + 3])
            if qty is not None and price is not None and total is not None and qty > 0:
                description = re.sub(r"\s+", " ", " ".join(block[:qty_idx])).strip()
                if description:
                    return description, qty, unit, price, total

    # Fallback for rows where description and numbers share one line.
    joined = re.sub(r"\s+", " ", " ".join(block)).strip()
    match = re.search(
        r"^(.+?)\s+([0-9][0-9,]*)\s+([A-Za-z][A-Za-z./\-]*)\s+"
        r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s+"
        r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)$",
        joined,
    )
    if match:
        description = match.group(1).strip()
        qty = _to_decimal(match.group(2))
        price = _to_decimal(match.group(4))
        total = _to_decimal(match.group(5))
        if description and qty is not None and price is not None and total is not None and qty > 0:
            return description, qty, match.group(3).strip(), price, total

    return None


def _extract_items_from_pages(
    pages_text: List[str],
    item_codes: List[str],
) -> List[QuotationLineItem]:
    """
    Parse line items in a layout-tolerant way.

    Accepts canonical codes (``ITEM-A``) and short codes (``A``), with the
    description and numeric columns either on separate lines or in one row.
    Every discovered code is mapped back to its canonical purchase-request code.
    """
    if not item_codes:
        return []

    token_to_code: Dict[str, str] = {}
    for code in item_codes:
        upper = code.upper()
        token_to_code[upper] = code
        if upper.startswith("ITEM-") and len(upper) > 5:
            token_to_code[upper[5:]] = code

    tokens = sorted(token_to_code, key=lambda token: (-len(token), token))
    token_re = re.compile(
        r"^(?:" + "|".join(re.escape(token) for token in tokens) + r")"
        r"(?![A-Za-z0-9\-])\s*[.:)\-]?\s*(.*)$",
        re.IGNORECASE,
    )
    stop_re = re.compile(
        r"^(?:subtotal|vat\b|total\b|grand\s+total|supplier\s+(?:tin|bin)|"
        r"tin\b|bin\b|terms\s+(?:and|&)\s+conditions|delivery\s+terms|"
        r"quotation\s+validity|payment\s+terms|article\s+\d+|item\s+code|"
        r"description|quantity|unit(?:\s+price)?|line\s+total)\b",
        re.IGNORECASE,
    )

    items: List[QuotationLineItem] = []
    seen_codes = set()

    for page_idx, page_text in enumerate(pages_text):
        lines = [line.strip() for line in (page_text or "").splitlines()]
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            match = token_re.match(line) if line else None
            if not match:
                idx += 1
                continue

            raw_token = line.split()[0].rstrip(".:)-").upper()
            code = token_to_code.get(raw_token)
            if not code or code in seen_codes:
                idx += 1
                continue

            rest = match.group(1).strip()
            block: List[str] = [rest] if rest else []
            next_idx = idx + 1
            while next_idx < len(lines) and len(block) < 12:
                candidate = lines[next_idx]
                if token_re.match(candidate) or stop_re.match(candidate):
                    break
                if candidate:
                    block.append(candidate)
                next_idx += 1

            parsed = _parse_item_block(block)
            if parsed:
                description, qty, unit, price, total = parsed
                source_text = "\n".join([line] + block).strip()
                items.append(QuotationLineItem(
                    item_code=code,
                    description=description,
                    quantity=qty,
                    unit=unit,
                    unit_price=price,
                    line_total=total,
                    source_text=source_text,
                    page_number=page_idx + 1,
                ))
                seen_codes.add(code)

            idx = next_idx if next_idx > idx else idx + 1

    return items


# ---------------------------------------------------------------------------
# Financial totals
# ---------------------------------------------------------------------------

def _totals_text(text: str) -> str:
    """Normalise totals text and drop parentheticals.

    Dropping parentheticals prevents labels such as ``(Excl. VAT)`` or
    ``(Incl. VAT)`` from being mistaken for the VAT/grand-total line itself.
    """
    flat = _normalize_ws(text)
    return re.sub(r"\([^)]*\)", " ", flat)


def _extract_subtotal(text: str) -> Optional[Decimal]:
    flat = _totals_text(text)
    match = re.search(
        r"\bsub[\s-]?total\b\s*:?\s*" + _CURRENCY + r"\s*" + _AMOUNT,
        flat,
        re.IGNORECASE,
    )
    return _to_decimal(match.group(1)) if match else None


def _extract_vat_amount(text: str) -> Optional[Decimal]:
    flat = _totals_text(text)
    match = re.search(
        r"\b(?:total\s+)?(?:applicable\s+)?vat(?:\s+amount)?\b"
        r"\s*(?:@|at)?\s*"
        r"(?:[0-9]+(?:\.[0-9]+)?\s*%\s*)?"
        r"\s*:?\s*"
        + _CURRENCY + r"\s*" + _AMOUNT,
        flat,
        re.IGNORECASE,
    )
    return _to_decimal(match.group(1)) if match else None


def _extract_grand_total(text: str) -> Optional[Decimal]:
    flat = _totals_text(text)
    match = re.search(
        r"\b(?:grand\s+total|total\s+quoted\s+value|total\s+amount|"
        r"total\s+payable|total\s+price|total)\b"
        r"\s*:?\s*"
        + _CURRENCY + r"\s*" + _AMOUNT,
        flat,
        re.IGNORECASE,
    )
    return _to_decimal(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# Optional AI-assisted gap-filling (placeholder for future integration)
# ---------------------------------------------------------------------------

# This section is reserved for future AI/ML integration to assist with
# edge cases where deterministic parsing may not extract all fields.
# The system currently relies entirely on deterministic regex-based extraction
# to ensure 100% reproducibility and auditability.

def _no_ai_fallback_quotation(quotation: ExtractedQuotation, raw_text: str) -> ExtractedQuotation:
    """Deterministic extraction only - no AI fallback."""
    return quotation

def _no_ai_fallback_contract(contract: ExtractedContract, raw_text: str) -> ExtractedContract:
    """Deterministic extraction only - no AI fallback."""
    return contract

def _no_ai_fill_gaps(
    quotation: ExtractedQuotation,
    contract: ExtractedContract,
    raw_text: str,
) -> Tuple[ExtractedQuotation, ExtractedContract]:
    """Deterministic extraction only - no AI fallback."""
    return quotation, contract


class StructuredExtractor:
    @classmethod
    def extract_quotation(cls, doc_info: Dict[str, Any]) -> ExtractedQuotation:
        raw_text = doc_info.get("full_text", "")
        filename = doc_info.get("filename", "")
        doc_hash = doc_info.get("doc_hash", "")
        page_count = doc_info.get("page_count", 1)
        pages_text = doc_info.get("pages_text") or [raw_text]

        supplier_name = _extract_supplier_name(raw_text)
        quo_no = _extract_quotation_no(raw_text)
        pr_ref = _extract_pr_reference(raw_text)
        date_str = _extract_date(raw_text)
        tin = _extract_tin(raw_text)
        bin_num = _extract_bin(raw_text)

        validity_days = _extract_validity_days(raw_text)
        delivery_days = _extract_delivery_days(raw_text)
        advance_pct = _extract_advance_pct(raw_text)
        remaining_days = _extract_remaining_days(raw_text)

        items = _extract_items_from_pages(pages_text, _load_pr_item_codes())

        subtotal = _extract_subtotal(raw_text)
        vat_amount = _extract_vat_amount(raw_text)
        vat_separate = _quotation_vat_is_separate(raw_text, vat_amount)
        grand_total = _extract_grand_total(raw_text)

        quotation = ExtractedQuotation(
            supplier_name=supplier_name,
            quotation_no=quo_no,
            pr_reference=pr_ref,
            date_str=date_str,
            tin=tin,
            bin=bin_num,
            validity_days=validity_days,
            delivery_days=delivery_days,
            advance_pct=advance_pct,
            remaining_days=remaining_days,
            items=items,
            subtotal=subtotal,
            vat_amount=vat_amount,
            vat_separate=vat_separate,
            grand_total=grand_total,
            raw_text=raw_text,
            page_count=page_count,
            doc_hash=doc_hash,
            source_filename=filename,
        )
        return _no_ai_fallback_quotation(quotation, raw_text)

    @classmethod
    def extract_contract(cls, doc_info: Dict[str, Any]) -> ExtractedContract:
        raw_text = doc_info.get("full_text", "")
        filename = doc_info.get("filename", "")
        doc_hash = doc_info.get("doc_hash", "")
        page_count = doc_info.get("page_count", 1)

        agr_no = _extract_labeled_value(
            raw_text,
            [r"Agreement\s+No\.?", r"Contract\s+Reference"],
            value_pattern=r"[A-Za-z0-9][A-Za-z0-9\-/_.]*",
        )
        pr_ref = _extract_pr_reference(raw_text)
        supplier_name = _extract_supplier_name(raw_text)
        tin = _extract_tin(raw_text)
        bin_num = _extract_bin(raw_text)

        delivery_days = _extract_delivery_days(raw_text)
        advance_pct = _extract_advance_pct(raw_text)
        remaining_days = _extract_remaining_days(raw_text)

        penalty_clause, penalty_rate_pct = _extract_penalty(raw_text)
        penalty_basis = (
            "order_value_per_week"
            if penalty_clause and "order value" in _normalize_ws(penalty_clause).lower()
            else "unspecified"
        )

        contract = ExtractedContract(
            agreement_no=agr_no,
            supplier_name=supplier_name,
            pr_reference=pr_ref,
            tin=tin,
            bin=bin_num,
            delivery_days=delivery_days,
            advance_pct=advance_pct,
            remaining_days=remaining_days,
            penalty_clause=penalty_clause,
            penalty_rate_pct=penalty_rate_pct,
            penalty_basis=penalty_basis,
            vat_separate=_contract_vat_is_separate(raw_text),
            raw_text=raw_text,
            page_count=page_count,
            doc_hash=doc_hash,
            source_filename=filename,
        )
        return _no_ai_fallback_contract(contract, raw_text)

    @classmethod
    def extract_combined_document(
        cls, doc_info: Dict[str, Any]
    ) -> Tuple[ExtractedQuotation, ExtractedContract]:
        """
        Extracts both logical sections (Section A: Quotation, Section B: Terms &
        Conditions) from a single combined supplier document PDF.
        Preserves exact page tracking, evidence citations, and handles sections
        appearing in any order.
        """
        raw_text = doc_info.get("full_text", "")
        filename = doc_info.get("filename", "")
        doc_hash = doc_info.get("doc_hash", "")
        page_count = doc_info.get("page_count", 1)
        pages_text: List[str] = doc_info.get("pages_text") or [raw_text]

        # 1. Identify section locations across pages
        quo_page_idx = 0
        terms_page_idx = 1 if len(pages_text) > 1 else 0

        for p_idx, p_text in enumerate(pages_text):
            lower_text = p_text.lower()
            if "quotation" in lower_text or "line total" in lower_text or "unit price" in lower_text:
                quo_page_idx = p_idx
            if ("agreement" in lower_text or "terms and conditions" in lower_text
                    or "terms & conditions" in lower_text or "article" in lower_text
                    or "late-delivery penalty" in lower_text):
                terms_page_idx = p_idx

        quo_text = pages_text[quo_page_idx] if quo_page_idx < len(pages_text) else raw_text

        # 2. Global supplier identity and tax numbers
        supplier_name = _extract_supplier_name(raw_text)
        tin = _extract_tin(raw_text)
        bin_num = _extract_bin(raw_text)
        pr_ref = _extract_pr_reference(raw_text)

        # Quotation metadata (prefer the quotation page, fall back to full text)
        quo_no = _extract_quotation_no(quo_text) or _extract_quotation_no(raw_text)
        date_str = _extract_date(quo_text) or _extract_date(raw_text)
        validity_days = _extract_validity_days(raw_text)

        # Delivery / payment terms are usually in the T&C section.
        delivery_days = _extract_delivery_days(raw_text)
        advance_pct = _extract_advance_pct(raw_text)
        remaining_days = _extract_remaining_days(raw_text)

        items = _extract_items_from_pages(pages_text, _load_pr_item_codes())

        # Financial totals belong to the quotation section.  Using quo_text
        # avoids accidentally reading VAT percentages from the contract text.
        subtotal = _extract_subtotal(quo_text)
        vat_amount = _extract_vat_amount(quo_text)
        quotation_vat_separate = _quotation_vat_is_separate(quo_text, vat_amount)
        contract_vat_separate = _contract_vat_is_separate(raw_text)
        grand_total = _extract_grand_total(quo_text)

        structured_q = ExtractedQuotation(
            supplier_name=supplier_name,
            quotation_no=quo_no,
            pr_reference=pr_ref,
            date_str=date_str,
            tin=tin,
            bin=bin_num,
            validity_days=validity_days,
            delivery_days=delivery_days,
            advance_pct=advance_pct,
            remaining_days=remaining_days,
            items=items,
            subtotal=subtotal,
            vat_amount=vat_amount,
            vat_separate=quotation_vat_separate,
            grand_total=grand_total,
            raw_text=raw_text,
            page_count=page_count,
            doc_hash=doc_hash,
            source_filename=filename,
        )

        # --- SECTION B: TERMS AND CONDITIONS EXTRACTION ---
        agr_no = _extract_labeled_value(
            raw_text,
            [r"Agreement\s+No\.?", r"Contract\s+Reference"],
            value_pattern=r"[A-Za-z0-9][A-Za-z0-9\-/_.]*",
        )

        penalty_clause, penalty_rate_pct = _extract_penalty(raw_text)
        penalty_basis = (
            "order_value_per_week"
            if penalty_clause and "order value" in _normalize_ws(penalty_clause).lower()
            else "unspecified"
        )

        structured_c = ExtractedContract(
            agreement_no=agr_no or quo_no,
            supplier_name=supplier_name,
            pr_reference=pr_ref,
            tin=tin,
            bin=bin_num,
            delivery_days=delivery_days,
            advance_pct=advance_pct,
            remaining_days=remaining_days,
            penalty_clause=penalty_clause,
            penalty_rate_pct=penalty_rate_pct,
            penalty_basis=penalty_basis,
            vat_separate=contract_vat_separate,
            raw_text=raw_text,
            page_count=page_count,
            doc_hash=doc_hash,
            source_filename=filename,
        )

        return _no_ai_fill_gaps(structured_q, structured_c, raw_text)
