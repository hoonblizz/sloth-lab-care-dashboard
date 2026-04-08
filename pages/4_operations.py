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
from lib.i18n import t, inject_custom_css
from lib.filters import filter_df_by_date, aggregated_data_note

check_password()
inject_custom_css()

st.title(t("operations_title"))

start, end = sidebar_date_filter(30)

# ---------------------------------------------------------------------------
# Daily check-up status (stacked bar)
# ---------------------------------------------------------------------------

st.subheader(t("daily_status"))

df_daily = get_daily_checkups(start, end)
df_daily = filter_df_by_date(df_daily, "day")

if not df_daily.empty:
    fig = stacked_bar_chart(
        df_daily, x="day",
        y_cols=["responded", "sent", "failed", "retrying", "pending"],
        title=t("chart_status"),
        colors=[COLORS["secondary"], COLORS["info"], COLORS["danger"],
                COLORS["accent"], COLORS["muted"]],
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("total"), int(df_daily["total"].sum()),
              help=t("desc_total_checkups"))
    c2.metric(t("responded"), int(df_daily["responded"].sum()),
              help=t("desc_responded"))
    c3.metric(t("failed"), int(df_daily["failed"].sum()),
              help=t("desc_failed"))
    total_delivered = df_daily["responded"].sum() + df_daily["sent"].sum() + df_daily["failed"].sum()
    rate = round(df_daily["responded"].sum() / max(total_delivered, 1) * 100, 1)
    c4.metric(t("response_rate"), f"{rate}%",
              help=t("desc_response_rate"))

    with st.expander(t("raw_data")):
        st.dataframe(df_daily, use_container_width=True)
        st.download_button(
            t("download_csv"), df_daily.to_csv(index=False),
            "daily_checkups.csv", "text/csv",
        )
else:
    st.info(t("no_checkup_range"))

# ---------------------------------------------------------------------------
# Call vs SMS + Retry stats (side by side)
# ---------------------------------------------------------------------------

st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader(t("call_vs_sms"))
    df_type = get_checkup_type_stats(start, end)
    if not df_type.empty:
        fig = pie_chart(df_type, names="checkup_type", values="total",
                        title=t("chart_type_dist"))
        st.plotly_chart(fig, use_container_width=True)

        # Type stats table
        st.dataframe(
            df_type[["checkup_type", "total", "responded", "failed", "response_rate"]],
            use_container_width=True,
        )
    else:
        st.info(t("no_type_data"))
    aggregated_data_note()

with col_right:
    st.subheader(t("retry_stats"))
    df_retry = get_retry_stats(start, end)
    if not df_retry.empty:
        display = df_retry.copy()
        display.columns = ["Attempt #", t("total"), t("responded"), "Success Rate (%)"]
        fig = heatmap_table(display, title=t("chart_retry"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(t("no_retry_data"))

# ---------------------------------------------------------------------------
# Opt-out tracking
# ---------------------------------------------------------------------------

st.divider()
st.subheader(t("opt_out_summary"))

opt_out = get_opt_out_count()
st.metric(t("opted_out_recipients"), opt_out, help=t("desc_opted_out"))
st.caption(t("opt_out_caption"))
