# Connects to the inbox and fetches invoice emails

import email
import imaplib
import time
from datetime import datetime
from email.message import Message
from pathlib import Path
from typing import Optional
from email.utils import parseaddr

from config import (
    IMAP_HOST,
    IMAP_PORT,
    EMAIL_ADDRESS,
    EMAIL_PASSWORD,
    IMAP_FOLDER,
    IMAP_SUBJECT_FILTER,
    ATTACHMENTS_DIR,
    EMAIL_RETRY_COUNT,
    MAX_ATTACHMENT_SIZE_MB,
    ALLOWED_ATTACHMENT_EXTENSIONS,
    ALLOWED_SENDERS,
)

from logger_config import get_logger

logger = get_logger(__name__)

class NoInvoiceEmailFound(Exception):
    """Raised when no matching email with a ZIP attachment is found."""


def connect_to_inbox() -> imaplib.IMAP4_SSL:
    """Open an authenticated IMAP connection with retry support."""

    for attempt in range(1, EMAIL_RETRY_COUNT + 1):
        try:
            logger.info(
                f"Connecting to inbox {EMAIL_ADDRESS} "
                f"@ {IMAP_HOST}:{IMAP_PORT} "
                f"(Attempt {attempt}/{EMAIL_RETRY_COUNT})"
            )

            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

            status, _ = mail.select(IMAP_FOLDER)

            if status != "OK":
                raise RuntimeError(
                    f"Cannot open mailbox folder: {IMAP_FOLDER}"
                )            

            return mail

        except Exception as exc:
            logger.error(
                f"Connection failed (Attempt {attempt}/{EMAIL_RETRY_COUNT}) "
                f"- {exc}"
            )

            if attempt == EMAIL_RETRY_COUNT:
                raise

            time.sleep(5)

def _find_matching_email_ids(mail: imaplib.IMAP4_SSL) -> list[bytes]:
    """Return all unread matching email IDs."""

    status, data = mail.search(
        None,"UNSEEN",f'SUBJECT "{IMAP_SUBJECT_FILTER}"'
    )
    if status != "OK":
        logger.error("IMAP search failed")
        return []

    email_ids = data[0].split()

    logger.info(f"Found {len(email_ids)} matching unread emails")

    return email_ids


def _extract_zip_attachment(msg: Message) -> Optional[tuple]:
    """Return first valid ZIP attachment."""

    for part in msg.walk():

        if part.get_content_maintype() == "multipart":
            continue

        filename = part.get_filename()

        if not filename:
            continue

        if filename.lower().endswith(
            tuple(ALLOWED_ATTACHMENT_EXTENSIONS)
        ):
            return filename, part.get_payload(decode=True)

    return None

def _build_saved_filename(sender: str, original_filename: str) -> str:
    """
    Example:
        Bahaa_Invoices_July_2026.zip
    """

    sender_name = sender.split("<")[0].strip()

    sender_name = "".join(
        c if c.isalnum() or c in ("_", "-") else "_"
        for c in sender_name
    )

    return f"{sender_name}_{original_filename}"

def fetch_invoice_emails() -> list[dict]:
    """
    Process all unread matching invoice emails.

    Returns:
        [
            {
                "email_id": "...",
                "message_id": "...",
                "subject": "...",
                "from": "...",
                "status": "SUCCESS|REJECTED",
                "reason": "...",
                "zip_path": Path | None,
            }
        ]
    """

    processed_emails = []

    mail = connect_to_inbox()

    try:

        email_ids = _find_matching_email_ids(mail)

        if not email_ids:
            raise NoInvoiceEmailFound(
                f"No unread email with subject "
                f"containing '{IMAP_SUBJECT_FILTER}' was found."
            )

        for email_id in email_ids:

            try:

                status, msg_data = mail.fetch(email_id, "(RFC822)")

                if status != "OK":

                    logger.error(
                        f"Failed to fetch email {email_id.decode()}"
                    )

                    processed_emails.append(
                        {
                            "email_id": email_id.decode(),
                            "message_id": "",
                            "subject": "",
                            "from": "",
                            "status": "REJECTED",
                            "reason": "Failed to fetch email",
                            "zip_path": None,
                        }
                    )

                    continue

                raw_email = msg_data[0][1]

                msg = email.message_from_bytes(raw_email)

                subject = msg.get("Subject", "")
                sender = msg.get("From", "")
                message_id = (
                    msg.get("Message-ID")
                    or email_id.decode()
                )                
                sender_name, sender_email = parseaddr(sender)
                sender_email = sender_email.lower()

                if ALLOWED_SENDERS and sender_email not in ALLOWED_SENDERS:

                    logger.warning(
                        f"Unauthorized sender: {sender_email}"
                    )

                    processed_emails.append(
                        {
                            "email_id": email_id.decode(),
                            "message_id": message_id,
                            "subject": subject,
                            "from": sender,
                            "status": "REJECTED",
                            "reason": "Unauthorized sender",
                            "zip_path": None,
                        }
                    )

                    mail.store(
                        email_id,
                        "+FLAGS",
                        "\\Seen"
                    )

                    continue                

                logger.info(
                    f"Matched email -> "
                    f"From: {sender} | Subject: {subject}"
                )

                attachment = _extract_zip_attachment(msg)

                if attachment is None:

                    logger.warning(
                        f"Email {email_id.decode()} "
                        f"has no valid attachment."
                    )

                    processed_emails.append(
                        {
                            "email_id": email_id.decode(),
                            "message_id": message_id,
                            "subject": subject,
                            "from": sender,
                            "status": "REJECTED",
                            "reason": "No valid attachment found",
                            "zip_path": None,
                        }
                    )

                    mail.store(
                        email_id,
                        "+FLAGS",
                        "\\Seen"
                    )

                    continue

                filename, raw_bytes = attachment

                size_mb = len(raw_bytes) / (1024 * 1024)

                if size_mb > MAX_ATTACHMENT_SIZE_MB:

                    logger.error(
                        f"Attachment exceeds allowed size "
                        f"({size_mb:.2f} MB)"
                    )

                    processed_emails.append(
                        {
                            "email_id": email_id.decode(),
                            "message_id": message_id,
                            "subject": subject,
                            "from": sender,
                            "status": "REJECTED",
                            "reason": (
                                f"Attachment exceeds "
                                f"{MAX_ATTACHMENT_SIZE_MB} MB"
                            ),
                            "zip_path": None,
                        }
                    )

                    mail.store(
                        email_id,
                        "+FLAGS",
                        "\\Seen"
                    )

                    continue

                timestamp = datetime.now().strftime(
                    "%Y%m%d_%H%M%S"
                )

                saved_filename = (
                    f"{timestamp}_"
                    f"{_build_saved_filename(sender, filename)}"
                )

                zip_path = Path(ATTACHMENTS_DIR) / saved_filename

                zip_path.write_bytes(raw_bytes)

                logger.info(
                    f"Attachment saved -> {zip_path}"
                )

                mail.store(
                    email_id,
                    "+FLAGS",
                    "\\Seen"
                )

                processed_emails.append(
                    {
                        "email_id": email_id.decode(),
                        "message_id": message_id,
                        "subject": subject,
                        "from": sender,
                        "status": "SUCCESS",
                        "reason": "",
                        "zip_path": zip_path,
                    }
                )

            except Exception as exc:

                logger.exception(
                    f"Failed processing email "
                    f"{email_id.decode()} - {exc}"
                )

                processed_emails.append(
                    {
                        "email_id": email_id.decode(),
                        "message_id": "",
                        "subject": "",
                        "from": "",
                        "status": "REJECTED",
                        "reason": str(exc),
                        "zip_path": None,
                    }
                )

        return processed_emails

    finally:
        mail.logout()


def fetch_invoice_email():
    """
    Returns the first matching invoice email.

    Used by the current single-email pipeline for
    backward compatibility.
    """

    emails = fetch_invoice_emails()

    if not emails:
        raise NoInvoiceEmailFound(
            "No matching emails found"
        )

    return emails[0]