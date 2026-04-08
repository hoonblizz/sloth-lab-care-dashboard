"""Funnel Analysis."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from lib.db import check_password
from lib.queries import (
    get_funnel_snapshot,
    get_time_to_first_action,
    sidebar_date_filter,
)
from lib.charts import funnel_chart, histogram, COLORS

check_password()

st.title("Funnel Analysis")
sidebar_date_filter()  # consistent sidebar

# ---------------------------------------------------------------------------
# Full funnel
# ---------------------------------------------------------------------------

st.subheader("User Journey Funnel")

df_funnel = get_funnel_snapshot()

if not df_funnel.empty:
    fig = funnel_chart(df_funnel, stage_col="stage", value_col="user_count",
                       title="Signup to Subscription Funnel")
    st.plotly_chart(fig, use_container_width=True)

    # Drop-off table
    st.subheader("Stage Drop-off")
    df_drop = df_funnel.copy()
    df_drop["prev_count"] = df_drop["user_count"].shift(1)
    df_drop["dropoff"] = df_drop.apply(
        lambda r: f"{round((1 - r['user_count'] / r['prev_count']) * 100, 1)}%"
        if pd.notna(r["prev_count"]) and r["prev_count"] > 0 else "-",
        axis=1,
    )
    st.dataframe(
        df_drop[["stage", "user_count", "pct_of_total", "dropoff"]].rename(
            columns={
                "stage": "Stage",
                "user_count": "Users",
                "pct_of_total": "% of Total",
                "dropoff": "Drop-off from Prev",
            }
        ),
        use_container_width=True,
    )
else:
    st.info("No funnel data available.")

# ---------------------------------------------------------------------------
# Time to first action
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Time to First Action")

df_action = get_time_to_first_action()

if not df_action.empty:
    col_left, col_right = st.columns(2)

    with col_left:
        # Signup → First Recipient
        df_rec = df_action[df_action["hours_to_recipient"].notna()].copy()
        if not df_rec.empty:
            fig = histogram(
                df_rec["hours_to_recipient"],
                title="Hours: Signup to First Recipient",
                xaxis_title="Hours",
                nbins=25,
            )
            st.plotly_chart(fig, use_container_width=True)
            median_h = df_rec["hours_to_recipient"].median()
            st.metric("Median", f"{median_h:.1f} hours")
        else:
            st.info("No users with recipients yet.")

    with col_right:
        # Signup → First Check-up
        df_chk = df_action[df_action["hours_to_checkup"].notna()].copy()
        if not df_chk.empty:
            fig = histogram(
                df_chk["hours_to_checkup"],
                title="Hours: Signup to First Check-up",
                xaxis_title="Hours",
                nbins=25,
            )
            st.plotly_chart(fig, use_container_width=True)
            median_h = df_chk["hours_to_checkup"].median()
            st.metric("Median", f"{median_h:.1f} hours")
        else:
            st.info("No users with check-ups yet.")

    with st.expander("Raw data"):
        st.dataframe(df_action, use_container_width=True)
        st.download_button(
            "Download CSV", df_action.to_csv(index=False),
            "time_to_first_action.csv", "text/csv",
        )
else:
    st.info("No user action data.")
