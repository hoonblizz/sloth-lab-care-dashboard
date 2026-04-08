"""Check-up Operations."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from lib.db import check_password
from lib.queries import (
    get_daily_checkups,
    get_checkup_type_stats,
    get_retry_stats,
    get_opt_out_count,
    sidebar_date_filter,
)
from lib.charts import stacked_bar_chart, pie_chart, heatmap_table, line_chart, COLORS

check_password()

st.title("Check-up Operations")

start, end = sidebar_date_filter(30)

# ---------------------------------------------------------------------------
# Daily check-up status (stacked bar)
# ---------------------------------------------------------------------------

st.subheader("Daily Check-up Status")

df_daily = get_daily_checkups(start, end)

if not df_daily.empty:
    fig = stacked_bar_chart(
        df_daily, x="day",
        y_cols=["responded", "sent", "failed", "retrying", "pending"],
        title="Check-ups by Status",
        colors=[COLORS["secondary"], COLORS["info"], COLORS["danger"],
                COLORS["accent"], COLORS["muted"]],
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", int(df_daily["total"].sum()))
    c2.metric("Responded", int(df_daily["responded"].sum()))
    c3.metric("Failed", int(df_daily["failed"].sum()))
    total_delivered = df_daily["responded"].sum() + df_daily["sent"].sum() + df_daily["failed"].sum()
    rate = round(df_daily["responded"].sum() / max(total_delivered, 1) * 100, 1)
    c4.metric("Response Rate", f"{rate}%")

    with st.expander("Raw data"):
        st.dataframe(df_daily, use_container_width=True)
        st.download_button(
            "Download CSV", df_daily.to_csv(index=False),
            "daily_checkups.csv", "text/csv",
        )
else:
    st.info("No check-up data for selected range.")

# ---------------------------------------------------------------------------
# Call vs SMS + Retry stats (side by side)
# ---------------------------------------------------------------------------

st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Call vs SMS")
    df_type = get_checkup_type_stats(start, end)
    if not df_type.empty:
        fig = pie_chart(df_type, names="checkup_type", values="total",
                        title="Check-up Type Distribution")
        st.plotly_chart(fig, use_container_width=True)

        # Type stats table
        st.dataframe(
            df_type[["checkup_type", "total", "responded", "failed", "response_rate"]],
            use_container_width=True,
        )
    else:
        st.info("No type data.")

with col_right:
    st.subheader("Retry Attempt Stats")
    df_retry = get_retry_stats(start, end)
    if not df_retry.empty:
        display = df_retry.copy()
        display.columns = ["Attempt #", "Total", "Responded", "Success Rate (%)"]
        fig = heatmap_table(display, title="Success Rate by Attempt Number")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No retry data.")

# ---------------------------------------------------------------------------
# Opt-out tracking
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Opt-out Summary")

opt_out = get_opt_out_count()
st.metric("Opted-out Recipients", opt_out)
st.caption(
    "Recipients who replied STOP. These recipients are automatically "
    "excluded from future check-ups."
)
