"""
routers/customers.py
────────────────────
Source mart: marts.mart_customer_metrics

mart_customer_metrics has one row per customer with lifetime metrics
computed by dbt (LTV, MRR, health score, months active, etc).
"""

from fastapi import APIRouter, Query
from typing import Optional
from backend.db import query
from backend.models import CustomerMetrics

router = APIRouter(prefix="/top-customers", tags=["Customers"])


@router.get("", response_model=list[CustomerMetrics], summary="Top customers by LTV")
def get_top_customers(
    limit: int = Query(20, ge=1, le=100, description="Max rows to return"),
    status: Optional[str] = Query(
        None,
        description="Filter by status",
        enum=["active", "churned"],
    ),
    plan: Optional[str] = Query(
        None,
        description="Filter by plan name",
        example="enterprise",
    ),
    sort_by: str = Query(
        "ltv",
        description="Sort field",
        enum=["ltv", "mrr", "months_active", "health_score"],
    ),
):
    """
    Top customers ranked by LTV from **marts.mart_customer_metrics**.

    Supports filtering by:
    - `status` — active or churned
    - `plan` — pricing tier

    And sorting by `ltv`, `mrr`, `months_active`, or `health_score`.
    """
    conditions = []
    params: list = []

    if status:
        params.append(status)
        conditions.append(f"status = ${len(params)}")
    if plan:
        params.append(plan)
        conditions.append(f"LOWER(plan) = LOWER(${len(params)})")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    allowed_sorts = {"ltv", "mrr", "months_active", "health_score"}
    order_col = sort_by if sort_by in allowed_sorts else "ltv"

    params.append(limit)

    sql = f"""
        SELECT
            customer_id::VARCHAR    AS customer_id,
            customer_name,
            plan,
            channel,
            mrr,
            ltv,
            months_active,
            status,
            health_score
        FROM marts.mart_customer_metrics
        {where}
        ORDER BY {order_col} DESC NULLS LAST
        LIMIT ${len(params)}
    """

    rows = query(sql, params if params else None)
    return [CustomerMetrics(**r) for r in rows]
