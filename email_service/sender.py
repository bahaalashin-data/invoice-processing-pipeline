# Builds and sends the completion email with the report attached

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr
from html import escape
from pathlib import Path
from typing import Optional, Tuple

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

def _display_name(recipient: Optional[str]) -> str:
    name, _ = parseaddr(recipient or "")
    return name.strip()

def build_completion_email_body(
    invoices_processed: int,
    records_loaded: int,
    report_filename: str,
    rejected_count: int = 0,
    recipient: Optional[str] = None,
) -> Tuple[str, str]:
    """Builds the completion email. Returns (plain_text, html)."""
    name = _display_name(recipient)
    greeting = f"Dear {name}," if name else "Dear Team,"

    rejected_note = ""
    if rejected_count:
        rejected_note = (
            "Some records did not pass the data quality checks. The reason for "
            'each one is listed in the "Rejected Invoices" sheet of the attached report.'
        )

    # Plain text version (for email apps that don't show HTML)
    lines = [
        greeting,
        "",
        "Thank you for sending your invoices. Your batch has been processed.",
        "",
        "Summary",
        f"  - Invoice lines processed successfully: {invoices_processed}",
        f"  - Records loaded to the database: {records_loaded}",
        f"  - Records rejected: {rejected_count}",
        "",
        f"The full report is attached: {report_filename}",
    ]
    if rejected_note:
        lines += ["", rejected_note]
    lines += ["", "Best regards,", "Invoice Processing Pipeline", "(This is an automated message.)"]
    text_body = "\n".join(lines)

    # HTML version (what most people will see)
    rejected_color = "#B91C1C" if rejected_count else "#111827"
    note_html = ""
    if rejected_note:
        note_html = (
            '<p style="margin:16px 0 0 0;padding:12px 14px;background:#FFF7E6;'
            'border-left:4px solid #F59E0B;color:#92400E;font-size:14px;">'
            f"{escape(rejected_note)}</p>"
        )

    row_style = "padding:10px 14px;border-bottom:1px solid #E5E7EB;"
    html_body = f"""\
<html>
  <body style="margin:0;padding:0;background:#F3F4F6;font-family:Arial,Helvetica,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#F3F4F6;padding:24px 0;">
      <tr><td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border-radius:8px;overflow:hidden;">
          <tr>
            <td style="background:#1F4E78;padding:20px 28px;color:#FFFFFF;font-size:20px;font-weight:bold;">
              Invoice Processing Completed
            </td>
          </tr>
          <tr>
            <td style="padding:28px;color:#111827;font-size:15px;line-height:1.6;">
              <p style="margin:0 0 12px 0;">{escape(greeting)}</p>
              <p style="margin:0 0 20px 0;">Thank you for sending your invoices. Your batch has been processed.</p>
              <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #E5E7EB;">
                <tr>
                  <td style="{row_style}">Invoice lines processed successfully</td>
                  <td align="right" style="{row_style}font-weight:bold;">{invoices_processed}</td>
                </tr>
                <tr>
                  <td style="{row_style}">Records loaded to the database</td>
                  <td align="right" style="{row_style}font-weight:bold;">{records_loaded}</td>
                </tr>
                <tr>
                  <td style="padding:10px 14px;">Records rejected</td>
                  <td align="right" style="padding:10px 14px;font-weight:bold;color:{rejected_color};">{rejected_count}</td>
                </tr>
              </table>
              {note_html}
              <p style="margin:20px 0 0 0;">The full report is attached: <b>{escape(report_filename)}</b></p>
              <p style="margin:24px 0 0 0;">Best regards,<br>Invoice Processing Pipeline</p>
            </td>
          </tr>
          <tr>
            <td style="padding:14px 28px;background:#F9FAFB;color:#6B7280;font-size:12px;">
              This is an automated message.
            </td>
          </tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>
"""
    return text_body, html_body

def send_reply_email(
    to_address: str,
    attachment_path: Path,
    subject: str = "Invoice Processing Completed",
    body: str = "",
    html_body: str = "",
) -> None:
    """
    Sends an email with the Excel report attached via SMTP (STARTTLS).
    """
    attachment_path = Path(attachment_path)
    if not attachment_path.exists():
        raise FileNotFoundError(f"Report attachment not found: {attachment_path}")

    msg = MIMEMultipart("mixed")
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_address
    if REPORT_CC_EMAILS:
        msg["Cc"] = ", ".join(REPORT_CC_EMAILS)
    msg["Subject"] = subject

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(body, "plain", "utf-8"))
    if html_body:
        alternative.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alternative)

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
