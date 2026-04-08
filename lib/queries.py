"""Query functions — wraps RPC calls, returns DataFrames with caching."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from lib.db import rpc, get_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _date_params(start: date, end: date) -> dict:
    return {"p_start_date": start.isoformat(), "p_end_date": end.isoformat()}


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_overview_kpis() -> dict:
    rows = rpc("analytics_overview_kpis")
    return rows[0] if rows else {}


# ---------------------------------------------------------------------------
# Acquisition
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_user_growth(start: date, end: date) -> pd.DataFrame:
    rows = rpc("analytics_user_growth", _date_params(start, end))
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=1800)
def get_signup_methods() -> pd.DataFrame:
    rows = rpc("analytics_signup_methods")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=1800)
def get_platform_distribution() -> pd.DataFrame:
    rows = rpc("analytics_platform_distribution")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_tier_distribution() -> pd.DataFrame:
    rows = rpc("analytics_tier_distribution")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=1800)
def get_trial_conversion() -> pd.DataFrame:
    rows = rpc("analytics_trial_conversion")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Engagement
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_dau_wau_mau(target: date | None = None) -> dict:
    params = {"p_target_date": target.isoformat()} if target else {}
    rows = rpc("analytics_dau_wau_mau", params or None)
    return rows[0] if rows else {}


@st.cache_data(ttl=300)
def get_dau_trend(start: date, end: date) -> pd.DataFrame:
    rows = rpc("analytics_dau_trend", _date_params(start, end))
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=1800)
def get_retention_cohort() -> pd.DataFrame:
    rows = rpc("analytics_retention_cohort")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=1800)
def get_feature_adoption() -> pd.DataFrame:
    rows = rpc("analytics_feature_adoption")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def get_weekly_response_rate(start: date, end: date) -> pd.DataFrame:
    rows = rpc("analytics_weekly_response_rate", _date_params(start, end))
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_daily_checkups(start: date, end: date) -> pd.DataFrame:
    rows = rpc("analytics_daily_checkups", _date_params(start, end))
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def get_checkup_type_stats(start: date, end: date) -> pd.DataFrame:
    rows = rpc("analytics_checkup_type_stats", _date_params(start, end))
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def get_retry_stats(start: date, end: date) -> pd.DataFrame:
    rows = rpc("analytics_retry_stats", _date_params(start, end))
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=1800)
def get_opt_out_count() -> int:
    """Count opted-out recipients."""
    sb = get_client()
    try:
        result = (
            sb.table("recipients")
            .select("id", count="exact")
            .eq("is_opted_out", True)
            .execute()
        )
        return result.count or 0
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Funnel
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_funnel_snapshot() -> pd.DataFrame:
    rows = rpc("analytics_funnel_snapshot")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=1800)
def get_time_to_first_action() -> pd.DataFrame:
    rows = rpc("analytics_time_to_first_action")
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # Filter out users who never took action
    return df


# ---------------------------------------------------------------------------
# Sidebar date filter (shared)
# ---------------------------------------------------------------------------

def sidebar_date_filter(default_days: int = 30) -> tuple[date, date]:
    """Render a date range picker in the sidebar, return (start, end)."""
    st.sidebar.header("Filters")
    preset = st.sidebar.selectbox(
        "Date Range",
        ["Last 7 days", "Last 30 days", "Last 90 days", "All time", "Custom"],
        index=1,
    )
    today = date.today()

    if preset == "Last 7 days":
        start, end = today - timedelta(days=7), today
    elif preset == "Last 30 days":
        start, end = today - timedelta(days=30), today
    elif preset == "Last 90 days":
        start, end = today - timedelta(days=90), today
    elif preset == "All time":
        start, end = date(2026, 1, 1), today
    else:
        start = st.sidebar.date_input("Start", today - timedelta(days=default_days))
        end = st.sidebar.date_input("End", today)

    return start, end
