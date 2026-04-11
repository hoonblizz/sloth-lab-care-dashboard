"""Messaging — two fixed conditions (welcome + trial_ending_2d).

This page replaces the generic Templates/Triggers CRUD. The DB schema is
still generic, but operationally we only surface:

  1. Welcome email — fires on profile_created (DB trigger → trigger-messaging)
  2. Trial ending in 2 days — fires 2 days before trial expiry (pg_cron)

Each condition is a card with:
  - language tabs (EN / ES / FR)
  - subject input + HTML file upload + preview
  - on/off toggle mapped to message_triggers.is_active
  - save button with {{unsubscribe_url}} validation
"""

from __future__ import annotations

import os
import sys

import streamlit as st
import streamlit.components.v1 as components

# Allow importing from sibling lib/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.messaging import (  # noqa: E402
    FIXED_CONDITION_LANGUAGES,
    FIXED_CONDITIONS,
    LANGUAGE_LABELS,
    get_condition_templates,
    get_trigger_active_state,
    render_preview_html,
    set_trigger_active_state,
    upsert_html_template,
    validate_html_template,
)
from lib.supabase_client import get_env_client  # noqa: E402


def _render_language_tab(
    sb,
    *,
    condition: dict,
    language: str,
    existing_row: dict | None,
) -> None:
    """Render the editor for one (condition, language) pair."""
    slug = condition["slug"]
    state_key_prefix = f"msg_{slug}_{language}"

    existing_subject = (existing_row or {}).get("subject", "") or ""
    existing_html = (existing_row or {}).get("body_html", "") or ""

    # --- Subject ---
    subject = st.text_input(
        "Subject",
        value=existing_subject,
        key=f"{state_key_prefix}_subject",
        placeholder="예) Welcome to Sloth Care, {{first_name}}!",
        help="이메일 제목. {{first_name}} 등 변수 치환 가능.",
    )

    # --- HTML upload ---
    uploaded = st.file_uploader(
        "HTML 파일 업로드",
        type=["html", "htm"],
        key=f"{state_key_prefix}_upload",
        help=(
            "전체 이메일 HTML 파일. {{first_name}}, {{trial_end_date}}, "
            "{{days_until_expiry}}, {{unsubscribe_url}} 같은 placeholder를 "
            "포함할 수 있습니다. {{unsubscribe_url}}은 필수입니다 (CAN-SPAM)."
        ),
    )

    if uploaded is not None:
        try:
            uploaded_bytes = uploaded.read()
            new_html = uploaded_bytes.decode("utf-8")
            st.session_state[f"{state_key_prefix}_html"] = new_html
            st.success(
                f"파일 로드됨: `{uploaded.name}` ({len(new_html):,} chars). "
                "저장하려면 아래 '저장' 버튼을 눌러주세요."
            )
        except UnicodeDecodeError:
            st.error("UTF-8로 디코딩 실패. HTML 파일이 UTF-8인지 확인하세요.")

    # Working HTML = session_state (upload이 있으면) → 기존 DB 값 fallback
    working_html = st.session_state.get(
        f"{state_key_prefix}_html", existing_html
    )

    # --- Preview ---
    if working_html:
        preview_html = render_preview_html(
            working_html, condition["dummy_variables"]
        )
        preview_tab1, preview_tab2 = st.tabs(
            ["미리보기 (변수 치환됨)", "Raw HTML 소스"]
        )
        with preview_tab1:
            st.caption(
                f"더미 변수로 렌더: {', '.join(f'{k}={v}' for k, v in condition['dummy_variables'].items())}"
            )
            components.html(preview_html, height=500, scrolling=True)
        with preview_tab2:
            st.code(working_html, language="html")
    else:
        st.info(
            "아직 HTML이 업로드되지 않았습니다. 위에서 HTML 파일을 업로드하면 미리보기가 나타납니다."
        )

    # --- Save ---
    col_save, col_clear, _ = st.columns([1, 1, 4])

    with col_save:
        if st.button("💾 저장", key=f"{state_key_prefix}_save", type="primary"):
            if not subject.strip():
                st.error("Subject를 입력해주세요.")
                return
            if not working_html:
                st.error("HTML 본문이 비어있습니다. 먼저 파일을 업로드하세요.")
                return

            errors = validate_html_template(working_html)
            if errors:
                for err in errors:
                    st.error(err)
                return

            try:
                upsert_html_template(
                    sb,
                    slug=slug,
                    language=language,
                    subject=subject.strip(),
                    body_html=working_html,
                )
                # Clear the session-state override so the next render reads
                # the canonical value back from the DB. Prevents stale
                # "파일 로드됨" banner from lingering after a successful save.
                st.session_state.pop(f"{state_key_prefix}_html", None)
                st.success(
                    f"저장 완료: `{slug}` / `{language}` ({len(working_html):,} chars)"
                )
                st.rerun()
            except Exception as exc:  # pragma: no cover — display only
                st.error(f"저장 실패: {exc}")

    with col_clear:
        if working_html and st.button(
            "🗑 업로드 취소",
            key=f"{state_key_prefix}_clear",
            help="업로드한 HTML을 초기화하고 DB의 기존 값으로 되돌립니다.",
        ):
            st.session_state.pop(f"{state_key_prefix}_html", None)
            st.rerun()

    # --- Status line ---
    if existing_row:
        updated_at = existing_row.get("updated_at") or existing_row.get("created_at")
        html_len = len(existing_row.get("body_html") or "")
        st.caption(
            f"DB 상태: `{language}` — body_html {html_len:,} chars, "
            f"last updated: {updated_at}"
        )
    else:
        st.caption(f"DB 상태: `{language}` — 아직 저장되지 않음")


def _render_condition_card(sb, condition: dict) -> None:
    slug = condition["slug"]

    with st.container(border=True):
        header_col, toggle_col = st.columns([5, 2])

        with header_col:
            st.subheader(condition["label"])
            st.caption(condition["description"])
            st.caption(f"Trigger: `{condition['trigger_description']}`")

        with toggle_col:
            current_active = get_trigger_active_state(sb, slug)
            new_active = st.toggle(
                "발송 활성화",
                value=current_active,
                key=f"toggle_{slug}",
                help=(
                    "ON일 때만 이 조건에 해당하는 이메일이 발송됩니다. "
                    "OFF로 하면 trigger-messaging이 이 조건을 건너뜁니다."
                ),
            )
            if new_active != current_active:
                try:
                    set_trigger_active_state(sb, slug, new_active)
                    state_word = "활성화" if new_active else "비활성화"
                    st.success(f"{state_word}됨")
                    st.rerun()
                except Exception as exc:  # pragma: no cover — display only
                    st.error(f"토글 실패: {exc}")

        st.markdown("---")

        # Required variable hint.
        required_vars = ", ".join(
            f"`{{{{{v}}}}}`" for v in condition["required_variables"]
        )
        st.caption(f"**필수 변수**: {required_vars}")

        # Language tabs.
        templates_by_lang = get_condition_templates(sb, slug)

        tab_labels = [LANGUAGE_LABELS[lang] for lang in FIXED_CONDITION_LANGUAGES]
        tabs = st.tabs(tab_labels)

        for tab, language in zip(tabs, FIXED_CONDITION_LANGUAGES):
            with tab:
                _render_language_tab(
                    sb,
                    condition=condition,
                    language=language,
                    existing_row=templates_by_lang.get(language),
                )


def main() -> None:
    st.set_page_config(
        page_title="Messaging",
        page_icon=":envelope:",
        layout="wide",
    )

    st.title("Messaging")

    env, sb = get_env_client()
    st.caption(f"환경: **{env}**")

    st.markdown(
        """
Sloth Care는 현재 **2개의 고정 조건**에서만 자동 이메일을 발송합니다. 각 조건마다
EN/ES/FR 3개 언어의 HTML 파일을 업로드하고, 발송 ON/OFF를 토글할 수 있습니다.

- HTML 파일은 전체 이메일(`<html>...</html>`)이어야 합니다. 별도 base layout으로 감싸지 않습니다.
- `{{first_name}}`, `{{trial_end_date}}`, `{{days_until_expiry}}`, `{{unsubscribe_url}}`은 발송 시점에 치환됩니다.
- `{{unsubscribe_url}}`은 **필수** (CAN-SPAM 준수) — 저장 시 검증됩니다.
        """
    )

    for condition in FIXED_CONDITIONS:
        st.markdown("")
        _render_condition_card(sb, condition)


main()
