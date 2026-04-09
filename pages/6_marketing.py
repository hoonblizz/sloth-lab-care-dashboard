"""Marketing Insights — recipient geography, engagement health, timing, latency."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from lib.queries import (
    get_recipient_geography,
    get_checkup_timing,
    get_user_health,
    get_inactive_users,
    get_user_engagement_segments,
    get_response_latency,
)
from lib.charts import pie_chart, bar_chart, timing_heatmap, heatmap_table, COLORS
from lib.i18n import t, inject_custom_css, sidebar_language_toggle
from lib.filters import (
    sidebar_filters,
    get_internal_user_ids,
)

inject_custom_css()

# Sidebar (no date picker on this page)
sidebar_language_toggle()
sidebar_filters()

st.title(t("marketing_title"))

exclude_ids = tuple(get_internal_user_ids()) if st.session_state.get("exclude_internal") else ()

# ==========================================================================
# 1. Market Distribution
# ==========================================================================

st.header(t("market_distribution"))
st.caption(t("section_desc_market"))

df_geo = get_recipient_geography(exclude_user_ids=exclude_ids)
if not df_geo.empty:
    c1, c2 = st.columns(2)
    with c1:
        fig = pie_chart(df_geo, names="country", values="recipient_count",
                        title=t("chart_geo"))
        st.plotly_chart(fig, width="stretch")
    with c2:
        display = df_geo.copy()
        display.columns = [t("country"), t("code"), t("total"), t("active")]
        st.dataframe(display, width="stretch", hide_index=True)
else:
    st.info(t("no_recipient_data"))

# ==========================================================================
# 2. Engagement Health
# ==========================================================================

st.divider()
st.header(t("engagement_health"))
st.caption(t("section_desc_engagement_health"))

# --- Inactive user alert cards ---
inactive = get_inactive_users(exclude_user_ids=exclude_ids)
if inactive:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("inactive_7d"), inactive.get("inactive_7d", 0),
              help=t("desc_inactive_7d"))
    c2.metric(t("inactive_14d"), inactive.get("inactive_14d", 0),
              help=t("desc_inactive_14d"))
    c3.metric(t("inactive_30d"), inactive.get("inactive_30d", 0),
              help=t("desc_inactive_30d"))
    at_risk = inactive.get("at_risk_premium", 0)
    c4.metric(t("at_risk_premium"), at_risk,
              help=t("desc_at_risk_premium"))
    if at_risk and at_risk > 0:
        st.warning(t("at_risk_warning").format(count=at_risk))

# --- Engagement segments ---
st.subheader(t("user_segments"))
st.caption(t("section_desc_segments"))
df_seg = get_user_engagement_segments(exclude_user_ids=exclude_ids)
if not df_seg.empty:
    c1, c2 = st.columns(2)
    with c1:
        fig = bar_chart(df_seg, x="segment", y="user_count",
                        title=t("chart_segments"))
        st.plotly_chart(fig, width="stretch")
    with c2:
        display = df_seg.copy()
        display.columns = [t("segment"), t("users"), t("premium_col"), t("pct_premium")]
        st.dataframe(display, width="stretch", hide_index=True)
else:
    st.info(t("no_segment_data"))

# --- User health table ---
st.subheader(t("user_health_scores"))
st.caption(t("section_desc_health_scores"))
df_health = get_user_health(exclude_user_ids=exclude_ids)
if not df_health.empty:
    # Filters
    fc1, fc2 = st.columns(2)
    with fc1:
        status_filter = st.multiselect(
            t("health_status"), ["active", "at_risk", "churned"],
            default=["active", "at_risk", "churned"],
        )
    with fc2:
        tier_filter = st.multiselect(
            t("tier"), ["free", "premium"],
            default=["free", "premium"],
        )

    filtered = df_health[
        df_health["health_status"].isin(status_filter) &
        df_health["tier"].isin(tier_filter)
    ].copy()

    # Color-code health status
    def _status_icon(s):
        if s == "active":
            return t("status_active")
        elif s == "at_risk":
            return t("status_at_risk")
        return t("status_churned")

    filtered["health_status"] = filtered["health_status"].apply(_status_icon)
    display = filtered[["email", "tier", "days_since_active",
                         "total_checkups", "response_rate", "health_status"]].copy()
    display.columns = [t("email"), t("tier"), t("days_inactive"),
                       t("checkups"), t("response_pct"), t("status")]

    st.dataframe(display, width="stretch", hide_index=True,
                 height=min(400, 40 + 35 * len(display)))

    with st.expander(t("download")):
        st.download_button(t("download_csv"), display.to_csv(index=False),
                           "user_health.csv", "text/csv")
else:
    st.info(t("no_health_data"))

# ==========================================================================
# 3. Timing Optimization
# ==========================================================================

st.divider()
st.header(t("timing_optimization"))

# --- Day x Hour heatmap ---
st.subheader(t("response_by_day_hour"))
st.caption(t("section_desc_timing"))
df_timing = get_checkup_timing(exclude_user_ids=exclude_ids)
if not df_timing.empty:
    fig = timing_heatmap(df_timing, x="hour_utc", y="day_name", z="response_rate",
                         title=t("chart_timing"))
    st.plotly_chart(fig, width="stretch")

    # Find best time
    if "response_rate" in df_timing.columns:
        best = df_timing.loc[df_timing["response_rate"].idxmax()]
        st.success(t("best_time").format(
            day=best["day_name"],
            hour=int(best["hour_utc"]),
            rate=best["response_rate"],
            total=int(best["total"]),
            responded=int(best["responded"]),
        ))
else:
    st.info(t("no_timing_data"))

# --- Response latency ---
st.subheader(t("response_latency"))
st.caption(t("section_desc_latency"))
df_latency = get_response_latency(exclude_user_ids=exclude_ids)
if not df_latency.empty:
    c1, c2 = st.columns(2)
    with c1:
        display = df_latency.copy()
        display.columns = [t("type_col"), t("responded_col"), t("avg_min"),
                           t("median_min"), t("p90_min")]
        st.dataframe(display, width="stretch", hide_index=True)
    with c2:
        fig = bar_chart(df_latency, x="checkup_type", y="avg_minutes",
                        title=t("chart_latency"))
        st.plotly_chart(fig, width="stretch")
else:
    st.info(t("no_latency_data"))

# ==========================================================================
# 4. Actionable Insights
# ==========================================================================

st.divider()
st.header(t("actionable_insights"))
st.caption(t("section_desc_insights"))

insights = []

# Churn risk
if inactive:
    at_risk = inactive.get("at_risk_premium", 0)
    if at_risk and at_risk > 0:
        insights.append(t("insight_churn").format(count=at_risk))

# Best timing
if not df_timing.empty and "response_rate" in df_timing.columns and len(df_timing) > 0:
    best = df_timing.loc[df_timing["response_rate"].idxmax()]
    insights.append(t("insight_timing").format(
        day=best["day_name"],
        hour=int(best["hour_utc"]),
        rate=best["response_rate"],
    ))

# Call vs SMS latency
if not df_latency.empty and len(df_latency) >= 2:
    call_row = df_latency[df_latency["checkup_type"] == "call"]
    sms_row = df_latency[df_latency["checkup_type"] == "sms"]
    if not call_row.empty and not sms_row.empty:
        call_avg = call_row.iloc[0]["avg_minutes"]
        sms_avg = sms_row.iloc[0]["avg_minutes"]
        winner = t("call_faster") if call_avg < sms_avg else t("sms_faster")
        insights.append(t("insight_call_sms").format(
            call_avg=call_avg, sms_avg=sms_avg, winner=winner,
        ))

# Market concentration
if not df_geo.empty and len(df_geo) > 0:
    top = df_geo.iloc[0]
    total = df_geo["recipient_count"].sum()
    pct = round(top["recipient_count"] / total * 100, 1) if total > 0 else 0
    insights.append(t("insight_market").format(
        pct=pct, country=top["country"], count=len(df_geo),
    ))

# Engagement segments
if not df_seg.empty:
    dormant = df_seg[df_seg["segment"] == "Dormant"]
    if not dormant.empty:
        dormant_count = int(dormant.iloc[0]["user_count"])
        total_users = int(df_seg["user_count"].sum())
        if total_users > 0:
            dormant_pct = round(dormant_count / total_users * 100, 1)
            insights.append(t("insight_dormant").format(
                pct=dormant_pct, count=dormant_count,
            ))

if insights:
    for insight in insights:
        st.markdown(insight)
else:
    st.info(t("no_insights"))
