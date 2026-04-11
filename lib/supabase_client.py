"""
Shared Supabase client + sidebar environment selector.

Every dashboard page imports :func:`get_env_client` to get a Supabase
client bound to the environment the operator picked in the sidebar.

Secret resolution order (first hit wins):
  1. ``st.secrets[KEY]``         — Streamlit Cloud managed secrets
  2. ``os.environ[KEY]``         — already-exported shell env
  3. ``.env`` via python-dotenv  — local dev fallback

This mirrors the pattern in the analytics dashboard's ``lib/db.py`` so both
modules can coexist inside the deployed ``sloth-lab-care-dashboard`` repo.
"""

from __future__ import annotations

import os
from typing import Optional

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

# Load .env from the project root (two levels up from lib/). Harmless on
# Streamlit Cloud where no .env exists.
load_dotenv()


def _get_secret(key: str) -> str:
    """Return a secret from Streamlit Cloud, env vars, or .env — in that order."""
    # 1. Streamlit Cloud managed secrets. Wrapping in try/except because
    #    st.secrets raises StreamlitSecretNotFoundError / KeyError when the
    #    key is missing OR when no secrets.toml exists at all (local dev).
    try:
        value = st.secrets.get(key)  # type: ignore[attr-defined]
        if value:
            return str(value)
    except (FileNotFoundError, KeyError, AttributeError):
        pass
    except Exception:
        # st.secrets can raise StreamlitSecretNotFoundError which isn't a
        # stable import path; swallow any unexpected failure and fall through.
        pass

    # 2. Shell environment (also picked up from .env above).
    return os.getenv(key, "")


ENV_CONFIG = {
    "QA": {
        "url": _get_secret("QA_SUPABASE_URL"),
        "key": _get_secret("QA_SUPABASE_SERVICE_ROLE_KEY"),
    },
    "Prod": {
        "url": _get_secret("PROD_SUPABASE_URL"),
        "key": _get_secret("PROD_SUPABASE_SERVICE_ROLE_KEY"),
    },
}

REVENUECAT_SECRET = _get_secret("REVENUECAT_V1_SECRET_KEY")


def get_supabase(env: str) -> Client:
    """Return a Supabase client for the given environment or stop the app."""
    cfg = ENV_CONFIG[env]
    if not cfg["url"] or not cfg["key"]:
        st.error(f"{env} 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        st.stop()
    return create_client(cfg["url"], cfg["key"])


def render_env_sidebar() -> str:
    """Render the shared sidebar selector and return the chosen env name.

    Pages should call this at the top of ``main()`` before any other
    Streamlit UI code. The selection is persisted in ``st.session_state``
    across navigation so that moving between pages doesn't reset to QA.
    """
    current = st.session_state.get("env", "QA")
    with st.sidebar:
        st.header("Environment")
        env = st.selectbox(
            "환경 선택",
            ["QA", "Prod"],
            index=0 if current == "QA" else 1,
            key="env_selector",
        )
        st.session_state["env"] = env

        cfg = ENV_CONFIG[env]
        if cfg["url"] and cfg["key"]:
            st.success(f"{env} 연결됨")
        else:
            st.error(f"{env} 환경변수 누락")

        st.divider()
        st.caption(
            f"Supabase: {cfg['url'][:40]}..." if cfg["url"] else "URL 없음"
        )
        st.caption(
            f"RevenueCat: {'설정됨' if REVENUECAT_SECRET else '미설정'}"
        )

    return env


def get_env_client() -> tuple[str, Client]:
    """Shortcut: render sidebar and return (env_name, supabase_client)."""
    env = render_env_sidebar()
    return env, get_supabase(env)


def get_supabase_url(env: Optional[str] = None) -> str:
    """Return the Supabase base URL for the given environment."""
    env = env or st.session_state.get("env", "QA")
    return ENV_CONFIG[env]["url"]


def get_service_role_key(env: Optional[str] = None) -> str:
    """Return the Supabase service role key for the given environment."""
    env = env or st.session_state.get("env", "QA")
    return ENV_CONFIG[env]["key"]
