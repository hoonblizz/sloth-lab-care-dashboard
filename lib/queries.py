"""Query functions — wraps RPC calls, returns DataFrames with caching."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from lib.db import rpc, get_client
from lib.i18n import t, sidebar_language_toggle
from lib.filters import sidebar_filters, get_min_date


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _date_params(start: date, end: date) -> dict:
    return {"p_start_date": start.isoformat(), "p_end_date": end.isoformat()}


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_overview_kpis(exclude_user_ids: tuple[str, ...] = ()) -> dict:
    params = {"p_exclude_user_ids": list(exclude_user_ids)} if exclude_user_ids else None
    rows = rpc("analytics_overview_kpis", params)
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
def get_funnel_snapshot(exclude_user_ids: tuple[str, ...] = ()) -> pd.DataFrame:
    params = {"p_exclude_user_ids": list(exclude_user_ids)} if exclude_user_ids else None
    rows = rpc("analytics_funnel_snapshot", params)
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
# Marketing
# ---------------------------------------------------------------------------

@st.cache_data(ttl=1800)
def get_recipient_geography() -> pd.DataFrame:
    rows = rpc("analytics_recipient_geography")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def get_checkup_timing() -> pd.DataFrame:
    rows = rpc("analytics_checkup_timing")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def get_user_health() -> pd.DataFrame:
    rows = rpc("analytics_user_health")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def get_inactive_users() -> dict:
    rows = rpc("analytics_inactive_users")
    return rows[0] if rows else {}


@st.cache_data(ttl=300)
def get_user_engagement_segments() -> pd.DataFrame:
    rows = rpc("analytics_user_engagement_segments")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


@st.cache_data(ttl=300)
def get_response_latency() -> pd.DataFrame:
    rows = rpc("analytics_response_latency")
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Sidebar date filter (shared)
# ---------------------------------------------------------------------------

def sidebar_date_filter(default_days: int = 30) -> tuple[date, date]:
    """Render language toggle, filter checkboxes, and date picker in sidebar."""
    sidebar_language_toggle()
    sidebar_filters()

    st.sidebar.header(t("filters"))

    presets = [
        t("last_7_days"),
        t("last_30_days"),
        t("last_90_days"),
        t("all_time"),
        t("custom"),
    ]
    preset = st.sidebar.selectbox(t("date_range"), presets, index=1)
    today = date.today()
    min_date = get_min_date()

    if preset == presets[0]:  # Last 7 days
        start, end = max(today - timedelta(days=7), min_date), today
    elif preset == presets[1]:  # Last 30 days
        start, end = max(today - timedelta(days=30), min_date), today
    elif preset == presets[2]:  # Last 90 days
        start, end = max(today - timedelta(days=90), min_date), today
    elif preset == presets[3]:  # All time
        start, end = min_date, today
    else:
        start = st.sidebar.date_input(
            t("start"), max(today - timedelta(days=default_days), min_date),
            min_value=min_date,
        )
        end = st.sidebar.date_input(t("end"), today, min_value=min_date)

    return start, end
