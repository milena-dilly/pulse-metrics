"""
routers/channels.py
───────────────────
Source mart: marts.dim_channel

dim_channel is a dimension table enriched by dbt with acquisition
and revenue metrics per channel. FastAPI reads it directly.
"""

from fastapi import APIRouter, Query
from typing import Optional
from backend.db import query
from backend.models import ChannelPerformance

router = APIRouter(prefix="/channel-performance", tags=["Channels"])


@router.get("", response_model=list[ChannelPerformance], summary="Revenue by acquisition channel")
def get_channel_performance(
    sort_by: str = Query(
        "total_revenue",
        description="Column to sort by",
        enum=["total_revenue", "customers_acquired", "churn_rate", "roi"],
    ),
    min_customers: Optional[int] = Query(
        None,
        description="Filter channels with fewer than N customers",
        example=10,
    ),
):
    """
    Performance metrics per acquisition channel from **marts.dim_channel**.

    Useful for answering:
    - Which channels drive the most revenue?
    - Which channels have the best retention?
    - Where is ROI highest?
    """
    where_clause = f"WHERE customers_acquired >= {min_customers}" if min_customers else ""

    # Safely allow only whitelisted sort columns
    allowed_sorts = {"total_revenue", "customers_acquired", "churn_rate", "roi"}
    order_col = sort_by if sort_by in allowed_sorts else "total_revenue"

    sql = f"""
        SELECT
            channel,
            customers_acquired,
            total_revenue,
            ROUND(total_revenue / NULLIF(customers_acquired, 0), 2)
                AS avg_revenue_per_customer,
            churn_rate,
            roi
        FROM marts.dim_channel
        {where_clause}
        ORDER BY {order_col} DESC NULLS LAST
    """
    rows = query(sql)
    return [ChannelPerformance(**r) for r in rows]
