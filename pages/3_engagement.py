"""Engagement & Retention."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from lib.db import check_password
from lib.queries import (
    get_dau_wau_mau,
    get_dau_trend,
    get_retention_cohort,
    get_feature_adoption,
    get_weekly_response_rate,
    sidebar_date_filter,
)
from lib.charts import line_chart, bar_chart, heatmap_table, COLORS

check_password()

st.title("Engagement & Retention")

start, end = sidebar_date_filter(30)

# ---------------------------------------------------------------------------
# DAU / WAU / MAU cards
# ---------------------------------------------------------------------------

st.subheader("Active Users")

active = get_dau_wau_mau()
if active:
    c1, c2, c3 = st.columns(3)
    c1.metric("DAU", active.get("dau", 0))
    c2.metric("WAU", active.get("wau", 0))
    c3.metric("MAU", active.get("mau", 0))
else:
    st.info("No active user data (requires analytics_events).")

# ---------------------------------------------------------------------------
# DAU trend
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Daily Active Users Trend")

df_dau = get_dau_trend(start, end)
if not df_dau.empty:
    fig = line_chart(df_dau, x="day", y="active_users", title="DAU")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No DAU data for selected range.")

# ---------------------------------------------------------------------------
# Cohort retention
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Cohort Retention")

df_ret = get_retention_cohort()
if not df_ret.empty:
    # Show as styled table
    display_df = df_ret.copy()
    display_df.columns = ["Cohort Week", "Size", "D1 %", "D7 %", "D14 %", "D30 %"]
    fig = heatmap_table(display_df, title="Weekly Cohort Retention")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Raw data"):
        st.dataframe(display_df, use_container_width=True)
        st.download_button(
            "Download CSV", display_df.to_csv(index=False),
            "retention_cohort.csv", "text/csv",
        )
else:
    st.info("No retention data (requires analytics_events over time).")

# ---------------------------------------------------------------------------
# Feature adoption
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Feature Adoption (Premium Users)")

df_feat = get_feature_adoption()
if not df_feat.empty:
    fig = bar_chart(
        df_feat, x="feature", y="adoption_rate",
        title="Feature Adoption Rate (%)",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No feature adoption data.")

# ---------------------------------------------------------------------------
# Weekly response rate
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Weekly Response Rate Trend")

df_resp = get_weekly_response_rate(start, end)
if not df_resp.empty:
    fig = line_chart(df_resp, x="week_start", y="response_rate",
                     title="Response Rate (%) by Week")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No response data for selected range.")
