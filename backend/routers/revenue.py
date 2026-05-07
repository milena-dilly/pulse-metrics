"""
routers/revenue.py
──────────────────
Source mart: marts.fact_revenue

fact_revenue contains one row per month with revenue broken down
by movement type (new, expansion, contraction, churn).
"""

from fastapi import APIRouter, Query
from backend.db import query
from backend.models import RevenueTrendRow

router = APIRouter(prefix="/revenue-trend", tags=["Revenue"])

_REVENUE_SELECT = """
    SELECT
        month::VARCHAR                                      AS month,
        SUM(CASE WHEN movement_type = 'new'
                 THEN revenue ELSE 0 END)                  AS new_revenue,
        SUM(CASE WHEN movement_type = 'expansion'
                 THEN revenue ELSE 0 END)                  AS expansion_revenue,
        SUM(CASE WHEN movement_type = 'churn'
                 THEN revenue ELSE 0 END)                  AS churn_revenue,
        SUM(CASE WHEN movement_type != 'churn'
                 THEN revenue ELSE 0 END)                  AS total_revenue,
        SUM(CASE WHEN movement_type IN ('new','expansion')
                 THEN revenue ELSE 0 END)
        - SUM(CASE WHEN movement_type IN ('churn','contraction')
                   THEN revenue ELSE 0 END)                AS net_new_revenue
    FROM marts.fact_revenue
"""

_CUMULATIVE_CTE = """
    WITH base AS (
        {inner}
    )
    SELECT
        *,
        SUM(total_revenue) OVER (ORDER BY month ROWS UNBOUNDED PRECEDING)
            AS cumulative_revenue
    FROM base
"""


@router.get("", response_model=list[RevenueTrendRow], summary="Monthly revenue trend")
def get_revenue_trend(
    from_month:  str  = Query("2023-01", example="2023-01"),
    to_month:    str  = Query("2024-06", example="2024-06"),
    cumulative:  bool = Query(False, description="Include cumulative revenue column"),
):
    """
    Monthly revenue time-series from **marts.fact_revenue**.

    Breaks down revenue into:
    - `new_revenue` — revenue from new customers
    - `expansion_revenue` — upgrades / seat expansions
    - `churn_revenue` — revenue lost to churn
    - `net_new_revenue` — net change (new + expansion − churn − contraction)
    - `total_revenue` — total active MRR
    - `cumulative_revenue` — running total (opt-in via `?cumulative=true`)
    """
    base_sql = (
        f"{_REVENUE_SELECT} "
        f"WHERE month::VARCHAR BETWEEN $1 AND $2 "
        f"GROUP BY month "
        f"ORDER BY month"
    )

    if cumulative:
        sql = _CUMULATIVE_CTE.format(inner=base_sql)
    else:
        sql = base_sql

    rows = query(sql, [from_month, to_month])
    return [RevenueTrendRow(**r) for r in rows]
