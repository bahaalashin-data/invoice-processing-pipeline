# Runs parse_invoice() across a batch of PDFs

from pathlib import Path
from typing import List, Tuple

from pdf_engine.extractor import parse_invoice, InvoiceParsingError
from logger_config import get_logger

logger = get_logger(__name__)


def extract_all_invoices(pdf_paths: List[Path]) -> Tuple[List[dict], List[dict]]:
    """
    Returns (extracted, failed):
      - extracted: list of successfully parsed invoice dicts
      - failed:    list of {"source_file": ..., "reason": ...} for PDFs
                    that could not be parsed at all (e.g. corrupt file,
                    unrecognized layout)
    """
    extracted, failed = [], []

    for pdf_path in pdf_paths:
        pdf_path = Path(pdf_path)
        try:
            invoice_lines = parse_invoice(pdf_path)
            extracted.extend(invoice_lines)
        except InvoiceParsingError as e:
            logger.warning(f"Failed to parse {pdf_path.name}: {e}")
            failed.append({"source_file": pdf_path.name, "reason": str(e)})
        except Exception as e:  # corrupt / unreadable PDF, etc.
            logger.exception(f"Unexpected error reading {pdf_path.name}: {e}")
            failed.append({"source_file": pdf_path.name, "reason": f"Unreadable PDF: {e}"})

    logger.info(f"PDF extraction done: {len(extracted)} succeeded, {len(failed)} failed")
    return extracted, failed
