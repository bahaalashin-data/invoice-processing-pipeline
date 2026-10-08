# Checks a single invoice line against the business rules (data quality)

from datetime import datetime
from typing import Optional

from config import AMOUNT_MISMATCH_TOLERANCE_PCT
from logger_config import get_logger

logger = get_logger(__name__)

DATE_FORMAT = "%Y-%m-%d"


def _is_valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, DATE_FORMAT)
        return True
    except (ValueError, TypeError):
        return False


def validate_invoice(invoice: dict) -> Optional[str]:

    required = ["invoice_no", "invoice_date", "customer_name", "product_category","product_name", "quantity", "unit_price", "total_amount", "country",]
    for field in required:
        if invoice.get(field) in (None, ""):
            return f"Missing required field: {field}"

    # Date format (YYYY-MM-DD)
    if not _is_valid_date(invoice["invoice_date"]):
        return f"Invalid invoice_date format (expected YYYY-MM-DD): {invoice['invoice_date']}"

    # Numeric fields must be non-negative (and quantity > 0) 
    quantity = invoice["quantity"]
    unit_price = invoice["unit_price"]
    total_amount = invoice["total_amount"]

    if quantity <= 0:
        return f"Invalid quantity (must be > 0): {quantity}"
    if unit_price < 0:
        return f"Invalid unit_price (must be >= 0): {unit_price}"
    if total_amount < 0:
        return f"Invalid total_amount (must be >= 0): {total_amount}"

    # quantity * unit_price ~= total_amount
    expected_total = quantity * unit_price
    tolerance = max(0.01, expected_total * AMOUNT_MISMATCH_TOLERANCE_PCT)
    if abs(expected_total - total_amount) > tolerance:
        return (
            f"Amount mismatch: quantity ({quantity}) x unit_price ({unit_price}) "
            f"= {expected_total:.2f}, but total_amount = {total_amount:.2f}"
        )

    return None
