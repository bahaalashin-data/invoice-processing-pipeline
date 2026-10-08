# Cleans invoice records - strips whitespace and removes duplicates

from typing import List, Tuple
from logger_config import get_logger

logger = get_logger(__name__)


def clean_invoice(invoice: dict) -> dict:
    cleaned = dict(invoice)
    text_fields = ["invoice_no", "invoice_date", "customer_name", "product_category", "product_name", "country",]
    for field in text_fields:
        value = cleaned.get(field)
        if isinstance(value, str):
            cleaned[field] = " ".join(value.split())
    return cleaned


def deduplicate_invoices(invoices: List[dict]) -> Tuple[List[dict], List[dict]]:
    seen = set()
    unique, duplicates = [], []

    for invoice in invoices:
        key = (invoice.get("invoice_no"), invoice.get("product_name"), invoice.get("quantity"), invoice.get("unit_price"))
        if key in seen:
            duplicates.append({**invoice, "reason": f"Duplicate invoice line: {key[0]} / {key[1]}"})
            logger.warning(f"Duplicate invoice line skipped: "f"{invoice.get('invoice_no')} / "f"{invoice.get('product_name')}")
        else:
            seen.add(key)
            unique.append(invoice)

    return unique, duplicates
