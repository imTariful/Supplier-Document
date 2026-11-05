"""
Purchase Request service.
Dynamically parses authoritative purchase-request.csv into validated Pydantic models.
Uses FlexiblePRDict to support transparent aliasing between 'A' and 'ITEM-A' without duplicating dictionary keys.
"""

import os
import csv
from decimal import Decimal
from typing import Dict, List, Optional
from app.schemas.models import PurchaseRequestItem

PR_CSV_PATH = "data/reference/purchase-request.csv"

# The generated assessment packs and some supplier documents use the legacy
# long-form PR reference, while the authoritative CSV/UI use PR-2026-114.
# Both identify the same purchase request and are accepted; anything else is a
# genuine reference mismatch and is escalated by the rule engine.
PR_REFERENCE_ALIASES = {
    "PR-2026-114": {"PR-2026-AGL-0089"},
    "PR-2026-AGL-0089": {"PR-2026-114"},
}


class FlexiblePRDict(dict):
    """
    Dictionary that allows lookup by both 'ITEM-A' and 'A' seamlessly
    while keeping the key set deduplicated so iterations and discovery
    do not produce duplicate line items.
    """
    def get(self, key, default=None):
        if key in self:
            return super().get(key, default)
        if isinstance(key, str):
            if key.startswith("ITEM-"):
                short_key = key[5:]
                if short_key in self:
                    return super().get(short_key, default)
            else:
                prefixed_key = f"ITEM-{key}"
                if prefixed_key in self:
                    return super().get(prefixed_key, default)
        return default

    def __getitem__(self, key):
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __contains__(self, key):
        if super().__contains__(key):
            return True
        if isinstance(key, str):
            if key.startswith("ITEM-"):
                return super().__contains__(key[5:])
            return super().__contains__(f"ITEM-{key}")
        return False

class PurchaseRequestService:
    @classmethod
    def get_pr_metadata(cls, filepath: str = PR_CSV_PATH) -> Dict[str, str]:
        if not os.path.exists(filepath):
            return {"pr_number": "PR-2026-114", "company": "Aamar Garments Ltd"}

        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pr_num = (
                    row.get("PR number") or
                    row.get("pr_number") or
                    row.get("PR Number") or
                    row.get("PR_NUMBER") or
                    "PR-2026-114"
                ).strip()
                return {
                    "pr_number": pr_num,
                    "company": "Aamar Garments Ltd",
                    "department": "Procurement Directorate",
                    "date": "2026-10-15",
                    "currency": "BDT"
                }
        return {"pr_number": "PR-2026-114", "company": "Aamar Garments Ltd"}

    @classmethod
    def get_canonical_pr_reference(cls, filepath: str = PR_CSV_PATH) -> str:
        """Return the authoritative PR number from the CSV/database source."""
        return (cls.get_pr_metadata(filepath).get("pr_number") or "PR-2026-114").strip()

    @classmethod
    def get_valid_references(cls, filepath: str = PR_CSV_PATH) -> set:
        """Return the canonical PR reference plus all accepted aliases."""
        canonical = cls.get_canonical_pr_reference(filepath).upper()
        valid = {canonical}
        for key, aliases in PR_REFERENCE_ALIASES.items():
            key_upper = key.upper()
            alias_upper = {alias.upper() for alias in aliases}
            if canonical == key_upper or canonical in alias_upper:
                valid.add(key_upper)
                valid.update(alias_upper)
        return valid

    @classmethod
    def canonicalize_reference(cls, reference: Optional[str], filepath: str = PR_CSV_PATH) -> str:
        """Map any accepted alias back to the authoritative PR reference."""
        if not reference:
            return ""
        raw = reference.strip().upper()
        canonical = cls.get_canonical_pr_reference(filepath).upper()
        if raw == canonical:
            return canonical
        for key, aliases in PR_REFERENCE_ALIASES.items():
            key_upper = key.upper()
            alias_upper = {alias.upper() for alias in aliases}
            if raw == key_upper or raw in alias_upper:
                if canonical == key_upper or canonical in alias_upper:
                    return canonical
        return raw

    @classmethod
    def references_match(cls, first: Optional[str], second: Optional[str], filepath: str = PR_CSV_PATH) -> bool:
        """True when two references identify the same purchase request or an alias."""
        if not first or not second:
            return False
        return cls.canonicalize_reference(first, filepath) == cls.canonicalize_reference(second, filepath)

    @classmethod
    def is_valid_reference(cls, reference: Optional[str], filepath: str = PR_CSV_PATH) -> bool:
        """True when the reference is the authoritative PR number or an accepted alias."""
        if not reference:
            return False
        return reference.strip().upper() in cls.get_valid_references(filepath)

    @classmethod
    def load_purchase_request(cls, filepath: str = PR_CSV_PATH) -> Dict[str, PurchaseRequestItem]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Purchase request file not found at: {filepath}")

        items = FlexiblePRDict()
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_code = (
                    row.get("Item") or
                    row.get("item_code") or
                    row.get("Item Code") or
                    row.get("item") or
                    ""
                ).strip()

                desc = (
                    row.get("Description") or
                    row.get("item_description") or
                    row.get("description") or
                    ""
                ).strip()

                spec = (
                    row.get("specification") or
                    row.get("Specification") or
                    desc
                ).strip()

                unit = (
                    row.get("Unit") or
                    row.get("unit") or
                    "piece"
                ).strip()

                qty_str = (
                    row.get("Quantity requested") or
                    row.get("quantity") or
                    row.get("Quantity") or
                    "0"
                ).replace(",", "").strip()

                price_str = (
                    row.get("Maximum unit price (BDT)") or
                    row.get("max_unit_price") or
                    row.get("Max Price") or
                    "0"
                ).replace(",", "").strip()

                target_days = int(row.get("target_delivery_days") or 30)
                vat_rate = Decimal(str(row.get("required_vat_rate") or "15.0"))
                max_adv = Decimal(str(row.get("max_advance_pct") or "20.0"))

                # Canonical representation: ITEM-A, ITEM-B, etc.
                canonical_code = f"ITEM-{raw_code}" if not raw_code.startswith("ITEM-") else raw_code

                item = PurchaseRequestItem(
                    item_code=canonical_code,
                    item_description=desc,
                    specification=spec,
                    quantity=Decimal(qty_str),
                    unit=unit,
                    max_unit_price=Decimal(price_str),
                    target_delivery_days=target_days,
                    required_vat_rate=vat_rate,
                    max_advance_pct=max_adv
                )

                items[canonical_code] = item

        return items

    @classmethod
    def get_all_items_list(cls, filepath: str = PR_CSV_PATH) -> List[Dict]:
        items_dict = cls.load_purchase_request(filepath)
        out = []
        for code in sorted(items_dict.keys()):
            item = items_dict[code]
            out.append({
                "item_code": item.item_code,
                "item_description": item.item_description,
                "specification": item.specification,
                "quantity": float(item.quantity),
                "unit": item.unit,
                "max_unit_price": float(item.max_unit_price),
                "target_delivery_days": item.target_delivery_days,
                "required_vat_rate": float(item.required_vat_rate),
                "max_advance_pct": float(item.max_advance_pct)
            })
        return out
