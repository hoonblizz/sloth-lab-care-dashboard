"""
Sloth Care (ChecKin) — Marketing Analytics Dashboard

Usage (local):
    pip install -r requirements.txt
    cp .env.example .env   # fill in real values
    streamlit run analytics_dashboard.py

Deployment:
    Streamlit Community Cloud — connect GitHub repo,
    set main file path to scripts/analytics/analytics_dashboard.py,
    configure secrets in the Streamlit Cloud dashboard.
"""

import sys
from pathlib import Path

# Ensure lib/ is importable from the main script and pages
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
from lib.db import check_password
from lib.queries import get_overview_kpis, get_daily_checkups, sidebar_date_filter
from lib.charts import line_chart, stacked_bar_chart, COLORS

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ChecKin Analytics",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded",
)

check_password()

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

st.title("ChecKin — Marketing Analytics")
st.caption("Overview Dashboard")

kpis = get_overview_kpis()

if not kpis:
    st.warning("No data available. Ensure analytics SQL functions are deployed.")
    st.stop()

# KPI row 1 — Users & Revenue
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Users", f"{kpis.get('total_users', 0):,}",
          delta=f"+{kpis.get('new_users_this_week', 0)} this week")
c2.metric("Premium", kpis.get("premium_users", 0))
c3.metric("MRR", f"${kpis.get('mrr', 0):,.2f}")
c4.metric("Conversion", f"{kpis.get('trial_conversion_rate', 0)}%")

# KPI row 2 — Operations
c1, c2, c3, c4 = st.columns(4)
c1.metric("Monthly Subs", kpis.get("monthly_subscribers", 0))
c2.metric("Annual Subs", kpis.get("annual_subscribers", 0))
today_total = kpis.get("total_checkups_today", 0)
today_resp = kpis.get("responded_today", 0)
c3.metric("Check-ups Today", today_total)
resp_rate = round(today_resp / today_total * 100, 1) if today_total else 0
c4.metric("Response Rate Today", f"{resp_rate}%")

# ---------------------------------------------------------------------------
# Recent check-up trend (last 14 days)
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Check-up Trend (Last 14 Days)")

from datetime import date, timedelta

start_14 = date.today() - timedelta(days=14)
df_checkups = get_daily_checkups(start_14, date.today())

if not df_checkups.empty:
    col_left, col_right = st.columns(2)
    with col_left:
        fig = stacked_bar_chart(
            df_checkups, x="day",
            y_cols=["responded", "sent", "failed", "pending"],
            title="Daily Check-ups by Status",
            colors=[COLORS["secondary"], COLORS["info"], COLORS["danger"], COLORS["muted"]],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # Response rate line
        df_checkups["response_rate"] = (
            df_checkups["responded"]
            / df_checkups["total"].replace(0, 1)
            * 100
        ).round(1)
        fig = line_chart(
            df_checkups, x="day", y="response_rate",
            title="Daily Response Rate (%)",
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No check-up data available yet.")

# ---------------------------------------------------------------------------
# Navigation hint
# ---------------------------------------------------------------------------

st.divider()
st.markdown(
    "Use the **sidebar** to navigate to detailed pages: "
    "Acquisition, Subscription, Engagement, Operations, Funnel."
)
