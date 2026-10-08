# Write functions - creates tables and inserts invoices/emails/pipeline runs

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config import DATABASE_PATH, SCHEMA_PATH
from logger_config import get_logger

logger = get_logger(__name__)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database() -> None:
    """Creates every table in database/schema.sql if it doesn't exist yet."""
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    schema_sql = Path(SCHEMA_PATH).read_text(encoding="utf-8")

    with get_connection() as conn:
        conn.executescript(schema_sql)

    logger.info(f"Database ready at {DATABASE_PATH}")


# invoice_data

def insert_invoices(records: List[dict]) -> int:
    """
    Inserts valid transport records into invoice_data.
    Uses INSERT OR IGNORE so a duplicate that slipped past the in-batch
    dedup (e.g. the same invoice arriving in a later email) is skipped
    instead of crashing the whole run.

    Returns the number of rows actually inserted (duplicates don't count).
    """
    if not records:
        return 0

    rows = [
        (
            r["invoice_no"],r["message_id"], r["invoice_date"], r["customer_name"],
            r["product_category"], r["product_name"], r["quantity"],
            r["unit_price"], r["total_amount"], r["country"], r["created_date"],
            r.get("record_status", "VALID"),r.get("rejection_reason"), r.get("source_batch"),
        )
        for r in records
    ]

    with get_connection() as conn:
        cursor = conn.executemany(
            """
            INSERT OR IGNORE INTO invoice_data (
                invoice_no, message_id, invoice_date, customer_name, product_category,
                product_name, quantity, unit_price, total_amount, country, created_date, record_status, rejection_reason, source_batch
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        inserted = cursor.rowcount if cursor.rowcount != -1 else len(rows)

    skipped = len(rows) - inserted
    logger.info(f"Inserted {inserted} invoice record(s) into invoice_data ({skipped} duplicate skipped)")
    return inserted


# email_processing_log

def insert_email_log(
    email_id: str,
    message_id: str,
    sender: str,
    subject: str,
    status: str,
    reason: Optional[str] = None,
) -> None:
    """
    Stores email processing results.

    status:
        SUCCESS
        REJECTED
        FAILED
    """

    processed_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO email_processing_log (
                email_id,
                message_id,
                sender,
                subject,
                status,
                reason,
                processed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email_id,
                message_id,
                sender,
                subject,
                status,
                reason,
                processed_at,
            ),
        )

    logger.info(
        f"Email logged -> "
        f"message_id={message_id} | "
        f"status={status}"
    )

# pipeline_runs / pipeline_activity_log  (Pipeline Monitoring dashboard)

def start_pipeline_run(email_subject: Optional[str] = None, zip_filename: Optional[str] = None) -> int:
    """Creates a RUNNING row in pipeline_runs and returns its run_id."""
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO pipeline_runs (start_time, status, email_subject, zip_filename)
            VALUES (?, 'RUNNING', ?, ?)
            """,
            (now, email_subject, zip_filename),
        )
        run_id = cursor.lastrowid

    log_activity(run_id, "Pipeline Started", "SUCCESS")
    return run_id


def complete_pipeline_run(run_id: int, invoices_found: int, invoices_loaded: int) -> None:
    _finish_pipeline_run(run_id, status="COMPLETED", invoices_found=invoices_found, invoices_loaded=invoices_loaded)


def fail_pipeline_run(run_id: int, error_message: str) -> None:
    _finish_pipeline_run(run_id, status="FAILED", error_message=error_message)


def _finish_pipeline_run(
    run_id: int,
    status: str,
    invoices_found: int = 0,
    invoices_loaded: int = 0,
    error_message: Optional[str] = None,
) -> None:
    end_time = datetime.now()
    with get_connection() as conn:
        row = conn.execute("SELECT start_time FROM pipeline_runs WHERE run_id = ?", (run_id,)).fetchone()
        if not row:raise ValueError(f"Run not found: {run_id}")
        duration_sec = None
        if row and row["start_time"]:
            start_time = datetime.fromisoformat(row["start_time"])
            duration_sec = (end_time - start_time).total_seconds()

        conn.execute(
            """
            UPDATE pipeline_runs
               SET end_time = ?, duration_sec = ?, status = ?,
                   invoices_found = ?, invoices_loaded = ?, error_message = ?
             WHERE run_id = ?
            """,
            (
                end_time.isoformat(timespec="seconds"), duration_sec, status,
                invoices_found, invoices_loaded, error_message, run_id,
            ),
        )

    log_activity(run_id, f"Pipeline {status.title()}", "SUCCESS" if status == "COMPLETED" else "FAILED", error_message)
    logger.info(f"Run #{run_id} -> {status} ({duration_sec:.1f}s)" if duration_sec else f"Run #{run_id} -> {status}")


def log_activity(run_id: int, step_name: str, status: str = "SUCCESS", message: Optional[str] = None) -> None:
    """Records one step in the Activity Log panel (e.g. 'ZIP Downloaded')."""
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO pipeline_activity_log (run_id, timestamp, step_name, status, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, now, step_name, status, message),
        )
    logger.info(f"[Run #{run_id}] {step_name} -> {status}" + (f" ({message})" if message else ""))

def insert_rejected_records(records: list[dict]) -> int:

    if not records:
        return 0

    rows = [
        (
            r.get("invoice_no"),
            r.get("message_id"),
            r.get("customer_name"),
            r.get("product_name"),
            r.get("source_file"),
            r.get("rejection_reason") or r.get("reason"),
            datetime.now().isoformat(),
            r.get("source_batch"),
        )
        for r in records
    ]

    with get_connection() as conn:

        cursor = conn.executemany(
            """
            INSERT OR IGNORE INTO rejected_records (
                invoice_no, message_id, customer_name, product_name,
                source_file, rejection_reason, created_at, source_batch
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        return cursor.rowcount