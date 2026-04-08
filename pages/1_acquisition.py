"""User Acquisition & Growth."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from lib.db import check_password
from lib.queries import (
    get_user_growth,
    get_signup_methods,
    get_platform_distribution,
    sidebar_date_filter,
)
from lib.charts import dual_axis_chart, pie_chart, bar_chart

check_password()

st.title("User Acquisition & Growth")

start, end = sidebar_date_filter(30)

# ---------------------------------------------------------------------------
# User growth — dual axis (new users bar + cumulative line)
# ---------------------------------------------------------------------------

st.subheader("User Growth")

df_growth = get_user_growth(start, end)

if not df_growth.empty:
    fig = dual_axis_chart(
        df_growth,
        x="day", y1="new_users", y2="cumulative_users",
        name1="New Users", name2="Cumulative",
        title="Daily New Users & Cumulative Total",
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Raw data"):
        st.dataframe(df_growth, use_container_width=True)
        st.download_button(
            "Download CSV", df_growth.to_csv(index=False),
            "user_growth.csv", "text/csv",
        )
else:
    st.info("No user data for selected range.")

# ---------------------------------------------------------------------------
# Signup methods & Platform — side by side
# ---------------------------------------------------------------------------

st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Signup Methods")
    df_methods = get_signup_methods()
    if not df_methods.empty:
        # Friendly labels
        label_map = {"google": "Google", "apple": "Apple", "email": "Email/OTP"}
        df_methods["method"] = df_methods["method"].map(
            lambda m: label_map.get(m, m.title())
        )
        fig = pie_chart(df_methods, names="method", values="user_count",
                        title="Auth Provider Distribution")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No signup method data.")

with col_right:
    st.subheader("Platform Distribution")
    df_platform = get_platform_distribution()
    if not df_platform.empty:
        fig = pie_chart(df_platform, names="platform", values="user_count",
                        title="iOS vs Android")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No platform data (requires analytics_events).")
