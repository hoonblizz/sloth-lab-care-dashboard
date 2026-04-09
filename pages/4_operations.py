"""Check-up Operations."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from lib.queries import (
    get_daily_checkups,
    get_checkup_type_stats,
    get_retry_stats,
    get_opt_out_count,
    sidebar_date_filter,
)
from lib.charts import stacked_bar_chart, pie_chart, heatmap_table, line_chart, COLORS
from lib.i18n import t, inject_custom_css
from lib.filters import filter_df_by_date, get_internal_user_ids

inject_custom_css()

st.title(t("operations_title"))

start, end = sidebar_date_filter(30)

exclude_ids = tuple(get_internal_user_ids()) if st.session_state.get("exclude_internal") else ()

# ---------------------------------------------------------------------------
# Daily check-up status (stacked bar)
# ---------------------------------------------------------------------------

st.subheader(t("daily_status"))
st.caption(t("section_desc_daily_status"))

df_daily = get_daily_checkups(start, end, exclude_user_ids=exclude_ids)
df_daily = filter_df_by_date(df_daily, "day")

if not df_daily.empty:
    fig = stacked_bar_chart(
        df_daily, x="day",
        y_cols=["responded", "sent", "failed", "retrying", "pending"],
        title=t("chart_status"),
        colors=[COLORS["secondary"], COLORS["info"], COLORS["danger"],
                COLORS["accent"], COLORS["muted"]],
    )
    st.plotly_chart(fig, width="stretch")

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
        st.dataframe(df_daily, width="stretch")
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
    st.caption(t("section_desc_call_sms"))
    df_type = get_checkup_type_stats(start, end, exclude_user_ids=exclude_ids)
    if not df_type.empty:
        fig = pie_chart(df_type, names="checkup_type", values="total",
                        title=t("chart_type_dist"))
        st.plotly_chart(fig, width="stretch")

        # Type stats table
        st.dataframe(
            df_type[["checkup_type", "total", "responded", "failed", "response_rate"]],
            width="stretch",
        )
    else:
        st.info(t("no_type_data"))

with col_right:
    st.subheader(t("retry_stats"))
    st.caption(t("section_desc_retry"))
    df_retry = get_retry_stats(start, end, exclude_user_ids=exclude_ids)
    if not df_retry.empty:
        display = df_retry.copy()
        display.columns = ["Attempt #", t("total"), t("responded"), "Success Rate (%)"]
        fig = heatmap_table(display, title=t("chart_retry"))
        st.plotly_chart(fig, width="stretch")
    else:
        st.info(t("no_retry_data"))

# ---------------------------------------------------------------------------
# Opt-out tracking
# ---------------------------------------------------------------------------

st.divider()
st.subheader(t("opt_out_summary"))
st.caption(t("section_desc_opt_out"))

opt_out = get_opt_out_count(exclude_user_ids=exclude_ids)
st.metric(t("opted_out_recipients"), opt_out, help=t("desc_opted_out"))
st.caption(t("opt_out_caption"))
