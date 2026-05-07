"""
models.py — Pydantic response schemas
──────────────────────────────────────
One schema per dbt mart. Field names mirror mart column names exactly
so serialization is zero-overhead (no mapping needed).
"""

from pydantic import BaseModel, Field
from typing import Optional


# ── /kpis → marts.mart_monthly_growth ────────────────────────────────────────

class KPISnapshot(BaseModel):
    """Headline KPIs from the latest month in mart_monthly_growth."""
    month: str
    mrr: float
    arr: float
    mrr_mom_pct: Optional[float] = Field(None, description="Month-over-month growth %")
    active_customers: int
    new_customers: int
    churned_customers: int
    churn_rate: float
    nrr: float = Field(description="Net Revenue Retention %")
    new_mrr: float
    expansion_mrr: float
    contraction_mrr: float
    churn_mrr: float
    net_new_mrr: float


# ── /revenue-trend → marts.fact_revenue ──────────────────────────────────────

class RevenueTrendRow(BaseModel):
    """One row per month in the revenue time-series."""
    month: str
    total_revenue: float
    new_revenue: float
    expansion_revenue: float
    churn_revenue: float
    net_new_revenue: float
    cumulative_revenue: Optional[float] = None


# ── /channel-performance → marts.dim_channel ─────────────────────────────────

class ChannelPerformance(BaseModel):
    """Performance metrics per acquisition channel."""
    channel: str
    customers_acquired: int
    total_revenue: float
    avg_revenue_per_customer: float
    churn_rate: float
    roi: Optional[float] = Field(None, description="Return on investment if cost data available")


# ── /funnel → marts.fct_marketing_funnel ─────────────────────────────────────

class FunnelStage(BaseModel):
    """Single stage in the marketing → revenue funnel."""
    stage: str
    count: int
    conversion_rate: Optional[float] = Field(None, description="Conversion % from previous stage")
    drop_off: Optional[int] = Field(None, description="Users lost at this stage")


class FunnelResponse(BaseModel):
    period: str
    stages: list[FunnelStage]
    overall_conversion: float = Field(description="Top-of-funnel to paid conversion %")


# ── /top-customers → marts.mart_customer_metrics ─────────────────────────────

class CustomerMetrics(BaseModel):
    """Per-customer metrics from mart_customer_metrics."""
    customer_id: str
    customer_name: Optional[str] = None
    plan: Optional[str] = None
    channel: Optional[str] = None
    mrr: float
    ltv: float
    months_active: int
    status: str  # active | churned
    health_score: Optional[float] = Field(None, description="0–100 customer health score")


# ── Shared ────────────────────────────────────────────────────────────────────

class APIInfo(BaseModel):
    service: str = "Analytics API"
    version: str = "2.0.0"
    dbt_source: str = "analytics.duckdb"
    status: str = "ok"
    endpoints: list[str]
