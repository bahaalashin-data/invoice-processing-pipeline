# Read-only queries used by the dashboard (pipeline monitoring, email log, business analytics)

from typing import List, Optional

from sql_engine.db import get_connection


# Section 1: Pipeline Monitoring

def get_pipeline_kpis() -> dict:
    """Total Runs / Running / Completed / Failed KPI cards."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_runs,
                COALESCE(SUM(CASE WHEN status = 'RUNNING'   THEN 1 ELSE 0 END), 0) AS running,
                COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END), 0) AS completed,
                COALESCE(SUM(CASE WHEN status = 'FAILED'    THEN 1 ELSE 0 END), 0) AS failed
            FROM pipeline_runs
            """
        ).fetchone()
    return dict(row) if row else {"total_runs": 0, "running": 0, "completed": 0, "failed": 0}


def get_pipeline_history(limit: int = 20) -> List[dict]:
    """Run ID / Start Time / Duration / Status table."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT run_id, start_time, duration_sec, status,
                   invoices_found, invoices_loaded
            FROM pipeline_runs
            ORDER BY run_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_activity_log(run_id: Optional[int] = None, limit: int = 50) -> List[dict]:
    """Recent activity feed, optionally scoped to a single run."""
    query = """
        SELECT run_id, timestamp, step_name, status, message
        FROM pipeline_activity_log
    """
    params: tuple = ()
    if run_id is not None:
        query += " WHERE run_id = ?"
        params = (run_id,)
    query += " ORDER BY log_id DESC LIMIT ?"
    params += (limit,)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]

# Section 2: Email Processing Monitoring
def get_email_kpis() -> dict:
    """
    Total Emails / Successful Emails / Rejected Emails KPI cards.
    """

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_emails,
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS success,
                SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected,
                SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed
            FROM email_processing_log
            """
        ).fetchone()

    return (
        dict(row)
        if row
        else {
            "total_emails": 0,
            "success": 0,
            "rejected": 0,
            "failed": 0,
        }
    )


def get_recent_email_logs(limit: int = 50) -> List[dict]:
    """
    Returns recent processed emails for the dashboard.
    """

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                email_id,
                message_id,
                sender,
                subject,
                status,
                reason,
                processed_at
            FROM email_processing_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(r) for r in rows]

# Section 3: Business Analytics
def get_business_kpis() -> dict:
    """Total Invoices / Total Revenue / Total Customers KPI cards."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(DISTINCT invoice_no)    AS total_invoices,
                COALESCE(SUM(total_amount), 0) AS total_revenue,
                COUNT(DISTINCT LOWER(customer_name)) AS total_customers
            FROM invoice_data
            """
        ).fetchone()
    return dict(row)


def get_revenue_by_customer() -> List[dict]:
    """Chart 1: Revenue By Customer."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT customer_name, SUM(total_amount) AS revenue
            FROM invoice_data
            GROUP BY customer_name
            ORDER BY revenue DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_revenue_by_category() -> List[dict]:
    """Chart 2: Revenue By Category."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT product_category, SUM(total_amount) AS revenue
            FROM invoice_data
            GROUP BY product_category
            ORDER BY revenue DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_invoice_trend() -> List[dict]:
    """Chart 3: Invoice Trend Over Time (invoices processed per day)."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT invoice_date, COUNT(DISTINCT invoice_no) AS invoice_count
            FROM invoice_data
            GROUP BY invoice_date
            ORDER BY invoice_date ASC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_invoice_records() -> List[dict]:

    with get_connection() as conn:

        rows = conn.execute(
            """
            SELECT
                invoice_no,
                invoice_date,
                created_date,
                customer_name,
                product_category,
                product_name,
                quantity,
                unit_price,
                total_amount,
                source_batch,
                country
            FROM invoice_data
            ORDER BY invoice_date
            """
        ).fetchall()

    return [dict(r) for r in rows]


def get_all_rejected_records() -> List[dict]:


    with get_connection() as conn:

        rows = conn.execute(
            """
            SELECT
                invoice_no,
                message_id,
                customer_name,
                product_name,
                source_file,
                rejection_reason,
                created_at,
                source_batch
            FROM rejected_records
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [dict(r) for r in rows]