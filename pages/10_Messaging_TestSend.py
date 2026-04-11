"""Messaging Test Send — deliver a template preview to your own inbox."""

from __future__ import annotations

import json
import os
import sys

import requests
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.messaging import (  # noqa: E402
    SUPPORTED_LANGUAGES,
    get_template,
    list_template_slugs,
)
from lib.rendering import render_email_preview  # noqa: E402
from lib.supabase_client import (  # noqa: E402
    get_env_client,
    get_service_role_key,
    get_supabase_url,
)


DEFAULT_VARIABLES = {
    "first_name": "Alex",
    "display_name": "Alex Kim",
    "email": "alex@example.com",
    "trial_end_date": "April 15, 2026",
    "days_until_expiry": "2",
}


def main() -> None:
    st.set_page_config(
        page_title="Messaging Test Send",
        page_icon=":test_tube:",
        layout="wide",
    )
    st.title("Messaging Test Send")

    env, sb = get_env_client()
    st.caption(f"환경: **{env}** — 실제 이메일이 발송됩니다.")

    slugs = list_template_slugs(sb)
    if not slugs:
        st.warning("먼저 Messaging Templates에서 템플릿을 만드세요.")
        return

    col1, col2 = st.columns(2)
    with col1:
        slug = st.selectbox("템플릿 slug", options=slugs)
    with col2:
        language = st.selectbox(
            "언어",
            options=SUPPORTED_LANGUAGES,
        )

    tpl = get_template(sb, slug, language, "email")
    if not tpl:
        st.warning(
            f"'{slug}' 템플릿의 {language} 버전이 없습니다. "
            "Templates 페이지에서 먼저 만들거나 복제하세요."
        )
        return

    st.markdown(f"**Subject 템플릿:** `{tpl['subject']}`")

    st.divider()
    st.subheader("변수 입력")

    st.caption("비워두면 기본값이 사용됩니다.")
    variables: dict[str, str] = {}
    cols = st.columns(2)
    keys = list(DEFAULT_VARIABLES.keys())
    for i, key in enumerate(keys):
        with cols[i % 2]:
            val = st.text_input(
                key,
                value=DEFAULT_VARIABLES[key],
                key=f"var_{key}",
            )
            variables[key] = val

    st.divider()
    st.subheader("수신 주소")
    to_email = st.text_input(
        "받을 이메일",
        placeholder="you@example.com",
        help="본인 이메일을 입력하세요. 실제 발송됩니다.",
    )

    if st.button("테스트 발송", type="primary"):
        if not to_email or "@" not in to_email:
            st.error("유효한 이메일을 입력하세요.")
            return

        rendered = render_email_preview(
            subject=tpl["subject"],
            body_markdown=tpl["body_markdown"],
            variables=variables,
            language=language,
        )

        with st.spinner("send-email Edge Function 호출 중..."):
            result = _call_send_email(
                env=env,
                to=to_email.strip(),
                subject=rendered["subject"],
                html=rendered["html"],
                text=rendered["text"],
                tags=[f"test-send", slug, language],
            )

        if result.get("ok"):
            st.success(
                f"발송 완료! provider_msg_id: `{result.get('provider_msg_id', '—')}`"
            )
        else:
            st.error(f"발송 실패: {result.get('error', 'unknown')}")

    st.divider()
    with st.expander("현재 렌더링 결과 미리보기"):
        import streamlit.components.v1 as components

        rendered = render_email_preview(
            subject=tpl["subject"],
            body_markdown=tpl["body_markdown"],
            variables=variables,
            language=language,
        )
        st.markdown(f"**Subject:** {rendered['subject']}")
        components.html(rendered["html"], height=600, scrolling=True)


def _call_send_email(
    *,
    env: str,
    to: str,
    subject: str,
    html: str,
    text: str,
    tags: list[str],
) -> dict:
    """Invoke the send-email Edge Function in direct (non-outbox) mode."""
    url = get_supabase_url(env)
    key = get_service_role_key(env)
    if not url or not key:
        return {"ok": False, "error": f"{env} 환경변수 누락"}

    endpoint = f"{url}/functions/v1/send-email"
    payload = {
        "to": to,
        "subject": subject,
        "html": html,
        "text": text,
        "tags": tags,
    }

    try:
        resp = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=30,
        )
    except requests.RequestException as e:
        return {"ok": False, "error": f"Network error: {e}"}

    try:
        data = resp.json()
    except ValueError:
        return {"ok": False, "error": f"{resp.status_code}: {resp.text[:500]}"}

    if resp.status_code == 200:
        return {
            "ok": True,
            "provider_msg_id": data.get("provider_msg_id"),
        }
    return {"ok": False, "error": data.get("error") or f"HTTP {resp.status_code}"}


main()
