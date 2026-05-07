"""
routers/funnel.py
─────────────────
Source mart: marts.fct_marketing_funnel

fct_marketing_funnel contains one row per stage per period.
We compute conversion rates and drop-off in SQL (dbt might pre-compute
these too — adapt the SELECT if your mart already has them).
"""

from fastapi import APIRouter, Query
from typing import Optional
from backend.db import query
from backend.models import FunnelStage, FunnelResponse

router = APIRouter(prefix="/funnel", tags=["Funnel"])

# Stage ordering — adapt to your actual stage names in the mart
STAGE_ORDER = ["visitor", "lead", "mql", "sql", "trial", "paid"]


@router.get("", response_model=FunnelResponse, summary="Marketing → Revenue funnel")
def get_funnel(
    period: Optional[str] = Query(
        None,
        description="Filter by period (YYYY-MM or YYYY-QN). Defaults to latest.",
        example="2024-Q2",
    ),
):
    """
    Marketing funnel from **marts.fct_marketing_funnel**.

    Returns each funnel stage with:
    - `count` — users/accounts at this stage
    - `conversion_rate` — % converted from the previous stage
    - `drop_off` — absolute drop from previous stage
    - `overall_conversion` — top-of-funnel to paid %
    """

    if period:
        rows = query(
            """
            SELECT
                stage,
                count,
                period
            FROM marts.fct_marketing_funnel
            WHERE period = $1
            ORDER BY stage_order ASC
            """,
            [period],
        )
        active_period = period
    else:
        # Latest period in the mart
        rows = query(
            """
            SELECT
                stage,
                count,
                period
            FROM marts.fct_marketing_funnel
            WHERE period = (SELECT MAX(period) FROM marts.fct_marketing_funnel)
            ORDER BY stage_order ASC
            """
        )
        active_period = rows[0]["period"] if rows else "unknown"

    if not rows:
        return FunnelResponse(period=active_period, stages=[], overall_conversion=0.0)

    # Compute conversion_rate and drop_off relative to previous stage
    stages: list[FunnelStage] = []
    for i, row in enumerate(rows):
        prev_count = rows[i - 1]["count"] if i > 0 else None
        curr_count = row["count"]

        conversion_rate = (
            round(curr_count / prev_count * 100, 1) if prev_count else None
        )
        drop_off = (prev_count - curr_count) if prev_count is not None else None

        stages.append(FunnelStage(
            stage=row["stage"],
            count=curr_count,
            conversion_rate=conversion_rate,
            drop_off=drop_off,
        ))

    # Overall = paid / visitors
    top    = rows[0]["count"]
    bottom = rows[-1]["count"]
    overall = round(bottom / top * 100, 2) if top else 0.0

    return FunnelResponse(
        period=active_period,
        stages=stages,
        overall_conversion=overall,
    )
