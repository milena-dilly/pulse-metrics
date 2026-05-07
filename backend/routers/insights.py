"""
routers/insights.py
───────────────────
Source marts: mart_monthly_growth + fact_revenue + mart_customer_metrics

AI-powered insights using Claude. Falls back to rule-based logic
if ANTHROPIC_API_KEY is not set.
"""

from fastapi import APIRouter, Query
from typing import Optional
from backend.db import query
from backend.ai_insights import generate_insights

router = APIRouter(prefix="/insights", tags=["AI Insights"])


@router.get("", summary="AI-generated executive insights")
def get_insights(
    month: Optional[str] = Query(
        None,
        description="Reference month YYYY-MM. Defaults to latest.",
        example="2024-06",
    )
):
    """
    Generates executive-level insights from dbt mart data.

    Uses **Claude (Anthropic)** when `ANTHROPIC_API_KEY` is set.
    Falls back to deterministic rule-based analysis otherwise.

    Context pulled from:
    - `marts.mart_monthly_growth` — KPI trends (last 3 months)
    - `marts.mart_customer_metrics` — churn risk signals
    - `marts.fct_marketing_funnel` — conversion trends
    """

    # Pull last 3 months of KPIs for context
    kpi_context = query("""
        SELECT
            month::VARCHAR  AS month,
            mrr,
            churn_rate,
            nrr,
            new_customers,
            churned_customers,
            mrr_mom_pct,
            net_new_mrr,
            expansion_mrr
        FROM marts.mart_monthly_growth
        ORDER BY month DESC
        LIMIT 3
    """)

    # Churn risk: customers with low health score still active
    at_risk = query("""
        SELECT COUNT(*) AS count
        FROM marts.mart_customer_metrics
        WHERE status = 'active'
          AND health_score < 40
    """)
    at_risk_count = at_risk[0]["count"] if at_risk else 0

    # Latest funnel conversion
    funnel_conv = query("""
        SELECT
            stage,
            count
        FROM marts.fct_marketing_funnel
        WHERE period = (SELECT MAX(period) FROM marts.fct_marketing_funnel)
        ORDER BY stage_order ASC
    """)

    active_month = kpi_context[0]["month"] if kpi_context else (month or "unknown")

    return generate_insights(
        kpi_context=kpi_context,
        at_risk_count=at_risk_count,
        funnel_data=funnel_conv,
        month=active_month,
    )
