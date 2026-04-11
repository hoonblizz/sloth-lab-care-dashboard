"""Messaging Outbox — view + resend queued/sent/failed messages."""

from __future__ import annotations

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.messaging import (  # noqa: E402
    list_outbox,
    list_template_slugs,
    outbox_metrics,
    reset_outbox_to_pending,
)
from lib.supabase_client import get_env_client  # noqa: E402


STATUS_OPTIONS = ["all", "pending", "sending", "sent", "failed", "skipped"]
STATUS_BADGE = {
    "pending": "🟡",
    "sending": "🔵",
    "sent": "🟢",
    "failed": "🔴",
    "skipped": "⚪️",
}


def main() -> None:
    st.set_page_config(
        page_title="Messaging Outbox",
        page_icon=":outbox_tray:",
        layout="wide",
    )
    st.title("Messaging Outbox")

    env, sb = get_env_client()
    st.caption(f"환경: **{env}**")

    # ---- Metrics ----
    metrics = outbox_metrics(sb)
    col1, col2, col3 = st.columns(3)
    col1.metric("Pending", metrics.get("pending", 0))
    col2.metric("Sent today", metrics.get("sent_today", 0))
    col3.metric("Failed today", metrics.get("failed_today", 0))

    st.divider()

    # ---- Filters ----
    slugs = list_template_slugs(sb)
    fcol1, fcol2, fcol3 = st.columns([2, 2, 1])
    with fcol1:
        status = st.selectbox("Status 필터", options=STATUS_OPTIONS, index=0)
    with fcol2:
        slug_filter = st.selectbox(
            "Template slug 필터",
            options=["(전체)"] + slugs,
        )
    with fcol3:
        st.write("")
        st.write("")
        if st.button("새로고침", use_container_width=True):
            st.rerun()

    rows = list_outbox(
        sb,
        status=status if status != "all" else None,
        template_slug=slug_filter if slug_filter != "(전체)" else None,
        limit=200,
    )

    if not rows:
        st.info("표시할 outbox 항목이 없습니다.")
        return

    st.markdown(f"**총 {len(rows)}건**")

    for row in rows:
        _render_row(sb, row)


def _render_row(sb, row: dict) -> None:
    rid = row["id"]
    status = row.get("status", "?")
    badge = STATUS_BADGE.get(status, "")
    title = (
        f"{badge} `{row.get('template_slug', '?')}` → "
        f"{row.get('recipient_email', '?')} · {row.get('language', '?')} "
        f"({status})"
    )
    with st.expander(title):
        meta_cols = st.columns(2)
        with meta_cols[0]:
            st.markdown(f"**ID:** `{rid}`")
            st.markdown(f"**Profile:** `{row.get('profile_id', '—')}`")
            st.markdown(f"**Channel:** {row.get('channel', '—')}")
            st.markdown(f"**Subject:** {row.get('subject', '—')}")
            st.markdown(f"**Dedupe key:** `{row.get('dedupe_key', '—')}`")
        with meta_cols[1]:
            st.markdown(f"**Created:** {row.get('created_at', '—')}")
            st.markdown(f"**Scheduled:** {row.get('scheduled_at', '—')}")
            st.markdown(f"**Sent:** {row.get('sent_at', '—')}")
            st.markdown(f"**Attempts:** {row.get('attempts', 0)}")
            if row.get("provider_msg_id"):
                st.markdown(f"**Provider msg:** `{row['provider_msg_id']}`")

        if row.get("variables"):
            st.markdown("**Variables**")
            st.json(row["variables"])

        if row.get("last_error"):
            st.error(f"마지막 오류: {row['last_error']}")

        if row.get("body_html"):
            with st.container():
                st.markdown("**HTML 미리보기**")
                import streamlit.components.v1 as components

                components.html(row["body_html"], height=420, scrolling=True)

        if status == "failed":
            if st.button("Resend (pending으로 재큐잉)", key=f"resend_{rid}"):
                reset_outbox_to_pending(sb, rid)
                st.success("재큐잉됨. 다음 cron 사이클(최대 5분)에 재시도됩니다.")
                st.rerun()


main()
