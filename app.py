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
from lib.queries import get_overview_kpis, get_daily_checkups
from lib.charts import line_chart, stacked_bar_chart, COLORS
from lib.i18n import t, sidebar_language_toggle, inject_custom_css
from lib.filters import sidebar_filters, get_internal_user_ids

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ChecKin Analytics",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()

# Sidebar — language + filters (no date picker on overview)
sidebar_language_toggle()
sidebar_filters()

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

st.title(t("overview_title"))
st.caption(t("overview_subtitle"))

exclude_ids = tuple(get_internal_user_ids()) if st.session_state.get("exclude_internal") else ()
kpis = get_overview_kpis(exclude_user_ids=exclude_ids)

if not kpis:
    st.warning(t("no_kpi_data"))
    st.stop()

# KPI row 1 — Users & Revenue
c1, c2, c3, c4 = st.columns(4)
c1.metric(t("total_users"), f"{kpis.get('total_users', 0):,}",
          delta=f"+{kpis.get('new_users_this_week', 0)} this week",
          help=t("desc_total_users"))
c2.metric(t("premium"), kpis.get("premium_users", 0),
          help=t("desc_premium"))
c3.metric(t("mrr"), f"CA${kpis.get('mrr', 0):,.2f}",
          help=t("desc_mrr"))
c4.metric(t("conversion"), f"{kpis.get('trial_conversion_rate', 0)}%",
          help=t("desc_conversion"))

# KPI row 2 — Operations
c1, c2, c3, c4 = st.columns(4)
c1.metric(t("monthly_subs"), kpis.get("monthly_subscribers", 0),
          help=t("desc_monthly_subs"))
c2.metric(t("annual_subs"), kpis.get("annual_subscribers", 0),
          help=t("desc_annual_subs"))
today_total = kpis.get("total_checkups_today", 0)
today_resp = kpis.get("responded_today", 0)
c3.metric(t("checkups_today"), today_total,
          help=t("desc_checkups_today"))
resp_rate = round(today_resp / today_total * 100, 1) if today_total else 0
c4.metric(t("response_rate_today"), f"{resp_rate}%",
          help=t("desc_response_rate_today"))

# ---------------------------------------------------------------------------
# Recent check-up trend (last 14 days)
# ---------------------------------------------------------------------------

st.divider()
st.subheader(t("checkup_trend_title"))
st.caption(t("section_desc_checkup_trend"))

from datetime import date, timedelta

start_14 = date.today() - timedelta(days=14)
df_checkups = get_daily_checkups(start_14, date.today(), exclude_user_ids=exclude_ids)

if not df_checkups.empty:
    col_left, col_right = st.columns(2)
    with col_left:
        fig = stacked_bar_chart(
            df_checkups, x="day",
            y_cols=["responded", "sent", "failed", "pending"],
            title=t("daily_checkups_status"),
            colors=[COLORS["secondary"], COLORS["info"], COLORS["danger"], COLORS["muted"]],
        )
        st.plotly_chart(fig, width="stretch")

    with col_right:
        # Response rate line
        df_checkups["response_rate"] = (
            df_checkups["responded"]
            / df_checkups["total"].replace(0, 1)
            * 100
        ).round(1)
        fig = line_chart(
            df_checkups, x="day", y="response_rate",
            title=t("daily_response_rate"),
        )
        st.plotly_chart(fig, width="stretch")
else:
    st.info(t("no_checkup_data"))

# ---------------------------------------------------------------------------
# Navigation hint
# ---------------------------------------------------------------------------

st.divider()
st.markdown(t("nav_hint"))
