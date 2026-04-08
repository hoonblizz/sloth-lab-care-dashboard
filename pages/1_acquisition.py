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
from lib.i18n import t, inject_custom_css
from lib.filters import filter_df_by_date, get_internal_user_ids

check_password()
inject_custom_css()

st.title(t("acquisition_title"))

start, end = sidebar_date_filter(30)

exclude_ids = tuple(get_internal_user_ids()) if st.session_state.get("exclude_internal") else ()

# ---------------------------------------------------------------------------
# User growth — dual axis (new users bar + cumulative line)
# ---------------------------------------------------------------------------

st.subheader(t("user_growth"))

df_growth = get_user_growth(start, end, exclude_user_ids=exclude_ids)
df_growth = filter_df_by_date(df_growth, "day")

if not df_growth.empty:
    fig = dual_axis_chart(
        df_growth,
        x="day", y1="new_users", y2="cumulative_users",
        name1=t("new_users"), name2=t("cumulative"),
        title=t("chart_user_growth"),
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander(t("raw_data")):
        st.dataframe(df_growth, use_container_width=True)
        st.download_button(
            t("download_csv"), df_growth.to_csv(index=False),
            "user_growth.csv", "text/csv",
        )
else:
    st.info(t("no_user_data"))

# ---------------------------------------------------------------------------
# Signup methods & Platform — side by side
# ---------------------------------------------------------------------------

st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader(t("signup_methods"))
    df_methods = get_signup_methods(exclude_user_ids=exclude_ids)
    if not df_methods.empty:
        # Friendly labels
        label_map = {"google": "Google", "apple": "Apple", "email": "Email/OTP"}
        df_methods["method"] = df_methods["method"].map(
            lambda m: label_map.get(m, m.title())
        )
        fig = pie_chart(df_methods, names="method", values="user_count",
                        title=t("chart_signup_methods"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(t("no_signup_data"))

with col_right:
    st.subheader(t("platform_distribution"))
    df_platform = get_platform_distribution(exclude_user_ids=exclude_ids)
    if not df_platform.empty:
        fig = pie_chart(df_platform, names="platform", values="user_count",
                        title=t("chart_platform"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(t("no_platform_data"))
