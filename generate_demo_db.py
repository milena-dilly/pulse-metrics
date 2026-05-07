import duckdb
import pandas as pd
import random
from datetime import datetime

conn = duckdb.connect("analytics.duckdb")

months = pd.date_range("2024-01-01", periods=12, freq="MS")

monthly_growth = pd.DataFrame({
    "month": months.astype(str),
    "mrr": [random.randint(80000, 150000) for _ in months],
    "mrr_mom_pct": [random.uniform(-0.05, 0.2) for _ in months],
    "active_customers": [random.randint(200, 500) for _ in months],
    "new_customers": [random.randint(10, 50) for _ in months],
    "churned_customers": [random.randint(1, 20) for _ in months],
    "churn_rate": [random.uniform(0.01, 0.08) for _ in months],
    "nrr": [random.uniform(95, 125) for _ in months],
    "new_mrr": [random.randint(10000, 30000) for _ in months],
    "expansion_mrr": [random.randint(5000, 20000) for _ in months],
    "contraction_mrr": [random.randint(1000, 10000) for _ in months],
    "churn_mrr": [random.randint(1000, 15000) for _ in months],
    "net_new_mrr": [random.randint(5000, 40000) for _ in months],
})

conn.execute("CREATE SCHEMA IF NOT EXISTS marts")

conn.register("monthly_growth_df", monthly_growth)

conn.execute("""
CREATE OR REPLACE TABLE marts.mart_monthly_growth AS
SELECT * FROM monthly_growth_df
""")

channels = pd.DataFrame({
    "channel": ["Organic", "Paid Ads", "Referral", "Partnership"],
    "customers_acquired": [120, 90, 60, 40],
    "total_revenue": [300000, 250000, 180000, 150000],
    "churn_rate": [0.03, 0.06, 0.02, 0.04],
    "roi": [4.5, 2.8, 5.2, 3.7]
})

conn.register("channels_df", channels)

conn.execute("""
CREATE OR REPLACE TABLE marts.dim_channel AS
SELECT * FROM channels_df
""")

customers = pd.DataFrame({
    "customer_id": range(1, 11),
    "customer_name": [f"Company {i}" for i in range(1, 11)],
    "plan": ["Pro"] * 10,
    "channel": ["Organic"] * 10,
    "mrr": [random.randint(1000, 5000) for _ in range(10)],
    "ltv": [random.randint(10000, 50000) for _ in range(10)],
    "months_active": [random.randint(3, 24) for _ in range(10)],
    "status": ["active"] * 10,
    "health_score": [random.randint(70, 100) for _ in range(10)]
})

conn.register("customers_df", customers)

conn.execute("""
CREATE OR REPLACE TABLE marts.mart_customer_metrics AS
SELECT * FROM customers_df
""")
 
revenue = pd.DataFrame({
    "month": [str(m.date()) for m in months for _ in range(4)],
    "movement_type": ["new", "expansion", "contraction", "churn"] * len(months),
    "revenue": [random.randint(1000, 20000) for _ in range(len(months) * 4)]
})

conn.register("revenue_df", revenue)

conn.execute("""
CREATE OR REPLACE TABLE marts.fact_revenue AS
SELECT * FROM revenue_df
""")

funnel = pd.DataFrame({
    "period": [str(m.date()) for m in months for _ in range(5)],
    "stage": ["visitor", "lead", "mql", "sql", "paid"] * len(months),
    "stage_order": [1, 2, 3, 4, 5] * len(months),
    "count": [random.randint(100, 5000) for _ in range(len(months) * 5)]
})

conn.register("funnel_df", funnel)

conn.execute("""
CREATE OR REPLACE TABLE marts.fct_marketing_funnel AS
SELECT * FROM funnel_df
""")

print("analytics.duckdb generated successfully!")