"""CRUD helpers for the messaging_center tables."""

from __future__ import annotations

import re
from typing import Any, Optional

from supabase import Client


SUPPORTED_LANGUAGES = ["en", "es", "fr", "ko"]
SUPPORTED_CHANNELS = ["email", "push"]
TRIGGER_TYPES = ["event", "scheduled_relative", "cron"]
KNOWN_EVENT_NAMES = ["profile_created"]
KNOWN_RELATIVE_FIELDS = ["subscription_expires_at", "created_at"]
AUDIENCE_FIELDS = [
    "subscription_tier",
    "subscription_period_type",
    "subscription_plan_type",
    "language_preference",
    "marketing_opt_in",
]

# ---------------------------------------------------------------------------
# Fixed conditions for the simplified Messaging page.
#
# The messaging center DB schema is still generic (templates × triggers ×
# outbox), but the dashboard now surfaces only these two hardcoded conditions.
# Each one maps to a slug that seed_messaging_templates.sql creates rows for
# in all three languages (en/es/fr). The on/off toggle flips the
# corresponding message_triggers row's is_active.
# ---------------------------------------------------------------------------

FIXED_CONDITION_LANGUAGES = ["en", "es", "fr"]

FIXED_CONDITIONS: list[dict[str, Any]] = [
    {
        "slug": "welcome",
        "label": "가입 환영 이메일",
        "description": "신규 가입 시 즉시 자동 발송 (DB AFTER INSERT 트리거 → trigger-messaging)",
        "trigger_description": "Welcome on profile_created (event)",
        "required_variables": ["first_name", "unsubscribe_url"],
        "dummy_variables": {
            "first_name": "테스트",
            "display_name": "테스트 사용자",
            "email": "test@example.com",
            "unsubscribe_url": "#preview-unsubscribe",
        },
    },
    {
        "slug": "trial_ending_2d",
        "label": "Trial 종료 2일 전",
        "description": "Trial 구독 종료 2일 전 pg_cron으로 자동 발송 (trial 유저만)",
        "trigger_description": "Trial ending in 2 days (scheduled_relative, -2d, 1h window)",
        "required_variables": [
            "first_name",
            "trial_end_date",
            "days_until_expiry",
            "unsubscribe_url",
        ],
        "dummy_variables": {
            "first_name": "테스트",
            "display_name": "테스트 사용자",
            "email": "test@example.com",
            "trial_end_date": "2026-04-17",
            "days_until_expiry": "2",
            "unsubscribe_url": "#preview-unsubscribe",
        },
    },
]

LANGUAGE_LABELS = {
    "en": "🇺🇸 English",
    "es": "🇪🇸 Español",
    "fr": "🇫🇷 Français",
    "ko": "🇰🇷 한국어",
}

# Regex mirroring the Deno edge function's substituteVariables — matches
# {{ var_name }} with optional whitespace.
_VARIABLE_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def list_templates(sb: Client) -> list[dict[str, Any]]:
    resp = (
        sb.table("message_templates")
        .select("*")
        .order("slug", desc=False)
        .order("language", desc=False)
        .execute()
    )
    return resp.data or []


def list_template_slugs(sb: Client) -> list[str]:
    rows = list_templates(sb)
    seen: list[str] = []
    for row in rows:
        if row["slug"] not in seen:
            seen.append(row["slug"])
    return seen


def get_template(
    sb: Client, slug: str, language: str, channel: str = "email"
) -> Optional[dict[str, Any]]:
    resp = (
        sb.table("message_templates")
        .select("*")
        .eq("slug", slug)
        .eq("language", language)
        .eq("channel", channel)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def upsert_template(
    sb: Client,
    *,
    slug: str,
    language: str,
    channel: str,
    subject: str,
    body_markdown: str,
    body_html: str,
    variables: list[str],
    is_active: bool = True,
) -> dict[str, Any]:
    """Insert or update a template by (slug, language, channel)."""
    payload = {
        "slug": slug.strip(),
        "language": language,
        "channel": channel,
        "subject": subject,
        "body_markdown": body_markdown,
        "body_html": body_html,
        "variables": variables,
        "is_active": is_active,
    }
    resp = (
        sb.table("message_templates")
        .upsert(payload, on_conflict="slug,language,channel")
        .execute()
    )
    return (resp.data or [{}])[0]


def delete_template(
    sb: Client, *, slug: str, language: str, channel: str
) -> None:
    sb.table("message_templates").delete().eq("slug", slug).eq(
        "language", language
    ).eq("channel", channel).execute()


# ---------------------------------------------------------------------------
# Triggers
# ---------------------------------------------------------------------------


def list_triggers(sb: Client) -> list[dict[str, Any]]:
    resp = (
        sb.table("message_triggers")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def create_trigger(
    sb: Client,
    *,
    name: str,
    template_slug: str,
    channel: str,
    trigger_type: str,
    event_name: Optional[str] = None,
    relative_field: Optional[str] = None,
    relative_offset: Optional[str] = None,
    relative_window: Optional[str] = None,
    audience_filter: Optional[dict[str, Any]] = None,
    is_active: bool = True,
) -> dict[str, Any]:
    payload = {
        "name": name,
        "template_slug": template_slug,
        "channel": channel,
        "trigger_type": trigger_type,
        "event_name": event_name,
        "relative_field": relative_field,
        "relative_offset": relative_offset,
        "relative_window": relative_window,
        "audience_filter": audience_filter or {},
        "is_active": is_active,
    }
    resp = sb.table("message_triggers").insert(payload).execute()
    return (resp.data or [{}])[0]


def update_trigger(
    sb: Client, trigger_id: str, patch: dict[str, Any]
) -> dict[str, Any]:
    resp = (
        sb.table("message_triggers")
        .update(patch)
        .eq("id", trigger_id)
        .execute()
    )
    return (resp.data or [{}])[0]


def delete_trigger(sb: Client, trigger_id: str) -> None:
    sb.table("message_triggers").delete().eq("id", trigger_id).execute()


# ---------------------------------------------------------------------------
# Outbox
# ---------------------------------------------------------------------------


def list_outbox(
    sb: Client,
    *,
    status: Optional[str] = None,
    template_slug: Optional[str] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    query = (
        sb.table("messaging_outbox")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status and status != "all":
        query = query.eq("status", status)
    if template_slug:
        query = query.eq("template_slug", template_slug)
    resp = query.execute()
    return resp.data or []


def reset_outbox_to_pending(sb: Client, outbox_id: str) -> None:
    """Re-queue a failed outbox row."""
    sb.table("messaging_outbox").update(
        {
            "status": "pending",
            "attempts": 0,
            "last_error": None,
        }
    ).eq("id", outbox_id).execute()


def outbox_metrics(sb: Client) -> dict[str, int]:
    """Quick metrics for the Outbox page header."""
    pending = (
        sb.table("messaging_outbox")
        .select("id", count="exact")
        .eq("status", "pending")
        .execute()
        .count
        or 0
    )
    # 'Today' is approximate; we just count rows since midnight UTC.
    from datetime import datetime, timezone

    midnight = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    since_iso = midnight.isoformat()
    sent_today = (
        sb.table("messaging_outbox")
        .select("id", count="exact")
        .eq("status", "sent")
        .gte("sent_at", since_iso)
        .execute()
        .count
        or 0
    )
    failed_today = (
        sb.table("messaging_outbox")
        .select("id", count="exact")
        .eq("status", "failed")
        .gte("created_at", since_iso)
        .execute()
        .count
        or 0
    )
    return {
        "pending": pending,
        "sent_today": sent_today,
        "failed_today": failed_today,
    }


# ---------------------------------------------------------------------------
# Fixed-condition helpers (for pages/2_Messaging.py)
# ---------------------------------------------------------------------------


def get_condition_templates(
    sb: Client, slug: str
) -> dict[str, dict[str, Any]]:
    """Return {language: template_row} for one fixed-condition slug.

    Only returns rows that exist — languages without a row are absent from
    the dict so callers can distinguish "never saved" from "saved empty".
    """
    rows = (
        sb.table("message_templates")
        .select("*")
        .eq("slug", slug)
        .eq("channel", "email")
        .execute()
        .data
        or []
    )
    return {row["language"]: row for row in rows}


def get_trigger_active_state(sb: Client, template_slug: str) -> bool:
    """Return True only if EVERY trigger row for this slug is active.

    A slug typically has one row, but if multiple exist they must all be
    active for the card toggle to read as on.
    """
    rows = (
        sb.table("message_triggers")
        .select("is_active")
        .eq("template_slug", template_slug)
        .execute()
        .data
        or []
    )
    if not rows:
        return False
    return all(bool(r["is_active"]) for r in rows)


def set_trigger_active_state(
    sb: Client, template_slug: str, active: bool
) -> None:
    """Flip the is_active flag for every trigger row with this slug."""
    sb.table("message_triggers").update({"is_active": active}).eq(
        "template_slug", template_slug
    ).execute()


def upsert_html_template(
    sb: Client,
    *,
    slug: str,
    language: str,
    subject: str,
    body_html: str,
) -> dict[str, Any]:
    """Save an admin-uploaded HTML template.

    body_markdown is kept as empty string (legacy path unused for these
    slugs); variables array is empty (the edge function's renderEmailFromHtml
    substitutes {{var}} tokens at send time without needing a declaration).
    """
    payload = {
        "slug": slug.strip(),
        "language": language,
        "channel": "email",
        "subject": subject,
        "body_markdown": "",
        "body_html": body_html,
        "variables": [],
        "is_active": True,
    }
    resp = (
        sb.table("message_templates")
        .upsert(payload, on_conflict="slug,language,channel")
        .execute()
    )
    return (resp.data or [{}])[0]


def render_preview_html(body_html: str, dummy_vars: dict[str, str]) -> str:
    """Substitute {{var}} tokens with dummy values for dashboard preview.

    Mirrors the edge function's substituteVariables. Unknown tokens are left
    as-is so the designer can see what will be substituted at send time.
    """

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return dummy_vars.get(key, match.group(0))

    return _VARIABLE_RE.sub(repl, body_html or "")


def validate_html_template(html: str) -> list[str]:
    """Pre-save validation. Returns list of error messages (empty = OK).

    The {{unsubscribe_url}} check is CAN-SPAM / legal compliance — every
    marketing email MUST include an unsubscribe link. Blocking save here
    prevents a broken template from ever reaching production.
    """
    errors: list[str] = []
    if not html or not html.strip():
        errors.append("HTML 본문이 비어있습니다.")
        return errors

    # Accept {{unsubscribe_url}} or {{ unsubscribe_url }} (with whitespace).
    if not _VARIABLE_RE.search(html) or not any(
        m.group(1) == "unsubscribe_url" for m in _VARIABLE_RE.finditer(html)
    ):
        errors.append(
            "HTML에 {{unsubscribe_url}} placeholder가 반드시 포함되어야 합니다 "
            "(CAN-SPAM 준수). <a href=\"{{unsubscribe_url}}\">Unsubscribe</a> 형태로 추가하세요."
        )
    return errors
