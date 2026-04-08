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
    sidebar_date_filter,
)
from lib.charts import pie_chart, bar_chart, COLORS
from lib.i18n import t, inject_custom_css
from lib.filters import aggregated_data_note

check_password()
inject_custom_css()

st.title(t("subscription_title"))
sidebar_date_filter()  # keep sidebar consistent even if not all charts use dates

# ---------------------------------------------------------------------------
# MRR Summary
# ---------------------------------------------------------------------------

kpis = get_overview_kpis()
if kpis:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("mrr"), f"${kpis.get('mrr', 0):,.2f}",
              help=t("desc_mrr"))
    c2.metric(t("monthly_subs"), kpis.get("monthly_subscribers", 0),
              help=t("desc_monthly_subs"))
    c3.metric(t("annual_subs"), kpis.get("annual_subscribers", 0),
              help=t("desc_annual_subs"))
    c4.metric(t("premium_total"), kpis.get("premium_users", 0),
              help=t("desc_premium"))

aggregated_data_note()

# ---------------------------------------------------------------------------
# Tier distribution
# ---------------------------------------------------------------------------

st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader(t("tier_distribution"))
    df_tier = get_tier_distribution()
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

df_conv = get_trial_conversion()

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

aggregated_data_note()

# ---------------------------------------------------------------------------
# Revenue calculation note
# ---------------------------------------------------------------------------

st.divider()
st.caption(t("mrr_note"))
