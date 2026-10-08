# Extracts the PDF invoices out of a downloaded ZIP file

import zipfile
from pathlib import Path
from typing import List

from config import EXTRACTED_PDFS_DIR
from logger_config import get_logger

logger = get_logger(__name__)

class InvalidInvoiceZip(Exception):
    """Raised when the ZIP is missing, corrupted, or has no PDFs inside."""


def extract_pdfs_from_zip(zip_path: Path) -> List[Path]:
    #Extracts every pdfs file found inside zip_path into its own subfolder.
    
    zip_path = Path(zip_path)

    if not zip_path.exists():
        raise InvalidInvoiceZip(f"ZIP file not found: {zip_path}")

    if not zipfile.is_zipfile(zip_path):
        raise InvalidInvoiceZip(f"File is not a valid ZIP: {zip_path}")

    run_folder = Path(EXTRACTED_PDFS_DIR) / zip_path.stem
    run_folder.mkdir(parents=True, exist_ok=True)

    extracted_paths: List[Path] = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        pdf_names = [n for n in zf.namelist() if n.lower().endswith(".pdf")]

        if not pdf_names:
            raise InvalidInvoiceZip(f"No PDF files found inside {zip_path.name}")

        for name in pdf_names:
            safe_name = Path(name).name

            target_path = run_folder / safe_name

            counter = 1

            while target_path.exists():

                target_path = (
                    run_folder /
                    f"{Path(safe_name).stem}_{counter}.pdf"
                )

                counter += 1            

            with zf.open(name) as source, open(target_path, "wb") as target:
                target.write(source.read())

            extracted_paths.append(target_path)

    logger.info(f"Extracted {len(extracted_paths)} PDF(s) from {zip_path.name} -> {run_folder}")
    return extracted_paths
