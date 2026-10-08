# Reads one invoice PDF and extracts its fields (supports multi-line invoices)

from pathlib import Path
from typing import Optional
import pdfplumber


from logger_config import get_logger

logger = get_logger(__name__)

# if invoice PDFs are in different formats, define aliases for each format.
LABEL_ALIASES = {
    "invoice_no": ["invoice number", "invoice no", "invoice #"],
    "invoice_date": ["invoice date"],
    "created_date": ["created date"],
    "customer_name": ["customer name", "bill to", "billed to"],
    "country": ["country"],
    "product_category": ["product category", "category"],
    "product_name": ["product name", "product"],
    "quantity": ["quantity", "qty"],
    "unit_price": ["unit price"],
    "total_amount": ["total amount", "total"],
}

# Header names (lowercased) that identify the line-items table in FORMAT B
TABLE_HEADER_HINTS = {"category", "product", "quantity", "unit price", "total amount"}


class InvoiceParsingError(Exception):
    """Raised when required fields can't be extracted from a PDF."""


def _clean_number(raw: str) -> Optional[float]: #'1,847.84' / '800' / '16' -> float. Returns None if not parseable.
    
    if raw is None:
        return None
    cleaned = raw.replace(",", "").replace("$", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_label_value_lines(text: str) -> dict:

    fields = {}
    alias_lookup = {
        alias: canonical
        for canonical, aliases in LABEL_ALIASES.items()
        for alias in aliases
    }

    for line in text.splitlines():
        if ":" not in line:
            continue
        label, _, value = line.partition(":")
        label = label.strip().lower()
        value = value.strip()

        if label in alias_lookup and value:
            fields[alias_lookup[label]] = value

    return fields

def _parse_line_items_table(pdf_page) -> Optional[list[dict]]:    
    tables = pdf_page.extract_tables()
    for table in tables:

        if len(table) < 2:
            continue

        header = [str(cell).strip().lower()if cell is not None else " "for cell in table[0]]

        if not TABLE_HEADER_HINTS.issubset(set(header)):
            continue

        items = []

        for data_row in table[1:]:

            row = dict(zip(header, data_row))

            items.append(
                {
                    "product_category": row.get("category", "").strip(),
                    "product_name": row.get("product", "").strip(),
                    "quantity": row.get("quantity", "").strip(),
                    "unit_price": row.get("unit price", "").strip(),
                    "total_amount": row.get("total amount", "").strip(),
                }
            )

        return items
    return None

def parse_invoice(pdf_path: Path) -> list[dict]:

    pdf_path = Path(pdf_path)
    fields = {}

    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:raise InvoiceParsingError(f"{pdf_path.name}: PDF contains no pages")
        page = pdf.pages[0] #Each invoice PDF is expected to have all required fields on the first page.
        text = page.extract_text() or ""

        fields.update(_parse_label_value_lines(text))

        table_items = _parse_line_items_table(page)

        if not table_items:

            raise InvoiceParsingError(f"{pdf_path.name}: no invoice line items found")

        records = []

        for item in table_items:

            record = {
                **fields,
                **item,
            }

            record["quantity"] = _clean_number(
                record.get("quantity")
            )

            record["unit_price"] = _clean_number(
                record.get("unit_price")
            )

            record["total_amount"] = _clean_number(
                record.get("total_amount")
            )

            record["source_file"] = pdf_path.name

            records.append(record)        

    # Convert numeric fields
    for record in records:

        missing = [
            f
            for f in (
                "invoice_no",
                "invoice_date",
                "customer_name",
                "product_category",
                "product_name",
                "quantity",
                "unit_price",
                "total_amount",
                "country",
            )
            if not record.get(f)
            and record.get(f) != 0
        ]

        if missing:

            raise InvoiceParsingError(
                f"{pdf_path.name}: missing required field(s): "
                f"{', '.join(missing)}"
            )

    logger.info(
        f"Parsed {pdf_path.name} -> "
        f"{len(records)} line item(s)"
    )

    return records