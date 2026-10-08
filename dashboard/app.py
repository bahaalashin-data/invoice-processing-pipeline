# Dashboard entry point - two tabs: Pipeline Monitoring and Business Analytics
# Run with: streamlit run dashboard/app.py

import sys
from pathlib import Path

# Allow dashboard to access project packages(config.py, sql_engine).
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from monitoring_section import render_monitoring
from business_section import render_business

st.set_page_config(
    page_title="Invoice Pipeline Dashboard",
    layout="wide",
)

st_autorefresh(
    interval=60000,  # 60 seconds
    key="dashboard_refresh"
)

st.markdown(
    """
    <style>

    .stApp {
        background-color: #F5F6F8;
    }

    /* TIGHTER OVERALL SPACING - less empty space at the top and
       between major sections */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1300px;
    }

    hr {
        margin: 0.6rem 0 !important;
    }

    /* ALL TEXT */

    body,
    p,
    span,
    label,
    div {
        color: #222222 !important;
    }

    /* KPI CARDS */

    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #DFE3E8;
        border-radius: 6px;
        padding: 10px;
    }

    div[data-testid="stMetricLabel"] * {
        color: #444444 !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] * {
        color: #000000 !important;
        font-size: 28px !important;
        font-weight: 700 !important;
    }

    /* TABS */

    button[data-baseweb="tab"] {
        color: #222222 !important;
        font-weight: 600 !important;
    }

    button[data-baseweb="tab"] * {
        color: #222222 !important;
    }

    /* HEADERS */

    h1,h2,h3,h4,h5,h6 {
        color: #222222 !important;
    }

    /* DATA TABLES */

    [data-testid="stDataFrame"] {
        background: white;
        border: 1px solid #DFE3E8;
        border-radius: 6px;
    }

    /* ALERTS */

    [data-testid="stAlert"] {
        color: #222222 !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Invoice Dashboard")

tab_monitoring, tab_business = st.tabs(["📊 Pipeline Monitoring", "📈 Business Analytics"])

with tab_monitoring:
    render_monitoring()

with tab_business:
    render_business()
