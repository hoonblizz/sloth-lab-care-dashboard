"""Funnel Analysis."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from lib.queries import (
    get_funnel_snapshot,
    get_time_to_first_action,
    sidebar_date_filter,
)
from lib.charts import funnel_chart, histogram, COLORS
from lib.i18n import t, inject_custom_css
from lib.filters import get_internal_user_ids

inject_custom_css()

st.title(t("funnel_title"))
sidebar_date_filter()  # consistent sidebar

# ---------------------------------------------------------------------------
# Full funnel
# ---------------------------------------------------------------------------

st.subheader(t("user_journey"))
st.caption(t("section_desc_funnel"))

exclude_ids = tuple(get_internal_user_ids()) if st.session_state.get("exclude_internal") else ()
df_funnel = get_funnel_snapshot(exclude_user_ids=exclude_ids)

if not df_funnel.empty:
    fig = funnel_chart(df_funnel, stage_col="stage", value_col="user_count",
                       title=t("chart_funnel"))
    st.plotly_chart(fig, width="stretch")

    # Drop-off table
    st.subheader(t("stage_dropoff"))
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
                "stage": t("stage"),
                "user_count": t("users"),
                "pct_of_total": t("pct_of_total"),
                "dropoff": t("dropoff_prev"),
            }
        ),
        width="stretch",
    )
else:
    st.info(t("no_funnel_data"))

# ---------------------------------------------------------------------------
# Time to first action
# ---------------------------------------------------------------------------

st.divider()
st.subheader(t("time_to_first_action"))
st.caption(t("section_desc_time_to_action"))

df_action = get_time_to_first_action(exclude_user_ids=exclude_ids)

if not df_action.empty:
    col_left, col_right = st.columns(2)

    with col_left:
        # Signup → First Recipient
        df_rec = df_action[df_action["hours_to_recipient"].notna()].copy()
        if not df_rec.empty:
            fig = histogram(
                df_rec["hours_to_recipient"],
                title=t("chart_time_recipient"),
                xaxis_title=t("hours"),
                nbins=25,
            )
            st.plotly_chart(fig, width="stretch")
            median_h = df_rec["hours_to_recipient"].median()
            st.metric(t("median"), f"{median_h:.1f} h",
                      help=t("desc_time_to_recipient"))
        else:
            st.info(t("no_recipients_yet"))

    with col_right:
        # Signup → First Check-up
        df_chk = df_action[df_action["hours_to_checkup"].notna()].copy()
        if not df_chk.empty:
            fig = histogram(
                df_chk["hours_to_checkup"],
                title=t("chart_time_checkup"),
                xaxis_title=t("hours"),
                nbins=25,
            )
            st.plotly_chart(fig, width="stretch")
            median_h = df_chk["hours_to_checkup"].median()
            st.metric(t("median"), f"{median_h:.1f} h",
                      help=t("desc_time_to_checkup"))
        else:
            st.info(t("no_checkups_yet"))

    with st.expander(t("raw_data")):
        st.dataframe(df_action, width="stretch")
        st.download_button(
            t("download_csv"), df_action.to_csv(index=False),
            "time_to_first_action.csv", "text/csv",
        )
else:
    st.info(t("no_action_data"))
