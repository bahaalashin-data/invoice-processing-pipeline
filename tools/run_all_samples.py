# Runs the pipeline (Local Mode) against every ZIP in sample_data/
# Usage: python tools/run_all_samples.py

import sys
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parent.parent))

from main import run_pipeline
from logger_config import get_logger

logger = get_logger(__name__)

SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent / "sample_data"


def main():
    zip_files = sorted(SAMPLE_DATA_DIR.glob("*.zip"))

    if not zip_files:
        logger.info(f"No ZIP files found in {SAMPLE_DATA_DIR}")
        return

    logger.info(f"Found {len(zip_files)} sample ZIP(s): {[z.name for z in zip_files]}")

    for zip_path in zip_files:
        logger.info(f"--- Processing {zip_path.name} ---")
        try:
            run_pipeline(source="local", zip_path=str(zip_path), send_email=False)
        except Exception as e:

            logger.error(f"{zip_path.name} failed: {e}")

    logger.info("All sample ZIPs processed.")


if __name__ == "__main__":
    main()