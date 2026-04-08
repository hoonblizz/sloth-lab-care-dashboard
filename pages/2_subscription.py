"""Subscription & Revenue."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from lib.db import check_password
from lib.queries import (
    get_tier_distribution,
    get_trial_conversion,
    get_overview_kpis,
    get_mrr_trend,
    get_churn_reasons,
    get_subscription_lifecycle,
    sidebar_date_filter,
)
from lib.charts import pie_chart, bar_chart, line_chart, COLORS
from lib.i18n import t, inject_custom_css
from lib.filters import get_internal_user_ids

check_password()
inject_custom_css()

st.title(t("subscription_title"))
start, end = sidebar_date_filter()

exclude_ids = tuple(get_internal_user_ids()) if st.session_state.get("exclude_internal") else ()

# ---------------------------------------------------------------------------
# MRR Summary
# ---------------------------------------------------------------------------

kpis = get_overview_kpis(exclude_user_ids=exclude_ids)
if kpis:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("mrr"), f"CA${kpis.get('mrr', 0):,.2f}",
              help=t("desc_mrr"))
    c2.metric(t("monthly_subs"), kpis.get("monthly_subscribers", 0),
              help=t("desc_monthly_subs"))
    c3.metric(t("annual_subs"), kpis.get("annual_subscribers", 0),
              help=t("desc_annual_subs"))
    c4.metric(t("premium_total"), kpis.get("premium_users", 0),
              help=t("desc_premium"))

# ---------------------------------------------------------------------------
# Tier distribution
# ---------------------------------------------------------------------------

st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader(t("tier_distribution"))
    df_tier = get_tier_distribution(exclude_user_ids=exclude_ids)
    if not df_tier.empty:
        # Combine tier + plan_type for labeling
        df_tier["label"] = df_tier.apply(
            lambda r: f"Premium ({r['plan_type']})"
            if r["tier"] == "premium" else "Free",
            axis=1,
        )
        df_agg = df_tier.groupby("label", as_index=False)["user_count"].sum()
        fig = pie_chart(df_agg, names="label", values="user_count",
                        title=t("chart_tier"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(t("no_tier_data"))

with col_right:
    st.subheader(t("monthly_vs_annual"))
    if not df_tier.empty:
        df_premium = df_tier[df_tier["tier"] == "premium"].copy()
        if not df_premium.empty:
            fig = pie_chart(df_premium, names="plan_type", values="user_count",
                            title=t("chart_plan_split"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(t("no_premium_yet"))
    else:
        st.info(t("no_data"))

# ---------------------------------------------------------------------------
# Trial Conversion by Cohort
# ---------------------------------------------------------------------------

st.divider()
st.subheader(t("trial_conversion_title"))

df_conv = get_trial_conversion(exclude_user_ids=exclude_ids)

if not df_conv.empty:
    df_conv = df_conv.sort_values("cohort_week")
    fig = bar_chart(df_conv, x="cohort_week", y="conversion_rate",
                    title=t("chart_conversion_cohort"))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander(t("cohort_details")):
        st.dataframe(
            df_conv[["cohort_week", "total_signups", "converted", "conversion_rate"]],
            use_container_width=True,
        )
        st.download_button(
            t("download_csv"), df_conv.to_csv(index=False),
            "trial_conversion.csv", "text/csv",
        )
else:
    st.info(t("no_conversion_data"))

# ---------------------------------------------------------------------------
# MRR Trend (subscription_events based)
# ---------------------------------------------------------------------------

st.divider()

st.subheader(t("mrr_trend_title"), help=t("desc_mrr_trend"))
df_mrr = get_mrr_trend(start, end, exclude_user_ids=exclude_ids)
if not df_mrr.empty and df_mrr["mrr"].sum() > 0:
    fig = line_chart(df_mrr, x="month", y=["mrr"], title=t("chart_mrr_trend"))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(t("no_mrr_trend_data"))

# ---------------------------------------------------------------------------
# Subscription Events & Churn Reasons (2-column)
# ---------------------------------------------------------------------------

st.divider()
col_events, col_churn = st.columns(2)

with col_events:
    st.subheader(t("subscription_lifecycle_title"), help=t("desc_subscription_lifecycle"))
    df_lifecycle = get_subscription_lifecycle(exclude_user_ids=exclude_ids)
    if not df_lifecycle.empty:
        fig = bar_chart(df_lifecycle, x="event_type", y="event_count",
                        title=t("chart_subscription_lifecycle"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(t("no_lifecycle_data"))

with col_churn:
    st.subheader(t("churn_reasons_title"), help=t("desc_churn_reasons"))
    df_churn = get_churn_reasons(exclude_user_ids=exclude_ids)
    if not df_churn.empty:
        fig = pie_chart(df_churn, names="reason", values="event_count",
                        title=t("chart_churn_reasons"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(t("no_churn_data"))

# ---------------------------------------------------------------------------
# Revenue calculation note
# ---------------------------------------------------------------------------

st.divider()
st.caption(t("mrr_note"))
