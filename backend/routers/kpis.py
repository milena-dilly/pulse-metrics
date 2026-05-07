"""
routers/kpis.py
───────────────
Source mart: marts.mart_monthly_growth

mart_monthly_growth is the pre-aggregated monthly snapshot produced by dbt.
We never aggregate here — FastAPI only reads and shapes what dbt already computed.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend.db import query, query_one
from backend.models import KPISnapshot

router = APIRouter(prefix="/kpis", tags=["KPIs"])

# ── SQL ───────────────────────────────────────────────────────────────────────

# Full mart columns we expose.
# Alias dbt column names → Pydantic field names where they differ.
_KPI_SELECT = """
    SELECT
        month::VARCHAR                        AS month,
        mrr,
        mrr * 12                              AS arr,
        mrr_mom_pct,
        active_customers,
        new_customers,
        churned_customers,
        churn_rate,
        nrr,
        new_mrr,
        expansion_mrr,
        contraction_mrr,
        churn_mrr,
        net_new_mrr
    FROM marts.mart_monthly_growth
"""


@router.get("", response_model=KPISnapshot, summary="Headline KPIs")
def get_kpis(
    month: Optional[str] = Query(
        None,
        description="Specific month in YYYY-MM format. Defaults to latest.",
        example="2024-06",
    )
):
    """
    Returns headline KPIs for a given month from **marts.mart_monthly_growth**.

    - Omit `month` to get the latest snapshot.
    - All aggregations are pre-computed by dbt — this endpoint is a pure read.
    """
    if month:
        row = query_one(
            f"{_KPI_SELECT} WHERE month::VARCHAR = $1",
            [month],
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"No KPI data found for month: {month}",
            )
    else:
        row = query_one(f"{_KPI_SELECT} ORDER BY month DESC LIMIT 1")
        if not row:
            raise HTTPException(
                status_code=404,
                detail="No KPI data found. Run `dbt build` first.",
            )

    return KPISnapshot(**row)


@router.get("/history", response_model=list[KPISnapshot], summary="KPI history")
def get_kpi_history(
    from_month: str = Query("2023-01", example="2023-01"),
    to_month:   str = Query("2024-06", example="2024-06"),
):
    """Returns all monthly KPI snapshots within a date range."""
    rows = query(
        f"{_KPI_SELECT} WHERE month::VARCHAR BETWEEN $1 AND $2 ORDER BY month",
        [from_month, to_month],
    )
    return [KPISnapshot(**r) for r in rows]
