/**
 * api/endpoints.js — All API calls in one place
 * ──────────────────────────────────────────────
 * Each function maps 1:1 to a FastAPI endpoint.
 * Components import from here — never call fetch() directly.
 */

import { apiFetch } from "./client";

// ── KPIs ─────────────────────────────────────────────────────────────────────

/** Latest headline KPIs, or a specific month. */
export const fetchKPIs = (month = null) =>
  apiFetch("/kpis", { month });

/** KPI history for charting. */
export const fetchKPIHistory = (fromMonth = "2023-01", toMonth = "2024-06") =>
  apiFetch("/kpis/history", { from_month: fromMonth, to_month: toMonth });

// ── Revenue Trend ─────────────────────────────────────────────────────────────

/**
 * Monthly revenue breakdown.
 * @param {string}  fromMonth  - YYYY-MM
 * @param {string}  toMonth    - YYYY-MM
 * @param {boolean} cumulative - include running total
 */
export const fetchRevenueTrend = (fromMonth = "2023-01", toMonth = "2024-06", cumulative = false) =>
  apiFetch("/revenue-trend", { from_month: fromMonth, to_month: toMonth, cumulative });

// ── Channel Performance ───────────────────────────────────────────────────────

/**
 * Revenue + retention metrics by acquisition channel.
 * @param {string}  sortBy        - total_revenue | customers_acquired | churn_rate | roi
 * @param {number}  minCustomers  - exclude channels below threshold
 */
export const fetchChannelPerformance = (sortBy = "total_revenue", minCustomers = null) =>
  apiFetch("/channel-performance", { sort_by: sortBy, min_customers: minCustomers });

// ── Funnel ────────────────────────────────────────────────────────────────────

/**
 * Marketing → paid funnel with conversion rates.
 * @param {string} period - YYYY-MM or YYYY-QN (latest if omitted)
 */
export const fetchFunnel = (period = null) =>
  apiFetch("/funnel", { period });

// ── Top Customers ─────────────────────────────────────────────────────────────

/**
 * Top customers ranked by LTV.
 * @param {object} opts
 * @param {number}  opts.limit   - max rows (default 20)
 * @param {string}  opts.status  - "active" | "churned"
 * @param {string}  opts.plan    - plan name filter
 * @param {string}  opts.sortBy  - ltv | mrr | months_active | health_score
 */
export const fetchTopCustomers = ({ limit = 20, status = null, plan = null, sortBy = "ltv" } = {}) =>
  apiFetch("/top-customers", { limit, status, plan, sort_by: sortBy });

// ── AI Insights ───────────────────────────────────────────────────────────────

/** AI-generated executive summary + insights for a given month. */
export const fetchInsights = (month = null) =>
  apiFetch("/insights", { month });
