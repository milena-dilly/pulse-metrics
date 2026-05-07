/**
 * App.jsx — Main dashboard
 * ─────────────────────────
 * All data comes from the FastAPI backend (no mocks).
 * Uses useApiBatch to load everything in parallel on mount.
 */

import { useState } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, FunnelChart,
  Funnel, LabelList,
} from "recharts";

import { useApiBatch, useApi } from "./hooks/useApi";
import {
  fetchKPIs, fetchRevenueTrend, fetchChannelPerformance,
  fetchFunnel, fetchTopCustomers, fetchInsights,
} from "./api/endpoints";

// ── Design tokens ─────────────────────────────────────────────────────────────
const C = {
  ink:        "#0f0f0f",
  ink2:       "#3a3a3a",
  ink3:       "#888",
  surface:    "#ffffff",
  bg:         "#f5f4f1",
  border:     "rgba(0,0,0,0.08)",
  navy:       "#1a1a2e",
  navy2:      "#16213e",
  green:      "#0d7a4e",
  greenBg:    "#e6f4ee",
  red:        "#c0392b",
  redBg:      "#fdecea",
  blue:       "#3266ad",
  violet:     "#6d28d9",
  teal:       "#10b981",
  amber:      "#b45309",
  chartGreen: "#4ade80",
  chartRed:   "#f87171",
  chartBlue:  "#60a5fa",
};

const PLAN_COLORS = { starter: C.blue, growth: C.violet, enterprise: C.teal };
const CHANNEL_COLORS = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4"];

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt   = (n) => n == null ? "—" : "$" + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });
const fmtK  = (n) => n == null ? "—" : n >= 1_000_000 ? `$${(n / 1e6).toFixed(2)}M` : `$${(n / 1e3).toFixed(0)}k`;
const pct   = (n) => n == null ? "—" : `${Number(n).toFixed(1)}%`;
const mono  = { fontFamily: "'DM Mono', monospace" };
const serif = { fontFamily: "'Fraunces', serif" };

// ── Shared components ─────────────────────────────────────────────────────────

function Card({ children, style = {} }) {
  return (
    <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: 18, ...style }}>
      {children}
    </div>
  );
}

function CardHeader({ title, sub }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 11, fontWeight: 500, textTransform: "uppercase", letterSpacing: ".8px", color: C.ink, marginBottom: 2 }}>{title}</div>
      {sub && <div style={{ fontSize: 11, color: C.ink3 }}>{sub}</div>}
    </div>
  );
}

function KPICard({ label, value, delta, deltaType }) {
  const bg    = { up: C.greenBg, down: C.redBg, flat: "#f1f0ec" };
  const color = { up: C.green,   down: C.red,   flat: C.ink3 };
  const bar   = { up: C.chartGreen, down: C.chartRed, flat: "#94a3b8" };
  return (
    <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: "14px 16px", position: "relative", overflow: "hidden" }}>
      <div style={{ fontSize: 10, color: C.ink3, textTransform: "uppercase", letterSpacing: ".8px", marginBottom: 6 }}>{label}</div>
      <div style={{ ...serif, fontSize: 22, fontWeight: 600, color: C.ink, lineHeight: 1.1 }}>{value}</div>
      {delta && (
        <div style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11, marginTop: 5, padding: "2px 6px", borderRadius: 4, background: bg[deltaType] || bg.flat, color: color[deltaType] || color.flat }}>
          {delta}
        </div>
      )}
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 2, background: bar[deltaType] || bar.flat }} />
    </div>
  );
}

function LoadingShimmer({ height = 200 }) {
  return (
    <div style={{ height, borderRadius: 8, background: "linear-gradient(90deg, #f0eeea 25%, #e8e6e1 50%, #f0eeea 75%)", backgroundSize: "200% 100%", animation: "shimmer 1.4s infinite" }}>
      <style>{`@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }`}</style>
    </div>
  );
}

function ErrorBox({ error }) {
  return (
    <div style={{ padding: "12px 16px", background: C.redBg, borderRadius: 8, color: C.red, fontSize: 12 }}>
      <strong>Error:</strong> {error?.detail || error?.message || "Unknown error"}
      <div style={{ marginTop: 4, color: C.ink3, fontSize: 11 }}>Is the FastAPI backend running on port 8000?</div>
    </div>
  );
}

function InsightItem({ insight }) {
  const borderColor = { positive: "#4ade80", warning: "#f87171", neutral: "#94a3b8" };
  return (
    <div style={{ background: "rgba(255,255,255,.06)", borderRadius: 8, padding: "10px 12px", marginBottom: 8, borderLeft: `3px solid ${borderColor[insight.type] || "#94a3b8"}` }}>
      <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: ".8px", color: "rgba(255,255,255,.4)", marginBottom: 3 }}>{insight.metric || insight.type}</div>
      <div style={{ fontSize: 12, fontWeight: 500, color: "#fff", marginBottom: 3 }}>{insight.title}</div>
      <div style={{ fontSize: 11, color: "rgba(255,255,255,.7)", lineHeight: 1.5 }}>{insight.body}</div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const [period, setPeriod] = useState({ from: "2023-01", to: "2024-06" });
  const [custFilter, setCustFilter] = useState({ status: null, plan: null });

  // Load everything in parallel on mount
  const { results, loading: batchLoading, error: batchError } = useApiBatch({
    kpis:     () => fetchKPIs(),
    revenue:  () => fetchRevenueTrend(period.from, period.to),
    channels: () => fetchChannelPerformance(),
    funnel:   () => fetchFunnel(),
  }, [period]);

  const { data: customers, loading: custLoading } = useApi(
    fetchTopCustomers,
    [{ limit: 10, ...custFilter }],
    [custFilter],
  );

  const { data: insights } = useApi(fetchInsights, []);

  const kpis    = results.kpis;
  const revenue = results.revenue;
  const channels = results.channels;
  const funnel  = results.funnel;
  const mom     = kpis?.mrr_mom_pct;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", minHeight: "100vh", ...mono, background: C.bg, color: C.ink }}>

      {/* ── Sidebar ── */}
      <aside style={{ background: C.navy, display: "flex", flexDirection: "column" }}>
        <div style={{ padding: "20px 20px 16px", borderBottom: "1px solid rgba(255,255,255,.08)" }}>
          <div style={{ ...serif, fontSize: 20, color: "#fff", fontWeight: 600 }}>Analytics</div>
          <div style={{ fontSize: 10, color: "rgba(255,255,255,.35)", letterSpacing: "1px", textTransform: "uppercase", marginTop: 2 }}>dbt · DuckDB · FastAPI</div>
        </div>
        <nav style={{ padding: "16px 0", flex: 1 }}>
          {[["Overview","●"],["Revenue","●"],["Channels","●"],["Funnel","●"],["Customers","●"],["AI Insights","●"]].map(([label, dot], i) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 20px", fontSize: 12, color: i === 0 ? "#fff" : "rgba(255,255,255,.45)", background: i === 0 ? "rgba(255,255,255,.07)" : "transparent", borderLeft: i === 0 ? "2px solid #60a5fa" : "2px solid transparent", cursor: "pointer" }}>
              <span style={{ fontSize: 6, opacity: .6 }}>{dot}</span>
              {label}
            </div>
          ))}
        </nav>
        <div style={{ padding: "16px 20px", borderTop: "1px solid rgba(255,255,255,.08)", fontSize: 10, color: "rgba(255,255,255,.25)" }}>
          Source: analytics.duckdb
        </div>
      </aside>

      {/* ── Main ── */}
      <main style={{ display: "flex", flexDirection: "column" }}>

        {/* Topbar */}
        <div style={{ background: C.surface, borderBottom: `1px solid ${C.border}`, padding: "14px 28px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ ...serif, fontSize: 16, fontWeight: 600 }}>Revenue Overview</div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {batchError && <span style={{ fontSize: 11, color: C.red }}>⚠ API error</span>}
            <span style={{ fontSize: 10, padding: "3px 8px", borderRadius: 20, background: batchError ? C.redBg : "#dcfce7", color: batchError ? C.red : "#166534", letterSpacing: ".5px" }}>
              {batchError ? "● Disconnected" : "● Live"}
            </span>
            <select
              value={`${period.from}|${period.to}`}
              onChange={e => {
                const [from, to] = e.target.value.split("|");
                setPeriod({ from, to });
              }}
              style={{ ...mono, fontSize: 12, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, padding: "5px 10px" }}
            >
              <option value="2024-01|2024-06">Last 6 months</option>
              <option value="2023-07|2024-06">Last 12 months</option>
              <option value="2023-01|2024-06">All time (18 mo)</option>
            </select>
          </div>
        </div>

        {/* Content */}
        <div style={{ padding: "24px 28px", flex: 1, overflowY: "auto" }}>

          {batchError && <ErrorBox error={batchError} />}

          {/* KPIs */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 12, marginBottom: 20 }}>
            {batchLoading ? Array(5).fill(0).map((_, i) => <LoadingShimmer key={i} height={90} />) : <>
              <KPICard label="MRR"              value={fmtK(kpis?.mrr)}              delta={mom != null ? `${mom > 0 ? "↑" : "↓"} ${Math.abs(mom).toFixed(1)}% MoM` : null} deltaType={mom > 0 ? "up" : "down"} />
              <KPICard label="ARR"              value={fmtK(kpis?.arr)}              delta="Annualised"       deltaType="flat" />
              <KPICard label="Active Customers" value={kpis?.active_customers ?? "—"} delta={`+${kpis?.new_customers ?? 0} new`}  deltaType="up" />
              <KPICard label="NRR"              value={pct(kpis?.nrr)}              delta={kpis?.nrr >= 100 ? "Healthy" : "Below 100%"} deltaType={kpis?.nrr >= 100 ? "up" : "down"} />
              <KPICard label="Churn Rate"       value={pct(kpis?.churn_rate)}       delta={`${kpis?.churned_customers ?? 0} churned`} deltaType="down" />
            </>}
          </div>

          {/* Row 1: Revenue Trend + Channel Mix */}
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16, marginBottom: 16 }}>
            <Card>
              <CardHeader title="Revenue Trend" sub="From marts.fact_revenue — new, expansion, churn MoM" />
              {batchLoading ? <LoadingShimmer /> : !revenue?.length ? <ErrorBox error={{ message: "No data" }} /> : (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={revenue} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,.05)" />
                    <XAxis dataKey="month" tick={{ fontSize: 10 }} tickFormatter={m => m.slice(5)} />
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(v, n) => [fmt(v), n]} />
                    <Line type="monotone" dataKey="total_revenue"   stroke={C.blue}       strokeWidth={2} dot={false} name="Total MRR" />
                    <Line type="monotone" dataKey="new_revenue"     stroke={C.chartGreen} strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="New" />
                    <Line type="monotone" dataKey="churn_revenue"   stroke={C.chartRed}   strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="Churn" />
                    <Line type="monotone" dataKey="net_new_revenue" stroke={C.amber}      strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="Net New" />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </Card>

            <Card>
              <CardHeader title="Channel Mix" sub="From marts.dim_channel" />
              {batchLoading ? <LoadingShimmer /> : !channels?.length ? <ErrorBox error={{ message: "No data" }} /> : (
                <>
                  <ResponsiveContainer width="100%" height={150}>
                    <PieChart>
                      <Pie data={channels} cx="50%" cy="50%" innerRadius={45} outerRadius={68} dataKey="total_revenue" paddingAngle={3}>
                        {channels.map((_, i) => <Cell key={i} fill={CHANNEL_COLORS[i % CHANNEL_COLORS.length]} />)}
                      </Pie>
                      <Tooltip formatter={(v) => [fmt(v), "Revenue"]} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{ display: "flex", flexDirection: "column", gap: 5, marginTop: 6 }}>
                    {channels.slice(0, 5).map((ch, i) => (
                      <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 11 }}>
                        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span style={{ width: 8, height: 8, borderRadius: 2, background: CHANNEL_COLORS[i] }} />
                          {ch.channel}
                        </span>
                        <span style={{ color: C.ink3 }}>{fmt(ch.total_revenue)}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </Card>
          </div>

          {/* Row 2: Waterfall + Funnel + Insights */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 16 }}>

            {/* MRR Waterfall */}
            <Card>
              <CardHeader title="MRR Movements" sub="New · Expansion · Churn" />
              {batchLoading ? <LoadingShimmer /> : !revenue?.length ? null : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={revenue} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,.05)" />
                    <XAxis dataKey="month" tick={{ fontSize: 9 }} tickFormatter={m => m.slice(5)} />
                    <YAxis tick={{ fontSize: 9 }} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(v, n) => [fmt(Math.abs(v)), n]} />
                    <Bar dataKey="new_revenue"       name="New"       fill={C.chartGreen} radius={[2,2,0,0]} stackId="a" />
                    <Bar dataKey="expansion_revenue" name="Expansion" fill={C.chartBlue}  radius={[2,2,0,0]} stackId="a" />
                    <Bar dataKey="churn_revenue"     name="Churn"     fill={C.chartRed}   radius={[0,0,2,2]} stackId="b" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>

            {/* Funnel */}
            <Card>
              <CardHeader title="Marketing Funnel" sub={`From marts.fct_marketing_funnel · ${funnel?.period ?? "—"}`} />
              {batchLoading ? <LoadingShimmer /> : !funnel?.stages?.length ? <ErrorBox error={{ message: "No funnel data" }} /> : (
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {funnel.stages.map((s, i) => {
                    const maxCount = funnel.stages[0].count;
                    const barWidth = Math.round((s.count / maxCount) * 100);
                    return (
                      <div key={i}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: C.ink3, marginBottom: 2 }}>
                          <span style={{ textTransform: "capitalize" }}>{s.stage}</span>
                          <span>{s.count?.toLocaleString()} {s.conversion_rate != null ? `(${s.conversion_rate}%)` : ""}</span>
                        </div>
                        <div style={{ background: C.bg, borderRadius: 3, height: 6, overflow: "hidden" }}>
                          <div style={{ width: `${barWidth}%`, height: "100%", background: CHANNEL_COLORS[i % CHANNEL_COLORS.length], borderRadius: 3, transition: "width .4s ease" }} />
                        </div>
                      </div>
                    );
                  })}
                  <div style={{ marginTop: 8, fontSize: 11, color: C.ink3 }}>
                    Overall conversion: <strong style={{ color: C.ink }}>{pct(funnel.overall_conversion)}</strong>
                  </div>
                </div>
              )}
            </Card>

            {/* AI Insights */}
            <div style={{ background: C.navy2, borderRadius: 10, padding: 18 }}>
              <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: ".7px", color: "rgba(255,255,255,.35)", marginBottom: 4 }}>
                AI · {insights?.month ?? "—"}
              </div>
              <div style={{ ...serif, fontSize: 14, color: "#fff", fontWeight: 600, marginBottom: 6 }}>Executive Insights</div>
              {insights ? (
                <>
                  <p style={{ fontSize: 11, color: "rgba(255,255,255,.6)", lineHeight: 1.6, marginBottom: 10 }}>{insights.summary}</p>
                  {insights.insights?.map((ins, i) => <InsightItem key={i} insight={ins} />)}
                  <div style={{ marginTop: 6, fontSize: 10, color: "rgba(255,255,255,.2)", textAlign: "right" }}>
                    {insights.generated_by === "llm" ? "Claude API" : "Rule-based"}
                  </div>
                </>
              ) : <LoadingShimmer height={160} />}
            </div>
          </div>

          {/* Row 3: Top Customers */}
          <Card>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <CardHeader title="Top Customers" sub="From marts.mart_customer_metrics" />
              <div style={{ display: "flex", gap: 8 }}>
                {[["All", null], ["Active", "active"], ["Churned", "churned"]].map(([label, val]) => (
                  <button key={label} onClick={() => setCustFilter(f => ({ ...f, status: val }))}
                    style={{ ...mono, fontSize: 11, padding: "4px 10px", borderRadius: 6, border: `1px solid ${C.border}`, background: custFilter.status === val ? C.ink : C.surface, color: custFilter.status === val ? "#fff" : C.ink, cursor: "pointer" }}>
                    {label}
                  </button>
                ))}
              </div>
            </div>
            {custLoading ? <LoadingShimmer height={160} /> : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr>{["Customer", "Plan", "Channel", "MRR", "LTV", "Months", "Health", "Status"].map(h => (
                    <th key={h} style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: ".6px", color: C.ink3, textAlign: "left", padding: "4px 8px", borderBottom: `1px solid ${C.border}` }}>{h}</th>
                  ))}</tr>
                </thead>
                <tbody>
                  {(customers ?? []).map((c) => (
                    <tr key={c.customer_id}>
                      <td style={{ padding: "7px 8px", color: C.ink2 }}>{c.customer_name ?? c.customer_id}</td>
                      <td style={{ padding: "7px 8px" }}>
                        <span style={{ padding: "2px 7px", borderRadius: 4, fontSize: 10, background: c.plan ? "#eff6ff" : C.bg, color: PLAN_COLORS[c.plan?.toLowerCase()] ?? C.ink3 }}>
                          {c.plan ?? "—"}
                        </span>
                      </td>
                      <td style={{ padding: "7px 8px", color: C.ink3 }}>{c.channel ?? "—"}</td>
                      <td style={{ padding: "7px 8px" }}>{fmt(c.mrr)}</td>
                      <td style={{ padding: "7px 8px", fontWeight: 500 }}>{fmt(c.ltv)}</td>
                      <td style={{ padding: "7px 8px", color: C.ink3 }}>{c.months_active}</td>
                      <td style={{ padding: "7px 8px" }}>
                        {c.health_score != null ? (
                          <span style={{ color: c.health_score >= 70 ? C.green : c.health_score >= 40 ? C.amber : C.red }}>
                            {c.health_score.toFixed(0)}
                          </span>
                        ) : "—"}
                      </td>
                      <td style={{ padding: "7px 8px", fontSize: 11, color: c.status === "active" ? C.green : C.red }}>
                        {c.status === "active" ? "● Active" : "○ Churned"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

        </div>
      </main>
    </div>
  );
}
