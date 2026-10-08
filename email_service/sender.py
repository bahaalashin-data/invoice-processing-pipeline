# Builds and sends the completion email with the report attached

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from config import (
    SMTP_HOST,
    SMTP_PORT,
    EMAIL_ADDRESS,
    EMAIL_PASSWORD,
    REPORT_RECIPIENT_EMAIL,
    REPORT_CC_EMAILS,
)
from logger_config import get_logger

logger = get_logger(__name__)


def resolve_recipient(original_sender: Optional[str]) -> str:
    """
    Determines who should receive the completion email.

    Priority:

        1. REPORT_RECIPIENT_EMAIL
        2. Original email sender

    Raises:
        ValueError if no recipient can be determined.
    """
    if REPORT_RECIPIENT_EMAIL:
        return REPORT_RECIPIENT_EMAIL
    if original_sender:
        return original_sender
    raise ValueError(
        "No recipient available: set REPORT_RECIPIENT_EMAIL in .env, "
        "or run in Email Mode where the original sender is known. set this for testing purposes only."
    )


def build_completion_email_body(
    invoices_processed: int,
    records_loaded: int,
    report_filename: str,
    rejected_count: int = 0,
) -> str:
    """Builds the plain-text body described in the project spec."""
    lines = [
        f"{invoices_processed} invoices processed successfully.",
        f"Records loaded to database: {records_loaded}",
    ]
    if rejected_count:
        lines.append(f"Records rejected (failed data quality checks): {rejected_count}")
    lines.append(f"Attached: {report_filename}")
    return "\n".join(lines)


def send_reply_email(
    to_address: str,
    attachment_path: Path,
    subject: str = "Invoice Processing Completed",
    body: str = "",
) -> None:
    """
    Sends an email with the Excel report attached via SMTP (STARTTLS).
    """
    attachment_path = Path(attachment_path)
    if not attachment_path.exists():
        raise FileNotFoundError(f"Report attachment not found: {attachment_path}")

    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_address
    if REPORT_CC_EMAILS:
        msg["Cc"] = ", ".join(REPORT_CC_EMAILS)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with open(attachment_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=attachment_path.name)
    part["Content-Disposition"] = f'attachment; filename="{attachment_path.name}"'
    msg.attach(part)

    logger.info(f"Sending completion email to {to_address} (attachment: {attachment_path.name})")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        recipients = [to_address]

        if REPORT_CC_EMAILS:
            recipients.extend(REPORT_CC_EMAILS)

        server.sendmail(EMAIL_ADDRESS, recipients, msg.as_string())

        logger.info("Completion email sent successfully")
