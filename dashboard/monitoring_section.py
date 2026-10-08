# Pipeline Monitoring tab - run history, email processing, activity log

import streamlit as st

from sql_engine import (
    get_pipeline_kpis,
    get_pipeline_history,
    get_activity_log,
    get_email_kpis,
    get_recent_email_logs,
)

STATUS_ICON = {
    "RUNNING": "🟢",
    "COMPLETED": "✅",
    "FAILED": "❌",
}


def render_monitoring() -> None:

    pipeline_kpis = get_pipeline_kpis()
    email_kpis = get_email_kpis()

    st.subheader("📊 General Monitoring")

    # -----------------------------------------
    # Pipeline KPIs
    # -----------------------------------------

    st.caption("Pipeline Health")

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])

    c1.metric("Total Runs", pipeline_kpis.get("total_runs") or 0)
    c2.metric("Running", pipeline_kpis.get("running") or 0)
    c3.metric("Completed", pipeline_kpis.get("completed") or 0)
    c4.metric("Failed", pipeline_kpis.get("failed") or 0)

    st.markdown("---")

    # -----------------------------------------
    # Email KPIs
    # -----------------------------------------

    st.caption("Email Processing")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Emails", email_kpis.get("total_emails") or 0)
    c2.metric("Success", email_kpis.get("success") or 0)
    c3.metric("Rejected", email_kpis.get("rejected") or 0)
    c4.metric("Failed", email_kpis.get("failed") or 0)

    st.markdown("---")

    # -----------------------------------------
    # Main Layout
    # -----------------------------------------

    left, right = st.columns([5, 2])

    # -----------------------------------------
    # LEFT SIDE
    # -----------------------------------------

    with left:

        st.markdown("#### Pipeline History")

        history = get_pipeline_history(limit=20)

        if not history:

            st.info(
                "No pipeline runs yet. "
                "Run python main.py to process your first batch."
            )

        else:

            table_rows = [
                {
                    "Run ID": r["run_id"],
                    "Status": (
                        f"{STATUS_ICON.get(r['status'], '')} "
                        f"{r['status']}"
                    ),
                    "Start Time": r["start_time"],
                    "Duration (s)": (
                        f"{r['duration_sec']:.1f}"
                        if r["duration_sec"]
                        else "-"
                    ),
                    "Invoices Loaded": (
                        f"{r['invoices_loaded']}/"
                        f"{r['invoices_found']}"
                    ),
                }
                for r in history
            ]

            st.dataframe(
                table_rows,
                hide_index=True,
                width=7500,
                height=270,
            )

        st.markdown("#### Recent Email Processing")

        email_history = get_recent_email_logs(limit=20)

        if not email_history:

            st.info(
                "No email processing records available yet."
            )

        else:

            st.dataframe(
                email_history,
                hide_index=True,
                width=750,
                height=220,
            )

    # -----------------------------------------
    # RIGHT SIDE
    # -----------------------------------------

    with right:

        st.markdown("#### Recent Activity")

        activity = get_activity_log(limit=20)

        with st.container(height=560, border=True):

            if not activity:

                st.info("No activity yet.")

            else:

                for entry in activity:

                    icon = (
                        "✅"
                        if entry["status"] == "SUCCESS"
                        else (
                            "❌"
                            if entry["status"] == "FAILED"
                            else "•"
                        )
                    )

                    st.markdown(
                        f"""
                    **{icon} {entry['step_name']}**

                    <small>{entry['timestamp']}</small>

                    <small>{entry['message'] if entry['message'] else ''}</small>
                    """,
                        unsafe_allow_html=True
                    )