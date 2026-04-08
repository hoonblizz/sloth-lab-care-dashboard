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

check_password()

st.title("Subscription & Revenue")
sidebar_date_filter()  # keep sidebar consistent even if not all charts use dates

# ---------------------------------------------------------------------------
# MRR Summary
# ---------------------------------------------------------------------------

kpis = get_overview_kpis()
if kpis:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("MRR", f"${kpis.get('mrr', 0):,.2f}")
    c2.metric("Monthly Subs", kpis.get("monthly_subscribers", 0))
    c3.metric("Annual Subs", kpis.get("annual_subscribers", 0))
    c4.metric("Premium Total", kpis.get("premium_users", 0))

# ---------------------------------------------------------------------------
# Tier distribution
# ---------------------------------------------------------------------------

st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Tier Distribution")
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
                        title="Free vs Premium (Monthly/Annual)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No tier data.")

with col_right:
    st.subheader("Monthly vs Annual")
    if not df_tier.empty:
        df_premium = df_tier[df_tier["tier"] == "premium"].copy()
        if not df_premium.empty:
            fig = pie_chart(df_premium, names="plan_type", values="user_count",
                            title="Premium Plan Type Split")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No premium subscribers yet.")
    else:
        st.info("No data.")

# ---------------------------------------------------------------------------
# Trial Conversion by Cohort
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Trial-to-Paid Conversion by Signup Cohort")

df_conv = get_trial_conversion()

if not df_conv.empty:
    df_conv = df_conv.sort_values("cohort_week")
    fig = bar_chart(df_conv, x="cohort_week", y="conversion_rate",
                    title="Conversion Rate (%) by Weekly Cohort")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Cohort details"):
        st.dataframe(
            df_conv[["cohort_week", "total_signups", "converted", "conversion_rate"]],
            use_container_width=True,
        )
        st.download_button(
            "Download CSV", df_conv.to_csv(index=False),
            "trial_conversion.csv", "text/csv",
        )
else:
    st.info("No conversion data.")

# ---------------------------------------------------------------------------
# Revenue calculation note
# ---------------------------------------------------------------------------

st.divider()
st.caption(
    "MRR = (monthly subs x $5.99) + (annual subs x $59.99 / 12). "
    "Historical MRR trend requires webhook event logs (future enhancement)."
)
