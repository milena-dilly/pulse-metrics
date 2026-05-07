"""
ai_insights.py — AI Insights Engine
─────────────────────────────────────
Tries Claude first. Falls back to rule-based if no API key.
Context is always sourced from dbt marts via the callers in routers/insights.py.
"""

import os
import json
import logging
from typing import Optional

log = logging.getLogger("ai_insights")


# ── Schemas (returned as plain dicts for flexibility) ─────────────────────────

def _insight(type_: str, title: str, body: str, metric: Optional[str] = None) -> dict:
    return {"type": type_, "title": title, "body": body, "metric": metric}


# ── Rule-based fallback ───────────────────────────────────────────────────────

def _rule_based(
    kpi_context: list[dict],
    at_risk_count: int,
    funnel_data: list[dict],
    month: str,
) -> dict:
    latest = kpi_context[0] if kpi_context else {}
    prev   = kpi_context[1] if len(kpi_context) > 1 else {}

    insights = []
    summary_parts = []

    # ── MoM growth ────────────────────────────────────────────
    mom = latest.get("mrr_mom_pct") or 0.0
    if mom >= 5:
        insights.append(_insight(
            "positive", "Strong MRR Growth",
            f"MRR grew {mom:.1f}% month-over-month — top-line momentum is healthy. "
            f"Net new MRR reached ${latest.get('net_new_mrr', 0):,.0f}, driven by new and expansion revenue.",
            f"+{mom:.1f}% MoM",
        ))
        summary_parts.append(f"MRR grew {mom:.1f}% MoM.")
    elif mom < 0:
        insights.append(_insight(
            "warning", "MRR Declined This Month",
            f"MRR contracted {abs(mom):.1f}% MoM. "
            "Review churn drivers and identify contraction accounts for CSM intervention.",
            f"{mom:.1f}% MoM",
        ))
        summary_parts.append(f"MRR declined {abs(mom):.1f}% — needs attention.")
    else:
        insights.append(_insight(
            "neutral", "Stable Revenue",
            f"MRR is flat with {mom:+.1f}% MoM change. "
            "Focus on expansion plays with high-health accounts to accelerate growth.",
            f"{mom:+.1f}% MoM",
        ))

    # ── Churn rate ────────────────────────────────────────────
    churn = latest.get("churn_rate", 0)
    prev_churn = prev.get("churn_rate", churn)
    churn_delta = churn - prev_churn

    if churn > 5:
        insights.append(_insight(
            "warning", "Elevated Churn Rate",
            f"Monthly churn hit {churn:.1f}% (+{churn_delta:.1f}pp vs prior month). "
            "Industry benchmark is <3%. Trigger save-the-customer playbooks immediately.",
            f"{churn:.1f}% churn",
        ))
        summary_parts.append(f"Churn at {churn:.1f}% is above benchmark.")
    elif churn < 2:
        insights.append(_insight(
            "positive", "Churn Well Under Control",
            f"Churn rate of {churn:.1f}% is below industry average. "
            "Customer success programs are performing — consider scaling what's working.",
            f"{churn:.1f}% churn",
        ))

    # ── NRR ───────────────────────────────────────────────────
    nrr = latest.get("nrr", 100)
    if nrr >= 110:
        insights.append(_insight(
            "positive", "Net Revenue Retention Above 110%",
            f"NRR of {nrr:.1f}% means existing customers expand faster than you lose "
            "revenue to churn — a hallmark of top-quartile SaaS companies.",
            f"NRR {nrr:.1f}%",
        ))
        summary_parts.append(f"NRR of {nrr:.1f}% is exceptional.")
    elif nrr < 95:
        insights.append(_insight(
            "warning", "NRR Below 100% — Leaky Bucket",
            f"NRR of {nrr:.1f}% means you're losing more revenue from existing customers "
            "than you're expanding. Prioritise upsell and seat expansion plays.",
            f"NRR {nrr:.1f}%",
        ))

    # ── At-risk customers ─────────────────────────────────────
    if at_risk_count > 0:
        insights.append(_insight(
            "warning", f"{at_risk_count} At-Risk Accounts",
            f"{at_risk_count} active customers have a health score below 40. "
            "These accounts represent potential churn in the next 30–60 days. "
            "Assign CSM outreach immediately.",
            f"{at_risk_count} accounts",
        ))

    # ── Funnel conversion ──────────────────────────────────────
    if funnel_data and len(funnel_data) >= 2:
        top = funnel_data[0]["count"]
        bottom = funnel_data[-1]["count"]
        if top:
            overall_conv = round(bottom / top * 100, 1)
            if overall_conv < 2:
                insights.append(_insight(
                    "warning", "Low Funnel Conversion",
                    f"Overall funnel conversion is {overall_conv:.1f}% "
                    f"({bottom:,} paid from {top:,} top-of-funnel). "
                    "Investigate drop-off between SQL and Trial stages.",
                    f"{overall_conv:.1f}% conversion",
                ))
            elif overall_conv >= 5:
                insights.append(_insight(
                    "positive", "Strong Funnel Performance",
                    f"Overall conversion of {overall_conv:.1f}% is healthy. "
                    "Consider increasing top-of-funnel investment to compound paid growth.",
                    f"{overall_conv:.1f}% conversion",
                ))

    if not summary_parts:
        summary_parts.append("Revenue metrics are within normal operating ranges.")

    return {
        "month": month,
        "summary": " ".join(summary_parts),
        "insights": insights,
        "generated_by": "rule-based",
    }


# ── LLM (Claude) ──────────────────────────────────────────────────────────────

def _llm_insights(
    kpi_context: list[dict],
    at_risk_count: int,
    funnel_data: list[dict],
    month: str,
) -> Optional[dict]:
    try:
        import anthropic
        client = anthropic.Anthropic()

        context = {
            "kpi_last_3_months": kpi_context,
            "at_risk_customers": at_risk_count,
            "funnel_latest": funnel_data,
        }

        prompt = f"""You are a SaaS revenue analyst presenting to the executive team.

Analyze this data from our analytics platform (sourced from dbt marts):

{json.dumps(context, indent=2, default=str)}

Return ONLY valid JSON in this exact shape — no markdown, no preamble:
{{
  "summary": "<2-sentence executive summary>",
  "insights": [
    {{
      "type": "positive|warning|neutral",
      "title": "<short title, max 6 words>",
      "body": "<2-3 sentences, specific numbers, actionable recommendation>",
      "metric": "<key metric e.g. +8.2% MoM>"
    }}
  ],
  "generated_by": "llm"
}}

Rules:
- Generate 3-5 insights
- Use exact numbers from the data
- Be actionable, not just descriptive
- Flag risks before opportunities
- month context: {month}"""

        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()
        parsed = json.loads(raw)
        parsed["month"] = month
        return parsed

    except Exception as e:
        log.warning(f"LLM call failed ({e}), falling back to rule-based.")
        return None


# ── Public entrypoint ─────────────────────────────────────────────────────────

def generate_insights(
    kpi_context: list[dict],
    at_risk_count: int,
    funnel_data: list[dict],
    month: str,
) -> dict:
    """Try LLM first, fall back to deterministic rules."""
    if os.getenv("ANTHROPIC_API_KEY"):
        result = _llm_insights(kpi_context, at_risk_count, funnel_data, month)
        if result:
            return result
    return _rule_based(kpi_context, at_risk_count, funnel_data, month)
