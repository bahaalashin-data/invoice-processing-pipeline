# Entry point - runs the pipeline in Email Mode (processes every unread
# matching email) or Local/Test Mode (processes one ZIP from disk)

import argparse
import time
from pathlib import Path

from logger_config import get_logger
from config import POLL_INTERVAL_SECONDS

from email_service import (
    fetch_invoice_emails,
    extract_pdfs_from_zip,
    send_reply_email,
    resolve_recipient,
    build_completion_email_body,
    NoInvoiceEmailFound,
)
from pdf_engine import extract_all_invoices
from data_transformation import transform_invoices
from report_engine import generate_excel_report

from sql_engine import (
    init_database,
    insert_invoices,
    insert_rejected_records,
    insert_email_log,
    start_pipeline_run,
    complete_pipeline_run,
    fail_pipeline_run,
    log_activity,
    get_all_invoice_records,
    get_all_rejected_records,
)

logger = get_logger(__name__)


def _process_one_batch(
    zip_path: Path,
    source: str,
    email_subject: str = None,
    original_sender: str = None,
    message_id: str = None,
    send_email: bool = False,
    to_override: str = None,
) -> None:
    """
    Runs the full pipeline (steps 2-8) for ONE ZIP file - whether that
    ZIP came from a single email or from --source local. Called once
    per email in Email Mode (same steps every time, no special-casing
    by sender), or once for the whole run in Local/Test Mode.
    """
    zip_path = Path(zip_path)
    run_id = start_pipeline_run(email_subject=email_subject, zip_filename=zip_path.name)
    log_activity(run_id, "Email Received" if source == "email" else "Local ZIP Provided", "SUCCESS",
                 original_sender or str(zip_path))

    try:
        # Step 2: extract PDFs
        pdf_paths = extract_pdfs_from_zip(zip_path)
        log_activity(run_id, f"{len(pdf_paths)} PDFs Extracted", "SUCCESS")

        # Step 3: read + extract invoice fields (one or more line items per PDF)
        extracted, parse_failed = extract_all_invoices(pdf_paths)

        # Link each invoice back to the email it came from (None in Local/Test Mode)
        for invoice in extracted:
            invoice["message_id"] = message_id

        # Step 4: clean, validate, and separate valid vs rejected
        valid, rejected = transform_invoices(extracted, pre_failed=parse_failed)
        log_activity(run_id, "Data Transformed & Validated", "SUCCESS",
                     f"{len(valid)} valid, {len(rejected)} rejected")

        report_year = (valid[0]["invoice_date"][:4] if valid else "Unknown")
        source_batch = f"{zip_path.stem}_{report_year}"

        # Step 5: load to SQLite
        for record in valid:
            record["source_batch"] = source_batch
        for record in rejected:
            record["source_batch"] = source_batch

        inserted = insert_invoices(valid)
        rejected_inserted = insert_rejected_records(rejected)
        log_activity(run_id, f"{inserted} Valid + {rejected_inserted} Rejected Loaded", "SUCCESS")

        # Step 6: per-batch report + refreshed master report
        report_filename = f"{zip_path.stem}_{report_year}_Report.xlsx"
        report_path = generate_excel_report(
            valid, rejected,
            output_path=Path("reports") / report_filename,
        )

        all_records = get_all_invoice_records()
        all_rejected = get_all_rejected_records()
        generate_excel_report(
            valid_records=all_records,
            rejected_records=all_rejected,
            output_path=Path("reports") / "Master_Invoice_Report.xlsx",
        )

        log_activity(run_id, "Excel Generated", "SUCCESS", report_path.name)

        complete_pipeline_run(run_id, invoices_found=len(pdf_paths), invoices_loaded=inserted)

        # Step 7: reply email
        should_send = (source == "email") or send_email
        if should_send:
            recipient = to_override or resolve_recipient(original_sender)

            body, html_body = build_completion_email_body(
                invoices_processed=len(valid),
                records_loaded=inserted,
                report_filename=report_path.name,
                rejected_count=len(rejected),
                recipient=recipient,
            )
            send_reply_email(recipient, report_path, body=body, html_body=html_body)
            log_activity(run_id, "Reply Sent", "SUCCESS", f"to {recipient}")
        else:
            log_activity(run_id, "Reply Skipped", "SUCCESS", "Local/Test mode (use --send-email to enable)")

        logger.info(f"Run #{run_id} finished: {inserted} loaded, {len(rejected)} rejected, report -> {report_path}")

    except Exception as e:
        logger.exception(f"Run #{run_id} failed")
        fail_pipeline_run(run_id, str(e))
        log_activity(run_id, "Pipeline Failed", "FAILED", str(e))
        raise


def run_pipeline(source: str, zip_path: str = None, send_email: bool = False, to_override: str = None) -> None:
    init_database()

    if source == "local":
        if not zip_path:
            raise ValueError("--zip is required when --source local")
        _process_one_batch(Path(zip_path), source="local", send_email=send_email, to_override=to_override)
        return

    # --- source == "email": process EVERY unread matching email found ---
    try:
        emails = fetch_invoice_emails()
    except NoInvoiceEmailFound as e:
        logger.info(f"Nothing to process: {e}")
        return

    logger.info(f"Found {len(emails)} email(s) to process this run")

    for email_meta in emails:
        # Log every email's outcome (SUCCESS or REJECTED), whether or
        # not it actually gets processed below.
        insert_email_log(
            email_id=email_meta.get("email_id"),
            message_id=email_meta.get("message_id"),
            sender=email_meta.get("from"),
            subject=email_meta.get("subject"),
            status=email_meta.get("status", "SUCCESS"),
            reason=email_meta.get("reason"),
        )

        if email_meta.get("status") != "SUCCESS" or not email_meta.get("zip_path"):
            logger.warning(f"Skipping email from {email_meta.get('from')}: {email_meta.get('reason')}")
            continue

        try:
            _process_one_batch(
                zip_path=email_meta["zip_path"],
                source="email",
                email_subject=email_meta.get("subject"),
                original_sender=email_meta.get("from"),
                message_id=email_meta.get("message_id"),
                send_email=send_email,
                to_override=to_override,
            )
        except Exception:
            # Already logged inside _process_one_batch; keep processing
            # the REST of this batch's emails instead of aborting all
            # of them because one failed.
            continue


def main():
    parser = argparse.ArgumentParser(description="Automated Invoice Processing Pipeline")
    parser.add_argument("--source", choices=["email", "local"], default="email",
                         help="Where the ZIP(s) come from. 'email' connects to the real inbox "
                              "and processes every unread matching email; "
                              "'local' reads a single ZIP already on disk.")
    parser.add_argument("--zip", dest="zip_path", default=None,
                         help="Path to a ZIP file. Required when --source local.")
    parser.add_argument("--send-email", action="store_true",
                         help="In local mode, also send the completion email "
                              "(requires REPORT_RECIPIENT_EMAIL in .env, or --to).")
    parser.add_argument("--to", dest="to_override", default=None,
                         help="Override the recipient email address for this run.")
    parser.add_argument("--watch", action="store_true",
                         help="Keep polling the inbox every POLL_INTERVAL_SECONDS "
                              "instead of running once. Only valid with --source email.")
    args = parser.parse_args()

    if args.watch and args.source != "email":
        parser.error("--watch is only valid with --source email")

    if not args.watch:
        run_pipeline(args.source, args.zip_path, args.send_email, args.to_override)
        return

    logger.info(f"Watching inbox every {POLL_INTERVAL_SECONDS}s ... (Ctrl+C to stop)")
    while True:
        try:
            run_pipeline("email")
        except Exception as exc:
            logger.exception(f"Watcher cycle failed: {exc}")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
