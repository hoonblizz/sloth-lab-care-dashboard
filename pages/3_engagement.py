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
from lib.i18n import t, inject_custom_css
from lib.filters import filter_df_by_date, get_internal_user_ids

check_password()
inject_custom_css()

st.title(t("engagement_title"))

start, end = sidebar_date_filter(30)

exclude_ids = tuple(get_internal_user_ids()) if st.session_state.get("exclude_internal") else ()

# ---------------------------------------------------------------------------
# DAU / WAU / MAU cards
# ---------------------------------------------------------------------------

st.subheader(t("active_users"))

active = get_dau_wau_mau(exclude_user_ids=exclude_ids)
if active:
    c1, c2, c3 = st.columns(3)
    c1.metric(t("dau"), active.get("dau", 0), help=t("desc_dau"))
    c2.metric(t("wau"), active.get("wau", 0), help=t("desc_wau"))
    c3.metric(t("mau"), active.get("mau", 0), help=t("desc_mau"))
else:
    st.info(t("no_active_data"))

# ---------------------------------------------------------------------------
# DAU trend
# ---------------------------------------------------------------------------

st.divider()
st.subheader(t("dau_trend"))

df_dau = get_dau_trend(start, end, exclude_user_ids=exclude_ids)
df_dau = filter_df_by_date(df_dau, "day")
if not df_dau.empty:
    fig = line_chart(df_dau, x="day", y="active_users", title=t("chart_dau"))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(t("no_dau_data"))

# ---------------------------------------------------------------------------
# Cohort retention
# ---------------------------------------------------------------------------

st.divider()
st.subheader(t("cohort_retention"))

df_ret = get_retention_cohort(exclude_user_ids=exclude_ids)
if not df_ret.empty:
    # Show as styled table
    display_df = df_ret.copy()
    display_df.columns = [t("cohort_week"), t("size"), "D1 %", "D7 %", "D14 %", "D30 %"]
    fig = heatmap_table(display_df, title=t("chart_retention"))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander(t("raw_data")):
        st.dataframe(display_df, use_container_width=True)
        st.download_button(
            t("download_csv"), display_df.to_csv(index=False),
            "retention_cohort.csv", "text/csv",
        )
else:
    st.info(t("no_retention_data"))

# ---------------------------------------------------------------------------
# Feature adoption
# ---------------------------------------------------------------------------

st.divider()
st.subheader(t("feature_adoption"))

df_feat = get_feature_adoption(exclude_user_ids=exclude_ids)
if not df_feat.empty:
    fig = bar_chart(
        df_feat, x="feature", y="adoption_rate",
        title=t("chart_feature_adoption"),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(t("no_feature_data"))

# ---------------------------------------------------------------------------
# Weekly response rate
# ---------------------------------------------------------------------------

st.divider()
st.subheader(t("weekly_response_rate"))

df_resp = get_weekly_response_rate(start, end, exclude_user_ids=exclude_ids)
df_resp = filter_df_by_date(df_resp, "week_start")
if not df_resp.empty:
    fig = line_chart(df_resp, x="week_start", y="response_rate",
                     title=t("chart_weekly_response"))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(t("no_response_data"))
