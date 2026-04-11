"""Account deletion page — previously the root admin_dashboard.py."""

from __future__ import annotations

import os
import sys

import requests
import streamlit as st
from supabase import Client

# Allow importing lib/* from sibling directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.supabase_client import REVENUECAT_SECRET, get_env_client  # noqa: E402

REVENUECAT_API_URL = "https://api.revenuecat.com/v1/subscribers"
STORAGE_BUCKETS = ["profile-images", "recordings"]


# ---------------------------------------------------------------------------
# User Lookup
# ---------------------------------------------------------------------------


def find_user_by_email(sb: Client, email: str) -> dict | None:
    """Search auth.users by email via admin API."""
    users = sb.auth.admin.list_users()
    for u in users:
        if getattr(u, "email", None) == email:
            return {
                "id": u.id,
                "email": u.email,
                "created_at": getattr(u, "created_at", None),
                "last_sign_in_at": getattr(u, "last_sign_in_at", None),
                "app_metadata": getattr(u, "app_metadata", {}),
                "user_metadata": getattr(u, "user_metadata", {}),
            }
    return None


# ---------------------------------------------------------------------------
# Account Summary
# ---------------------------------------------------------------------------


def get_account_summary(sb: Client, user_id: str) -> dict:
    """Collect row counts across all related tables."""
    summary: dict = {}

    resp = (
        sb.table("profiles")
        .select("id, email, display_name, subscription_tier, created_at")
        .eq("id", user_id)
        .execute()
    )
    summary["profile"] = resp.data[0] if resp.data else None

    resp = (
        sb.table("recipients")
        .select("id, first_name, last_name")
        .eq("user_id", user_id)
        .execute()
    )
    summary["recipients"] = resp.data
    summary["recipients_count"] = len(resp.data)

    resp = (
        sb.table("checkup_schedules")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    summary["schedules_count"] = (
        resp.count if resp.count is not None else len(resp.data)
    )

    resp = (
        sb.table("checkin_logs")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    summary["logs_count"] = (
        resp.count if resp.count is not None else len(resp.data)
    )

    resp = (
        sb.table("analytics_events")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    summary["analytics_count"] = (
        resp.count if resp.count is not None else len(resp.data)
    )

    resp = (
        sb.table("app_logs")
        .select("id", count="exact")
        .eq("profile_id", user_id)
        .execute()
    )
    summary["app_logs_count"] = (
        resp.count if resp.count is not None else len(resp.data)
    )

    resp = (
        sb.table("legal_consents")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    summary["consents_count"] = (
        resp.count if resp.count is not None else len(resp.data)
    )

    for bucket in STORAGE_BUCKETS:
        try:
            files = sb.storage.from_(bucket).list(user_id)
            summary[f"storage_{bucket}"] = len(files) if files else 0
        except Exception:
            summary[f"storage_{bucket}"] = 0

    return summary


# ---------------------------------------------------------------------------
# Deletion Functions
# ---------------------------------------------------------------------------


def delete_storage_files(sb: Client, bucket: str, user_id: str) -> int:
    try:
        files = sb.storage.from_(bucket).list(user_id)
        if not files:
            return 0
        paths = [f"{user_id}/{f['name']}" for f in files]
        sb.storage.from_(bucket).remove(paths)
        return len(paths)
    except Exception as e:
        st.warning(f"Storage ({bucket}) 삭제 실패: {e}")
        return 0


def delete_table_rows(sb: Client, table: str, column: str, user_id: str) -> int:
    try:
        resp = sb.table(table).delete().eq(column, user_id).execute()
        return len(resp.data) if resp.data else 0
    except Exception as e:
        st.warning(f"{table} 삭제 실패: {e}")
        return 0


def delete_revenuecat_subscriber(app_user_id: str) -> bool:
    if not REVENUECAT_SECRET:
        st.warning("REVENUECAT_V1_SECRET_KEY가 설정되지 않았습니다. 건너뜁니다.")
        return False
    try:
        resp = requests.delete(
            f"{REVENUECAT_API_URL}/{app_user_id}",
            headers={
                "Authorization": f"Bearer {REVENUECAT_SECRET}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if resp.status_code in (200, 204):
            return True
        if resp.status_code == 404:
            st.info("RevenueCat에 해당 구독자가 없습니다.")
            return True
        st.warning(f"RevenueCat 삭제 응답: {resp.status_code} — {resp.text}")
        return False
    except Exception as e:
        st.warning(f"RevenueCat API 호출 실패: {e}")
        return False


def delete_account(sb: Client, user_id: str, progress_callback) -> dict:
    """Execute the full account deletion sequence."""
    results: dict = {}

    progress_callback(1, 5, "Storage 파일 삭제 중...")
    for bucket in STORAGE_BUCKETS:
        count = delete_storage_files(sb, bucket, user_id)
        results[f"storage_{bucket}"] = count

    progress_callback(2, 5, "analytics_events 삭제 중...")
    results["analytics_events"] = delete_table_rows(
        sb, "analytics_events", "user_id", user_id
    )

    progress_callback(3, 5, "app_logs 삭제 중...")
    results["app_logs"] = delete_table_rows(sb, "app_logs", "profile_id", user_id)

    progress_callback(4, 5, "RevenueCat 구독자 삭제 중...")
    results["revenuecat"] = delete_revenuecat_subscriber(user_id)

    progress_callback(5, 5, "Auth 사용자 삭제 중 (CASCADE)...")
    try:
        sb.auth.admin.delete_user(user_id)
        results["auth_user"] = True
    except Exception as e:
        results["auth_user"] = False
        st.error(f"Auth 사용자 삭제 실패: {e}")

    return results


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(
        page_title="Account Deletion",
        page_icon=":wastebasket:",
        layout="wide",
    )
    st.title("Sloth Care — Account Deletion")

    env, sb = get_env_client()

    # --- Search ---
    st.subheader("1. 사용자 검색")
    email = st.text_input("이메일 주소", placeholder="user@example.com")

    if st.button("검색", type="primary"):
        if not email or "@" not in email:
            st.warning("유효한 이메일을 입력하세요.")
        else:
            with st.spinner("사용자 검색 중..."):
                user = find_user_by_email(sb, email.strip())
            if user:
                st.session_state["user"] = user
                with st.spinner("데이터 집계 중..."):
                    st.session_state["summary"] = get_account_summary(
                        sb, user["id"]
                    )
                st.session_state["deleted"] = False
            else:
                st.session_state.pop("user", None)
                st.session_state.pop("summary", None)
                st.error(f"'{email}' 사용자를 찾을 수 없습니다.")

    if "user" not in st.session_state:
        return

    user = st.session_state["user"]
    summary = st.session_state.get("summary", {})

    st.divider()
    st.subheader("2. 사용자 정보")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**User ID:** `{user['id']}`")
        st.markdown(f"**Email:** {user['email']}")
        profile = summary.get("profile")
        if profile:
            st.markdown(
                f"**Display Name:** {profile.get('display_name', '—')}"
            )
            st.markdown(
                f"**Subscription:** {profile.get('subscription_tier', '—')}"
            )
    with col2:
        st.markdown(f"**Created:** {user.get('created_at', '—')}")
        st.markdown(f"**Last Sign-in:** {user.get('last_sign_in_at', '—')}")
        st.markdown(
            f"**Environment:** :{'green' if env == 'QA' else 'red'}[{env}]"
        )

    st.divider()
    st.subheader("3. 데이터 요약")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Recipients", summary.get("recipients_count", 0))
    col2.metric("Schedules", summary.get("schedules_count", 0))
    col3.metric("Check-in Logs", summary.get("logs_count", 0))
    col4.metric("Legal Consents", summary.get("consents_count", 0))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Analytics Events", summary.get("analytics_count", 0))
    col2.metric("App Logs", summary.get("app_logs_count", 0))
    col3.metric("Profile Images", summary.get("storage_profile-images", 0))
    col4.metric("Recordings", summary.get("storage_recordings", 0))

    if summary.get("recipients"):
        with st.expander("Recipients 상세"):
            for r in summary["recipients"]:
                st.text(
                    f"  - {r.get('first_name', '')} {r.get('last_name', '')} (id: {r['id']})"
                )

    if st.session_state.get("deleted"):
        st.success("계정이 성공적으로 삭제되었습니다.")
        return

    st.divider()
    st.subheader("4. 계정 삭제")

    if env == "Prod":
        st.warning(
            "**Prod 환경**입니다. 삭제된 데이터는 복구할 수 없습니다."
        )

    confirm_email = st.text_input(
        "삭제 확인을 위해 이메일을 다시 입력하세요",
        placeholder=user["email"],
        key="confirm_email",
    )

    if st.button("DELETE ACCOUNT", type="primary", use_container_width=True):
        if confirm_email != user["email"]:
            st.error("이메일이 일치하지 않습니다.")
            return

        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress_callback(step: int, total: int, message: str) -> None:
            progress_bar.progress(step / total)
            status_text.text(f"[{step}/{total}] {message}")

        results = delete_account(sb, user["id"], progress_callback)

        progress_bar.progress(1.0)
        status_text.text("완료!")

        st.divider()
        st.subheader("삭제 결과")

        for key, value in results.items():
            if isinstance(value, bool):
                st.markdown(
                    f"- **{key}**: {'성공' if value else '실패'}"
                )
            else:
                st.markdown(f"- **{key}**: {value}건 삭제")

        if results.get("auth_user"):
            st.session_state["deleted"] = True
            st.success(
                f"계정 삭제 완료: {user['email']} ({env})"
            )
        else:
            st.error(
                "Auth 사용자 삭제에 실패했습니다. Supabase Dashboard에서 확인하세요."
            )


main()
