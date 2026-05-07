"""
main.py — PulseMetrics Analytics API v2.0
──────────────────────────────────────────
Architecture:
    dbt (analytics.duckdb) → FastAPI (read-only) → React frontend

Data flow:
    ALL queries hit dbt marts — no raw tables, no ETL logic here.
    FastAPI is a pure serving layer.

Run:
    uvicorn backend.main:app --reload --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging

from backend.routers import kpis, revenue, channels, funnel, customers, insights
from backend.models import APIInfo

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Analytics Platform API",
    description="""
## Analytics Platform — powered by dbt + DuckDB

**Data source:** All endpoints query pre-built dbt marts in `analytics.duckdb`.
FastAPI is a read-only serving layer — zero raw SQL, zero ETL logic.

### Marts consumed
| Endpoint | dbt Mart |
|---|---|
| `/kpis` | `marts.mart_monthly_growth` |
| `/revenue-trend` | `marts.fact_revenue` |
| `/channel-performance` | `marts.dim_channel` |
| `/funnel` | `marts.fct_marketing_funnel` |
| `/top-customers` | `marts.mart_customer_metrics` |
| `/insights` | All marts (AI-summarised) |
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Tighten origins in production (remove "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # → ["http://localhost:3000"] in prod
    allow_credentials=True,
    allow_methods=["*"],         # read-only API — no POST/PUT/DELETE
    allow_headers=["*"],
)

# ── Request timing middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
    log.info(f"{request.method} {request.url.path}  →  {response.status_code}  ({elapsed_ms}ms)")
    return response

# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    log.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": str(exc),
            "path": str(request.url.path),
        },
    )

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(kpis.router)
app.include_router(revenue.router)
app.include_router(channels.router)
app.include_router(funnel.router)
app.include_router(customers.router)
app.include_router(insights.router)

# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", response_model=APIInfo, tags=["Meta"])
def root():
    return APIInfo(
        endpoints=[
            "GET /kpis",
            "GET /kpis/history",
            "GET /revenue-trend",
            "GET /channel-performance",
            "GET /funnel",
            "GET /top-customers",
            "GET /insights",
        ]
    )

@app.get("/health", tags=["Meta"])
def health():
    """Liveness probe — used by Docker / k8s."""
    from backend.db import query_one
    try:
        query_one("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"
    return {"status": "ok", "db": db_status}
