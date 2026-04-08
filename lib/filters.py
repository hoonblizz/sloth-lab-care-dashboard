"""Data filters — internal account exclusion & pre-launch date filtering."""

from datetime import date

import pandas as pd
import streamlit as st

from lib.i18n import t

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INTERNAL_EMAILS = [
    "hoongoon86@gmail.com",
    "hoonblizz@gmail.com",
    "kay.ij1126@gmail.com",
    "slothlab.review@gmail.com",
]

LAUNCH_DATE = date(2026, 4, 1)


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

def sidebar_filters() -> None:
    """Render filter checkboxes in the sidebar and store state."""
    st.sidebar.checkbox(
        t("exclude_internal"),
        value=True,
        key="exclude_internal",
    )
    st.sidebar.checkbox(
        t("exclude_prelaunch"),
        value=True,
        key="exclude_prelaunch",
    )


# ---------------------------------------------------------------------------
# DataFrame filters (client-side)
# ---------------------------------------------------------------------------

def filter_df_by_email(df: pd.DataFrame, email_col: str = "email") -> pd.DataFrame:
    """Remove rows matching internal emails (if filter is active)."""
    if not st.session_state.get("exclude_internal", True):
        return df
    if email_col not in df.columns or df.empty:
        return df
    return df[~df[email_col].isin(INTERNAL_EMAILS)].reset_index(drop=True)


def filter_df_by_user_id(
    df: pd.DataFrame,
    user_id_col: str = "user_id",
) -> pd.DataFrame:
    """Remove rows whose user_id belongs to an internal account.

    Requires a Supabase lookup (cached) to map emails → user IDs.
    Falls back to no-op if the lookup fails.
    """
    if not st.session_state.get("exclude_internal", True):
        return df
    if user_id_col not in df.columns or df.empty:
        return df

    internal_ids = _get_internal_user_ids()
    if not internal_ids:
        return df
    return df[~df[user_id_col].isin(internal_ids)].reset_index(drop=True)


def filter_df_by_date(
    df: pd.DataFrame,
    date_col: str = "day",
) -> pd.DataFrame:
    """Remove rows before LAUNCH_DATE (if filter is active)."""
    if not st.session_state.get("exclude_prelaunch", True):
        return df
    if date_col not in df.columns or df.empty:
        return df
    # Ensure comparable types
    series = pd.to_datetime(df[date_col]).dt.date
    return df[series >= LAUNCH_DATE].reset_index(drop=True)


def get_min_date() -> date:
    """Return the earliest selectable date based on filter state."""
    if st.session_state.get("exclude_prelaunch", True):
        return LAUNCH_DATE
    return date(2026, 1, 1)


# ---------------------------------------------------------------------------
# Aggregated-data disclaimer
# ---------------------------------------------------------------------------

def aggregated_data_note() -> None:
    """Show a caption when data cannot be filtered client-side."""
    if st.session_state.get("exclude_internal", True):
        st.caption(t("aggregated_note"))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=1800)
def _get_internal_user_ids() -> list[str]:
    """Look up user IDs for internal email addresses."""
    try:
        from lib.db import get_client

        sb = get_client()
        result = (
            sb.table("profiles")
            .select("id")
            .in_("email", INTERNAL_EMAILS)
            .execute()
        )
        return [r["id"] for r in (result.data or [])]
    except Exception:
        return []
