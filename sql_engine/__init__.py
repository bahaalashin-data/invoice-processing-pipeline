# Database layer - table setup, inserts, and the queries the dashboard uses

from .db import (
    get_connection,
    init_database,
    insert_invoices,
    insert_rejected_records,
    insert_email_log,
    start_pipeline_run,
    complete_pipeline_run,
    fail_pipeline_run,
    log_activity,
)

from .analytics import (
    get_pipeline_kpis,
    get_pipeline_history,
    get_activity_log,
    get_email_kpis,
    get_recent_email_logs,
    get_business_kpis,
    get_revenue_by_customer,
    get_revenue_by_category,
    get_invoice_trend,
    get_all_invoice_records,
    get_all_rejected_records,
)

__all__ = [
    "init_database", "insert_invoices", "insert_email_log", "get_connection",
    "start_pipeline_run", "complete_pipeline_run", "fail_pipeline_run", "log_activity",
    "get_pipeline_kpis", "get_pipeline_history", "get_activity_log",
    "get_email_kpis", "get_recent_email_logs",
    "get_business_kpis", "get_revenue_by_customer", "get_revenue_by_category", "get_invoice_trend",
    "get_all_invoice_records", "get_all_rejected_records", "insert_rejected_records",
]
