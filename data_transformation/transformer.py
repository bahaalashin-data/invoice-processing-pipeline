# Runs cleaning + validation on extracted invoices, splits them into valid/rejected

from typing import List, Tuple, Optional

from data_transformation.validator import validate_invoice
from logger_config import get_logger

from datetime import datetime
from config import REQUIRE_SAME_INVOICE_MONTH

from data_transformation.cleaner import (clean_invoice, deduplicate_invoices,)


logger = get_logger(__name__)

TRANSPORT_FIELDS = ["invoice_no", "message_id", "invoice_date", "customer_name", "product_category","product_name", "quantity", "unit_price", "total_amount", "country","created_date",]


def build_transport_record(invoice: dict) -> dict:
    return {field: invoice.get(field) for field in TRANSPORT_FIELDS}


def validate_same_invoice_month(invoices: List[dict]) -> Optional[str]:

    months = set()

    for invoice in invoices:

        invoice_date = invoice.get("invoice_date")

        try:
            parsed_date = datetime.strptime(invoice_date, "%Y-%m-%d")

            months.add(parsed_date.strftime("%Y-%m"))

        except Exception:

            logger.warning(f"Could not parse invoice date: {invoice_date}")

            continue


    if len(months) > 1:
        return (
            "Multiple invoice months detected: "
            f"{', '.join(sorted(months))}"
        )

    return None


def transform_invoices(
    extracted: List[dict],
    pre_failed: Optional[List[dict]] = None,
) -> Tuple[List[dict], List[dict]]:

    rejected: List[dict] = list(pre_failed or [])
    # Step 1: Clean data
    cleaned = [clean_invoice(inv) for inv in extracted]
    # Step 2: Remove duplicates
    unique, duplicates = deduplicate_invoices(cleaned)
    rejected.extend(duplicates)

    # Step 3: Same invoice month validation
    if REQUIRE_SAME_INVOICE_MONTH:

        month_error = validate_same_invoice_month(unique)

        if month_error:

            logger.warning(month_error)

            for invoice in unique:

                rejected.append(
                    {
                        **invoice,
                        "record_status": "REJECTED",
                        "rejection_reason": month_error,
                        "reason": month_error,
                    }
                )

            unique = []

    # Step 4: Validate invoices
    valid: List[dict] = []
    for invoice in unique:
        reason = validate_invoice(invoice)
        if reason:

            rejected.append({**invoice, "record_status": "REJECTED", "rejection_reason": reason, "reason": reason})

            logger.warning(f"Rejected {invoice.get('invoice_no', '?')}: {reason}")
        else:
            record = build_transport_record(invoice)

            record["record_status"] = "VALID"
            record["rejection_reason"] = None

            valid.append(record)

    logger.info(
        f"Transformation done: {len(valid)} valid, {len(rejected)} rejected "
        f"({len(pre_failed or [])} parse failures + "
        f"{len(duplicates)} duplicates + "
        f"{len(rejected) - len(duplicates) - len(pre_failed or [])} failed validation)"
    )

    return valid, rejected
