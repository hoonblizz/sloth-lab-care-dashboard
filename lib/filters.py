"""Data filters — internal account exclusion & pre-launch date filtering.

Excluded accounts are stored in `public.analytics_excluded_users` (DB-managed
via the Settings page). The list is cached for 5 minutes; mutating helpers
clear the cache so changes propagate immediately within the same session.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from lib.i18n import t

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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
    """Remove rows matching excluded emails (if filter is active)."""
    if not st.session_state.get("exclude_internal", True):
        return df
    if email_col not in df.columns or df.empty:
        return df
    excluded = set(get_excluded_emails())
    if not excluded:
        return df
    return df[~df[email_col].isin(excluded)].reset_index(drop=True)


def filter_df_by_user_id(
    df: pd.DataFrame,
    user_id_col: str = "user_id",
) -> pd.DataFrame:
    """Remove rows whose user_id belongs to an excluded account."""
    if not st.session_state.get("exclude_internal", True):
        return df
    if user_id_col not in df.columns or df.empty:
        return df

    internal_ids = get_internal_user_ids()
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
# Excluded-user lookups (DB-backed)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_excluded_records() -> list[dict]:
    """Return all rows from `analytics_excluded_users` (cached 5 min).

    On failure, surfaces a sidebar warning so the user knows the exclusion
    list could not be loaded — preventing silent inclusion of internal
    accounts in metrics.
    """
    try:
        from lib.db import get_client

        sb = get_client()
        result = (
            sb.table("analytics_excluded_users")
            .select("id, email, reason, added_by, added_at")
            .order("added_at", desc=False)
            .execute()
        )
        return result.data or []
    except Exception as e:
        st.sidebar.warning(
            f"⚠️ Could not load exclusion list: {e}. "
            "Internal accounts may be included in metrics."
        )
        return []


def get_excluded_emails() -> list[str]:
    """Convenience wrapper returning just the email column."""
    return [r["email"] for r in get_excluded_records()]


@st.cache_data(ttl=1800)
def get_internal_user_ids() -> list[str]:
    """Look up user IDs whose email is in the excluded list."""
    emails = get_excluded_emails()
    if not emails:
        return []
    try:
        from lib.db import get_client

        sb = get_client()
        result = (
            sb.table("profiles")
            .select("id")
            .in_("email", emails)
            .execute()
        )
        return [r["id"] for r in (result.data or [])]
    except Exception as e:
        st.sidebar.warning(
            f"⚠️ Could not resolve excluded user IDs: {e}. "
            "Internal accounts may be included in metrics."
        )
        return []


# ---------------------------------------------------------------------------
# Mutations (Settings page)
# ---------------------------------------------------------------------------

def add_excluded_email(email: str, reason: str | None = None,
                       added_by: str = "dashboard") -> tuple[bool, str]:
    """Insert a new excluded email. Returns (ok, message_key)."""
    email_norm = (email or "").strip().lower()
    if not _is_valid_email(email_norm):
        return False, "email_invalid"

    try:
        from lib.db import get_client

        sb = get_client()
        sb.table("analytics_excluded_users").insert({
            "email": email_norm,
            "reason": (reason or "").strip() or None,
            "added_by": added_by,
        }).execute()
    except Exception as e:
        if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
            return False, "email_duplicate"
        return False, str(e)

    _invalidate_cache()
    return True, "add_success"


def remove_excluded_email(email: str) -> tuple[bool, str]:
    """Delete an excluded email row. Returns (ok, message_key)."""
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return False, "email_invalid"

    try:
        from lib.db import get_client

        sb = get_client()
        sb.table("analytics_excluded_users").delete().eq("email", email_norm).execute()
    except Exception as e:
        return False, str(e)

    _invalidate_cache()
    return True, "remove_success"


def _invalidate_cache() -> None:
    """Clear caches that depend on the excluded list."""
    get_excluded_records.clear()
    get_internal_user_ids.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

import re

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _is_valid_email(value: str) -> bool:
    return bool(_EMAIL_RE.match(value))
