# Business Analytics tab - KPIs, revenue by customer/category, invoice trend

import plotly.express as px
import streamlit as st

from sql_engine import (
    get_business_kpis,
    get_revenue_by_customer,
    get_revenue_by_category,
    get_invoice_trend,
)

CHART_TEMPLATE = "plotly_white"


def render_business() -> None:

    kpis = get_business_kpis()

    st.header("📈 Business Analytics")

    # ----------------------------------------
    # KPI Cards
    # ----------------------------------------

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Invoices",
        kpis.get("total_invoices") or 0,
    )

    col2.metric(
        "Total Revenue",
        f"${(kpis.get('total_revenue') or 0):,.2f}",
    )

    col3.metric(
        "Total Customers",
        kpis.get("total_customers") or 0,
    )

    if not kpis.get("total_invoices"):

        st.info(
            "No invoice data available."
        )

        return

    st.markdown("---")

    # ----------------------------------------
    # Top Charts
    # ----------------------------------------

    left, right = st.columns(2)

    with left:

        st.markdown("### Revenue By Customer")

        data = get_revenue_by_customer()

        fig = px.bar(
            data,
            x="customer_name",
            y="revenue",
            labels={
                "customer_name": "Customer",
                "revenue": "Revenue ($)"
            },
            template=CHART_TEMPLATE,
            color="customer_name",
        )

        fig.update_layout(
            showlegend=False,
            height=380,
        )

        st.plotly_chart(
            fig,
            width='stretch',
        )

    with right:

        st.markdown("### Revenue By Category")

        data = get_revenue_by_category()

        fig = px.bar(
            data,
            x="product_category",
            y="revenue",
            labels={
                "product_category": "Category",
                "revenue": "Revenue ($)"
            },
            template=CHART_TEMPLATE,
            color="product_category",
        )

        fig.update_layout(
            showlegend=False,
            height=380,
        )

        st.plotly_chart(
            fig,
            width='stretch',
        )

    st.markdown("---")

    # ----------------------------------------
    # Invoice Trend
    # ----------------------------------------

    st.markdown("### Invoice Trend")

    data = get_invoice_trend()

    fig = px.line(
        data,
        x="invoice_date",
        y="invoice_count",
        markers=True,
        labels={
            "invoice_date": "Date",
            "invoice_count": "Invoices Processed",
        },
        template=CHART_TEMPLATE,
    )

    fig.update_layout(
        height=300,
    )

    st.plotly_chart(
        fig,
        width='stretch',
    )