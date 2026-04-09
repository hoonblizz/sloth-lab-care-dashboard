"""Supabase connection and authentication for the analytics dashboard."""

from __future__ import annotations

import os

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_client() -> Client:
    """Get Supabase client with service_role key (cached)."""
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        st.error("Supabase credentials not configured. Check secrets / .env.")
        st.stop()

    return create_client(url, key)


def rpc(fn_name: str, params: dict | None = None) -> list[dict]:
    """Call a Supabase RPC function and return data rows."""
    sb = get_client()
    try:
        if params:
            result = sb.rpc(fn_name, params).execute()
        else:
            result = sb.rpc(fn_name).execute()
        return result.data or []
    except Exception as e:
        st.error(f"RPC `{fn_name}` failed: {e}")
        return []


def _get_secret(key: str) -> str:
    """Try st.secrets first (Streamlit Cloud), then env vars (local)."""
    try:
        return st.secrets[key]
    except (FileNotFoundError, KeyError):
        pass
    # Fallback: .env file
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
    return os.getenv(key, "")
