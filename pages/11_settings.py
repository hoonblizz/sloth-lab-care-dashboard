"""Settings — manage analytics filters & exclusion list (DB-backed)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from lib.filters import (
    add_excluded_email,
    get_excluded_records,
    remove_excluded_email,
)
from lib.i18n import inject_custom_css, t

inject_custom_css()

st.title(t("settings_title"))
st.caption(t("settings_subtitle"))

# ---------------------------------------------------------------------------
# Excluded accounts list
# ---------------------------------------------------------------------------

st.subheader(t("settings_excluded_section"))
st.caption(t("settings_excluded_caption"))

records = get_excluded_records()

if not records:
    st.info(t("no_excluded_accounts"))
else:
    df = pd.DataFrame(records)
    df["added_at"] = pd.to_datetime(df["added_at"]).dt.strftime("%Y-%m-%d %H:%M")

    header_cols = st.columns([3, 3, 2, 2, 1])
    header_cols[0].markdown(f"**{t('email_label')}**")
    header_cols[1].markdown(f"**{t('reason_label')}**")
    header_cols[2].markdown(f"**{t('added_by_label')}**")
    header_cols[3].markdown(f"**{t('added_at_label')}**")
    header_cols[4].markdown("&nbsp;")

    for row in df.to_dict("records"):
        c1, c2, c3, c4, c5 = st.columns([3, 3, 2, 2, 1])
        c1.write(row["email"])
        c2.write(row.get("reason") or "—")
        c3.write(row.get("added_by") or "—")
        c4.write(row["added_at"])
        if c5.button(t("remove_button"), key=f"rm_{row['id']}"):
            ok, msg_key = remove_excluded_email(row["email"])
            if ok:
                st.success(t(msg_key))
                st.rerun()
            else:
                st.error(t(msg_key) if msg_key in {
                    "email_invalid", "email_duplicate"
                } else msg_key)

st.divider()

# ---------------------------------------------------------------------------
# Add new excluded account
# ---------------------------------------------------------------------------

st.subheader(t("settings_add_section"))

with st.form("add_excluded_form", clear_on_submit=True):
    new_email = st.text_input(t("email_label"), placeholder="user@example.com")
    new_reason = st.text_input(t("reason_label"), placeholder="e.g. Internal — QA")
    submitted = st.form_submit_button(t("add_button"))

    if submitted:
        ok, msg_key = add_excluded_email(
            new_email,
            reason=new_reason,
            added_by="dashboard",
        )
        if ok:
            st.success(t(msg_key))
            st.rerun()
        else:
            st.error(t(msg_key) if msg_key in {
                "email_invalid", "email_duplicate"
            } else msg_key)

st.divider()

# ---------------------------------------------------------------------------
# Cache control
# ---------------------------------------------------------------------------

st.subheader(t("settings_cache_section"))
st.caption(t("settings_cache_caption"))

if st.button(t("refresh_button")):
    st.cache_data.clear()
    st.success(t("cache_cleared"))
