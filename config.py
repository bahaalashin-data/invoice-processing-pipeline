# Central configuration - reads settings from .env

import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Project root
BASE_DIR = Path(__file__).resolve().parent

# Folders
ATTACHMENTS_DIR = BASE_DIR / os.getenv("ATTACHMENTS_DIR", "attachments")
EXTRACTED_PDFS_DIR = BASE_DIR / os.getenv("EXTRACTED_PDFS_DIR", "extracted_pdfs")
REPORTS_DIR = BASE_DIR / os.getenv("REPORTS_DIR", "reports")
LOGS_DIR = BASE_DIR / os.getenv("LOGS_DIR", "logs")
DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "database/invoices.db")
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"

for folder in (ATTACHMENTS_DIR, EXTRACTED_PDFS_DIR, REPORTS_DIR, LOGS_DIR):
    folder.mkdir(parents=True, exist_ok=True)


# Email (IMAP - reading)
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX")
IMAP_SUBJECT_FILTER = os.getenv("IMAP_SUBJECT_FILTER", "Invoices")

# Email (SMTP - sending the reply)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# Only allow emails from these senders. Leave empty to allow all senders.
ALLOWED_SENDERS = [
    email.strip().lower()
    for email in os.getenv("ALLOWED_SENDERS", "").split(",")
    if email.strip()
]

# email always goes here
# Leave empty to send the report to the original sender.
REPORT_RECIPIENT_EMAIL = os.getenv("REPORT_RECIPIENT_EMAIL", "").strip()
# to the CC Recipients (CC:).
REPORT_CC_EMAILS = [email.strip().lower() for email in os.getenv("REPORT_CC_EMAILS", "").split(",") if email.strip()]

# Data quality thresholds (data_transformation)
# quantity * unit_price vs total_amount is allowed to differ by this fraction (rounding in the source invoice) before it's flagged and sent to the rejected log instead of the database.
AMOUNT_MISMATCH_TOLERANCE_PCT = float(os.getenv("AMOUNT_MISMATCH_TOLERANCE_PCT", 0.01))

# Behavior (Refresh interval for email listener)
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", 60))

# Retry when email failures.
EMAIL_RETRY_COUNT = int(os.getenv("EMAIL_RETRY_COUNT", 3))

# Allowed attachement type.
ALLOWED_ATTACHMENT_EXTENSIONS = [ext.strip().lower() for ext in os.getenv("ALLOWED_ATTACHMENT_EXTENSIONS",".zip").split(",") if ext.strip()]

# Max size of .zip attached.
MAX_ATTACHMENT_SIZE_MB = int(os.getenv("MAX_ATTACHMENT_SIZE_MB", 50))

# All invoices must have the same month.
REQUIRE_SAME_INVOICE_MONTH = (
    os.getenv("REQUIRE_SAME_INVOICE_MONTH","true").lower() == "true")


# Invoice fields
REQUIRED_INVOICE_FIELDS = [
    "invoice_no",
    "invoice_date",
    "customer_name",
    "product_category",
    "product_name",
    "quantity",
    "unit_price",
    "total_amount",
    "country",
]