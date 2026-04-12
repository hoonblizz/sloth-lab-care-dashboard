"""
Markdown → HTML preview rendering for the Messaging Templates page.

Mirrors the logic of ``supabase/functions/_shared/templating.ts`` closely
enough for operator preview. The actual email sent at runtime is always
rendered by the Edge Function — this module exists only so that the
dashboard can show a faithful preview inside an iframe.
"""

from __future__ import annotations

import html as html_lib
import re
from typing import Mapping


BRAND_NAME = "Sloth Care"
BRAND_TAGLINE = "Stay close to the ones you love"
FOOTER_ADDRESS_DEFAULT = "Sloth Lab Inc. · Vancouver, BC, Canada"

UNSUBSCRIBE_LABELS = {
    "en": "Unsubscribe",
    "es": "Cancelar suscripción",
    "fr": "Se désabonner",
    "ko": "수신 거부",
}

FOOTER_TAGLINES = {
    "en": "You're receiving this because you have a Sloth Care account.",
    "es": "Recibes este correo porque tienes una cuenta de Sloth Care.",
    "fr": "Vous recevez ce message car vous avez un compte Sloth Care.",
    "ko": "Sloth Care 계정을 보유하고 계시기에 이 이메일을 받으셨습니다.",
}

# Kept in lockstep with _shared/email_base.ts
EMAIL_BASE_LAYOUT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{SUBJECT}</title>
<style>
  body {{ margin:0; padding:0; background-color:#FAF6F1; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
  a {{ color:#E57A5F; text-decoration:underline; }}
  @media screen and (max-width: 600px) {{
    .container {{ width: 100% !important; }}
    .px {{ padding-left: 24px !important; padding-right: 24px !important; }}
    h1 {{ font-size: 26px !important; line-height: 32px !important; }}
  }}
</style>
</head>
<body style="margin:0; padding:0; background-color:#FAF6F1;">
<table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" bgcolor="#FAF6F1">
  <tr>
    <td align="center" style="padding:32px 12px;">
      <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="600" class="container" style="max-width:600px; background-color:#FFFFFF; border-radius:16px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.04);">
        <tr>
          <td align="center" bgcolor="#E57A5F" style="padding:32px 24px; background-color:#E57A5F;">
            <div style="color:#FFFFFF; font-size:24px; font-weight:700; letter-spacing:0.5px;">Sloth Care</div>
            <div style="color:#FFEFE9; font-size:13px; margin-top:4px;">Stay close to the ones you love</div>
          </td>
        </tr>
        <tr>
          <td class="px" style="padding:40px 48px; color:#2B2B2B; font-size:16px; line-height:1.6;">
            {BODY}
          </td>
        </tr>
        <tr>
          <td class="px" style="padding:24px 48px 40px 48px; border-top:1px solid #F0E8DF; color:#8A857E; font-size:12px; line-height:1.5; text-align:center;">
            <div style="margin-bottom:8px;">{FOOTER_TAGLINE}</div>
            <div style="margin-bottom:12px;"><a href="{UNSUBSCRIBE_URL}" style="color:#8A857E;">{UNSUBSCRIBE_LABEL}</a></div>
            <div style="color:#B5AFA7;">{FOOTER_ADDRESS}</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


def substitute_variables(template: str, variables: Mapping[str, object]) -> str:
    """Replace ``{{var}}`` tokens with values; leave unknown tokens as-is."""

    def replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in variables:
            return match.group(0)
        value = variables[key]
        if value is None:
            return match.group(0)
        return str(value)

    return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", replace, template)


def _inline_format(escaped: str) -> str:
    """Apply bold / italic / link formatting to an already-escaped line."""

    # Links: [label](http(s)|mailto)
    def link_repl(match: re.Match) -> str:
        label = match.group(1)
        url = match.group(2)
        return f'<a href="{url}" style="color:#E57A5F; text-decoration:underline;">{label}</a>'

    result = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+|mailto:[^)\s]+)\)",
        link_repl,
        escaped,
    )

    # Bold
    result = re.sub(
        r"\*\*([^*]+)\*\*",
        r'<strong style="color:#2B2B2B;">\1</strong>',
        result,
    )

    # Italic (single asterisks that aren't adjacent to another)
    result = re.sub(
        r"(^|[^*])\*([^*\s][^*]*[^*\s]|[^*\s])\*(?!\*)",
        r"\1<em>\2</em>",
        result,
    )

    return result


def markdown_to_html(escaped_markdown: str) -> str:
    """Render a safe subset of markdown to HTML."""
    lines = escaped_markdown.splitlines()
    out: list[str] = []
    in_ul = False
    in_ol = False
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            content = " ".join(paragraph).strip()
            if content:
                out.append(f'<p style="margin:0 0 16px 0;">{content}</p>')
            paragraph = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for raw in lines:
        line = raw.strip()

        if not line:
            flush_paragraph()
            close_lists()
            continue

        if re.match(r"^---+$", line):
            flush_paragraph()
            close_lists()
            out.append(
                '<hr style="border:none; border-top:1px solid #F0E8DF; margin:24px 0;">'
            )
            continue

        h3 = re.match(r"^###\s+(.+)$", line)
        if h3:
            flush_paragraph()
            close_lists()
            out.append(
                f'<h3 style="margin:24px 0 12px 0; font-size:18px; font-weight:700; color:#2B2B2B;">{_inline_format(h3.group(1))}</h3>'
            )
            continue

        h2 = re.match(r"^##\s+(.+)$", line)
        if h2:
            flush_paragraph()
            close_lists()
            out.append(
                f'<h2 style="margin:28px 0 12px 0; font-size:22px; font-weight:700; color:#2B2B2B;">{_inline_format(h2.group(1))}</h2>'
            )
            continue

        h1 = re.match(r"^#\s+(.+)$", line)
        if h1:
            flush_paragraph()
            close_lists()
            out.append(
                f'<h1 style="margin:0 0 20px 0; font-size:28px; font-weight:700; color:#E57A5F; line-height:1.3;">{_inline_format(h1.group(1))}</h1>'
            )
            continue

        ul = re.match(r"^[-*]\s+(.+)$", line)
        if ul:
            flush_paragraph()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append('<ul style="margin:0 0 16px 0; padding-left:20px;">')
                in_ul = True
            out.append(
                f'<li style="margin-bottom:6px;">{_inline_format(ul.group(1))}</li>'
            )
            continue

        ol = re.match(r"^\d+\.\s+(.+)$", line)
        if ol:
            flush_paragraph()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append('<ol style="margin:0 0 16px 0; padding-left:24px;">')
                in_ol = True
            out.append(
                f'<li style="margin-bottom:6px;">{_inline_format(ol.group(1))}</li>'
            )
            continue

        close_lists()
        paragraph.append(_inline_format(line))

    flush_paragraph()
    close_lists()
    return "\n".join(out)


def _normalize_language(language: str) -> str:
    lower = (language or "en").lower()
    if lower.startswith("ko"):
        return "ko"
    if lower.startswith("es"):
        return "es"
    if lower.startswith("fr"):
        return "fr"
    return "en"


def render_email_preview(
    *,
    subject: str,
    body_markdown: str,
    variables: Mapping[str, object],
    language: str,
    unsubscribe_url: str = "https://example.com/unsubscribe?token=preview",
    footer_address: str = FOOTER_ADDRESS_DEFAULT,
) -> dict[str, str]:
    """Render a preview email — returns {subject, html, text}."""
    lang = _normalize_language(language)

    # Escape each variable value before substituting into the body.
    safe_vars: dict[str, str] = {}
    for key, value in variables.items():
        if value is None:
            continue
        safe_vars[key] = html_lib.escape(str(value))

    subject_sub = substitute_variables(subject, variables)
    safe_subject = re.sub(r"[\r\n]+", " ", subject_sub).strip()

    escaped_body = html_lib.escape(body_markdown)
    substituted_body = substitute_variables(escaped_body, safe_vars)
    body_html = markdown_to_html(substituted_body)

    html = EMAIL_BASE_LAYOUT.format(
        SUBJECT=html_lib.escape(safe_subject),
        BODY=body_html,
        UNSUBSCRIBE_URL=html_lib.escape(unsubscribe_url),
        UNSUBSCRIBE_LABEL=html_lib.escape(
            UNSUBSCRIBE_LABELS.get(lang, UNSUBSCRIBE_LABELS["en"])
        ),
        FOOTER_TAGLINE=html_lib.escape(
            FOOTER_TAGLINES.get(lang, FOOTER_TAGLINES["en"])
        ),
        FOOTER_ADDRESS=html_lib.escape(footer_address),
    )

    raw_body_text = substitute_variables(body_markdown, variables)
    text_footer = "\n".join(
        [
            "",
            "---",
            FOOTER_TAGLINES.get(lang, FOOTER_TAGLINES["en"]),
            f"{UNSUBSCRIBE_LABELS.get(lang, UNSUBSCRIBE_LABELS['en'])}: {unsubscribe_url}",
            footer_address,
        ]
    )

    return {
        "subject": safe_subject,
        "html": html,
        "text": f"{raw_body_text}{text_footer}",
    }
