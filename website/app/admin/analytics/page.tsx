"use client";

import { useSession } from "next-auth/react";
import { useCallback, useEffect, useRef, useState } from "react";

interface RecentEvent {
  event: string;
  company: string;
  industry: string;
  ts: string;
  submission_id?: number | null;
  renderer_used?: string;
  report_generation_status?: string;
  duration_s?: number | null;
  warning_count?: number;
  has_report?: boolean;
  enhancement_keys?: string[];
  llm_preview_status?: string;
  top_warning?: string;
  research_quality_score?: number | null;
  research_coverage_score?: number | null;
  research_source_quality_score?: number | null;
  research_freshness_score?: number | null;
  low_coverage_dimensions?: string[];
  missing_evidence_flags?: string[];
  audit_path?: string;
  verdict?: string;
  score?: number | null;
}

interface BackendRun {
  ts: string;
  submission_id?: number | null;
  company: string;
  industry: string;
  renderer_used: string;
  duration_s?: number | null;
  warning_count: number;
  has_report: boolean;
  report_generation_status: string;
  enhancement_keys: string[];
  llm_preview_status: string;
  top_warning: string;
  research_quality_score?: number | null;
  research_coverage_score?: number | null;
  research_source_quality_score?: number | null;
  research_freshness_score?: number | null;
  low_coverage_dimensions: string[];
  missing_evidence_flags: string[];
  audit_path: string;
  verdict: string;
  score?: number | null;
}

interface Analytics {
  totals: Record<string, number>;
  daily_submissions: Array<{ date: string; count: number }>;
  status_breakdown: Array<{ label: string; count: number }>;
  industry_breakdown: Array<{ label: string; count: number }>;
  stage_breakdown: Array<{ label: string; count: number }>;
  recent_events: RecentEvent[];
  backend: {
    total_runs: number;
    avg_duration_s: number;
    avg_research_quality_score: number;
    degraded_runs: number;
    low_research_runs: number;
    report_failures: number;
    llm_preview_runs: number;
    failed_runs: number;
    needs_info_runs: number;
    legacy_renderer_runs: number;
    llm_renderer_runs: number;
    renderer_breakdown: Array<{ label: string; count: number }>;
    enhancement_coverage: Array<{ label: string; count: number }>;
    coverage_gap_breakdown: Array<{ label: string; count: number }>;
    recent_runs: BackendRun[];
    recent_degraded_runs: BackendRun[];
  };
  users: Array<{ id: number; name: string; email: string; isAdmin: boolean; submissionCount: number; createdAt: string }>;
  hourly_submissions: Array<{ hour: number; count: number }>;
}

const STATUS_COLORS: Record<string, string> = {
  queued: "#f3b13f",
  reviewing: "#196cff",
  report_sent: "#34c7a0",
  archived: "#6e7f97",
};

function timeAgo(dateStr: string): string {
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function formatDate(val: string): string {
  const d = new Date(val);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function formatDuration(value?: number | null): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return "—";
  if (value >= 60) return `${(value / 60).toFixed(1)}m`;
  return `${value.toFixed(1)}s`;
}

function formatScore01(value?: number | null): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) return "—";
  return value.toFixed(2);
}

function StatCard({ label, value, meta, accent }: { label: string; value: string | number; meta: string; accent?: string }) {
  return (
    <div className="p-5 rounded-[26px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg hover:-translate-y-0.5 transition-transform">
      <span className="block text-xs font-bold tracking-[0.14em] uppercase text-ink-soft">{label}</span>
      <strong className="block mt-2.5 text-2xl tracking-tight" style={accent ? { color: accent } : {}}>{value}</strong>
      <em className="block mt-1.5 text-sm text-ink-soft not-italic">{meta}</em>
    </div>
  );
}

function BarChart({ rows, height = 200 }: { rows: Array<{ label: string; value: number }>; height?: number }) {
  if (!rows.length) return <p className="text-ink-soft text-sm py-6 text-center">No data yet.</p>;
  const max = Math.max(...rows.map((r) => r.value), 1);
  return (
    <div className="flex items-end gap-2" style={{ minHeight: height }}>
      {rows.map((r, i) => {
        const h = Math.max(6, Math.round((r.value / max) * (height - 40)));
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-1.5 group">
            <span className="text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity">{r.value}</span>
            <div className="chart-bar w-full" style={{ height: h }} />
            <span className="text-[10px] text-ink-soft truncate w-full text-center">{r.label}</span>
          </div>
        );
      })}
    </div>
  );
}

function HBar({ items, colorMap }: { items: Array<{ label: string; count: number }>; colorMap?: Record<string, string> }) {
  if (!items.length) return <p className="text-ink-soft text-sm">No data yet.</p>;
  const max = Math.max(...items.map((i) => i.count), 1);
  const total = items.reduce((s, i) => s + i.count, 0);
  return (
    <div className="space-y-3">
      {items.map((item, i) => {
        const pct = total > 0 ? Math.round((item.count / total) * 100) : 0;
        return (
          <div key={i}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-ink capitalize">{item.label || "Unknown"}</span>
              <span className="text-ink-soft">{item.count} ({pct}%)</span>
            </div>
            <div className="bar-track">
              <div
                className="bar-track-fill"
                style={{
                  width: `${(item.count / max) * 100}%`,
                  background: colorMap?.[item.label] || undefined,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

const TABS = ["Overview", "Submissions", "Users", "Activity"] as const;
type Tab = (typeof TABS)[number];

export default function AnalyticsPage() {
  const { data: session } = useSession();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [days, setDays] = useState(14);
  const [tab, setTab] = useState<Tab>("Overview");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [countdown, setCountdown] = useState(30);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`/api/admin/analytics?days=${days}&limit=200`);
      if (!res.ok) throw new Error("Failed to load analytics.");
      const data = await res.json();
      setAnalytics(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load analytics.");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    if (autoRefresh) {
      setCountdown(30);
      intervalRef.current = setInterval(() => { loadData(); setCountdown(30); }, 30000);
      countdownRef.current = setInterval(() => setCountdown((c) => (c > 0 ? c - 1 : 30)), 1000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [autoRefresh, loadData]);

  const d = analytics;

  return (
    <div className="max-w-[1280px] mx-auto px-5 py-6">
      {/* Hero */}
      <section className="hero-gradient text-white rounded-[34px] p-8 shadow-lg">
        <div className="flex items-center gap-2.5 text-xs font-bold tracking-[0.14em] uppercase text-white/70">
          <span className="w-8 h-px bg-white/30" />
          Analytics
        </div>
        <h1 className="mt-4 font-display text-4xl md:text-5xl leading-[0.92] tracking-tight">
          Mirai portal <span className="italic text-sky">analytics</span>
        </h1>
        <p className="mt-3 text-white/70 max-w-[700px]">
          Submission velocity, user growth, status throughput, and portal activity.
        </p>
        <div className="flex flex-wrap gap-2.5 mt-5">
          <span className="inline-flex items-center gap-2 px-3 py-2.5 rounded-full border border-white/10 bg-white/5 text-sm font-bold">
            {session?.user ? `Signed in as ${session.user.name || session.user.email}` : "Checking..."}
          </span>
        </div>
      </section>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mt-6">
        <button
          onClick={() => setAutoRefresh(!autoRefresh)}
          className={`inline-flex items-center gap-1.5 px-4 py-2.5 rounded-full text-sm font-bold border transition-all ${
            autoRefresh
              ? "bg-[rgba(52,199,160,0.12)] text-[#34c7a0] border-[rgba(52,199,160,0.3)]"
              : "bg-white/80 text-ink-soft border-[rgba(11,26,47,0.1)]"
          }`}
        >
          {autoRefresh ? `Live \u00B7 ${countdown}s` : "Auto-refresh"}
        </button>
        <button
          onClick={() => { setLoading(true); loadData(); }}
          className="px-4 py-2.5 rounded-full border border-[rgba(11,26,47,0.1)] bg-white/80 text-sm font-bold hover:-translate-y-0.5 transition-transform"
        >
          Refresh
        </button>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-4 py-2.5 rounded-full border border-[rgba(11,26,47,0.1)] bg-white/80 text-sm font-bold focus:outline-none focus:ring-2 focus:ring-[#196cff]/30"
        >
          <option value={7}>7 days</option>
          <option value={14}>14 days</option>
          <option value={30}>30 days</option>
          <option value={90}>90 days</option>
        </select>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mt-5 mb-6 overflow-x-auto border-b border-[rgba(11,26,47,0.08)]">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-3 text-sm font-bold rounded-t-[12px] transition-all whitespace-nowrap ${
              tab === t
                ? "text-[#196cff] bg-[rgba(25,108,255,0.08)] border-b-2 border-[#196cff]"
                : "text-ink-soft hover:text-ink hover:bg-white/40"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {error && (
        <div className="p-4 rounded-[18px] border border-red-200 bg-red-50 text-red-800 mb-6">{error}</div>
      )}

      {loading && !d && (
        <div className="flex items-center justify-center py-20 text-ink-soft">Loading analytics...</div>
      )}

      {/* ===== OVERVIEW ===== */}
      {d && tab === "Overview" && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <StatCard label="Submissions" value={d.totals.submissions ?? 0} meta="Total requests" />
            <StatCard label="Queued" value={d.totals.queued ?? 0} meta="Waiting review" accent="#f3b13f" />
            <StatCard label="Reviewing" value={d.totals.reviewing ?? 0} meta="In progress" accent="#196cff" />
            <StatCard label="Sent" value={d.totals.report_sent ?? 0} meta="Reports delivered" accent="#34c7a0" />
            <StatCard label="Last 7d" value={d.totals.submissions_last_7d ?? 0} meta="Recent volume" />
            <StatCard label="Completion" value={`${d.totals.completion_rate ?? 0}%`} meta={`${d.totals.unique_requesters ?? 0} requesters`} />
          </div>

          {/* Velocity Chart */}
          <div className="mt-6 p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
            <h2 className="text-lg font-bold tracking-tight">Submission Velocity</h2>
            <p className="text-sm text-ink-soft mt-1">Daily request volume, last {days} days.</p>
            <div className="mt-4">
              <BarChart
                rows={d.daily_submissions.map((r) => ({ label: r.date.slice(5), value: r.count }))}
              />
            </div>
          </div>

          {/* Breakdowns */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mt-6">
            <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
              <h3 className="font-bold text-sm mb-3">Status Breakdown</h3>
              <HBar items={d.status_breakdown} colorMap={STATUS_COLORS} />
            </div>
            <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
              <h3 className="font-bold text-sm mb-3">Industry Breakdown</h3>
              <HBar items={d.industry_breakdown} />
            </div>
            <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
              <h3 className="font-bold text-sm mb-3">Stage Breakdown</h3>
              <HBar items={d.stage_breakdown} />
            </div>
          </div>

          {/* Hourly if available */}
          {d.hourly_submissions && d.hourly_submissions.length > 0 && (
            <div className="mt-6 p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
              <h2 className="text-lg font-bold tracking-tight">Submissions by Hour (UTC)</h2>
              <p className="text-sm text-ink-soft mt-1">When users submit requests.</p>
              <div className="mt-4">
                <BarChart
                  rows={d.hourly_submissions.map((r) => ({ label: `${r.hour}:00`, value: r.count }))}
                  height={160}
                />
              </div>
            </div>
          )}

            <div className="mt-6">
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-4">
                <StatCard label="Backend Runs" value={d.backend?.total_runs ?? 0} meta="Completed analyses" />
                <StatCard label="Avg Runtime" value={formatDuration(d.backend?.avg_duration_s)} meta="Per completed run" accent="#196cff" />
                <StatCard label="Research Q" value={formatScore01(d.backend?.avg_research_quality_score)} meta="Average evidence quality" accent="#0f7b6c" />
                <StatCard label="Degraded" value={d.backend?.degraded_runs ?? 0} meta="Warnings or missing report" accent="#f3b13f" />
                <StatCard label="Low Evidence" value={d.backend?.low_research_runs ?? 0} meta="Research quality below threshold" accent="#b45309" />
                <StatCard label="Report Fail" value={d.backend?.report_failures ?? 0} meta="Missing or failed report output" accent="#dc2626" />
                <StatCard label="LLM Preview" value={d.backend?.llm_preview_runs ?? 0} meta="Admin-only comparisons" />
                <StatCard label="Needs Info" value={d.backend?.needs_info_runs ?? 0} meta="Incomplete inputs" />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mt-6">
                <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
                  <h3 className="font-bold text-sm mb-3">Renderer Breakdown</h3>
                  <HBar items={d.backend?.renderer_breakdown || []} />
                </div>
                <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
                  <h3 className="font-bold text-sm mb-3">Enhancement Coverage</h3>
                  <HBar items={d.backend?.enhancement_coverage || []} />
                </div>
                <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
                  <h3 className="font-bold text-sm mb-3">Coverage Gaps</h3>
                  <HBar items={d.backend?.coverage_gap_breakdown || []} />
                </div>
              </div>

            <div className="mt-6 p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
              <h2 className="text-lg font-bold tracking-tight">Recent Backend Diagnostics</h2>
              <p className="text-sm text-ink-soft mt-1">Admin-only run telemetry from the real `/api/bi/analyze` pipeline.</p>
              {d.backend?.recent_degraded_runs?.length ? (
                <div className="mt-4 space-y-3">
                  {d.backend.recent_degraded_runs.map((run, i) => (
                    <article key={`${run.ts}-${i}`} className="p-4 rounded-[18px] border border-[rgba(11,26,47,0.08)] bg-white/90">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <strong className="block text-sm">{run.company || run.industry || "Analysis run"}</strong>
                          <span className="block mt-1 text-xs text-ink-soft">
                            {run.verdict || "No verdict"} • {run.renderer_used || "legacy"} • {formatDuration(run.duration_s)} • research {formatScore01(run.research_quality_score)}
                          </span>
                        </div>
                        <span className="text-xs text-ink-faint whitespace-nowrap">{formatDate(run.ts)}</span>
                      </div>
                      <div className="flex flex-wrap gap-2 mt-3">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-bold bg-[rgba(243,177,63,0.16)] text-[#8a5a00]">
                          {run.warning_count} warning{run.warning_count === 1 ? "" : "s"}
                        </span>
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-bold bg-[rgba(11,26,47,0.06)] text-ink-soft">
                          report: {run.report_generation_status || "unknown"}
                        </span>
                        {typeof run.research_quality_score === "number" && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-bold bg-[rgba(15,123,108,0.12)] text-[#0f7b6c]">
                            research: {formatScore01(run.research_quality_score)}
                          </span>
                        )}
                        {run.llm_preview_status === "generated" && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-bold bg-[rgba(25,108,255,0.12)] text-[#196cff]">
                            llm preview ready
                          </span>
                        )}
                      </div>
                      {run.low_coverage_dimensions?.length ? (
                        <p className="mt-3 text-sm text-ink-soft">
                          Low coverage: {run.low_coverage_dimensions.slice(0, 4).join(", ")}
                        </p>
                      ) : null}
                      {run.top_warning && (
                        <p className="mt-3 text-sm text-ink-soft">{run.top_warning}</p>
                      )}
                    </article>
                  ))}
                </div>
              ) : (
                <p className="text-ink-soft text-sm mt-4">No degraded backend runs in the selected window.</p>
              )}
            </div>
          </div>
        </>
      )}

      {/* ===== SUBMISSIONS ===== */}
      {d && tab === "Submissions" && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard label="Total" value={d.totals.submissions ?? 0} meta="All time" />
            <StatCard label="Queued" value={d.totals.queued ?? 0} meta="Pending" accent="#f3b13f" />
            <StatCard label="Report Sent" value={d.totals.report_sent ?? 0} meta="Completed" accent="#34c7a0" />
            <StatCard label="Completion" value={`${d.totals.completion_rate ?? 0}%`} meta="Delivery rate" />
          </div>

          <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
            <h2 className="text-lg font-bold tracking-tight mb-4">Submission Velocity</h2>
            <BarChart rows={d.daily_submissions.map((r) => ({ label: r.date.slice(5), value: r.count }))} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mt-6">
            <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
              <h3 className="font-bold mb-3">By Industry</h3>
              <HBar items={d.industry_breakdown} />
            </div>
            <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
              <h3 className="font-bold mb-3">By Stage</h3>
              <HBar items={d.stage_breakdown} />
            </div>
          </div>
        </>
      )}

      {/* ===== USERS ===== */}
      {d && tab === "Users" && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <StatCard label="Unique Requesters" value={d.totals.unique_requesters ?? 0} meta="Who submitted" />
            <StatCard label="Submissions" value={d.totals.submissions ?? 0} meta="Total" />
            <StatCard label="Avg / User" value={d.totals.unique_requesters ? (d.totals.submissions / d.totals.unique_requesters).toFixed(1) : "0"} meta="Submissions per user" />
          </div>

          {d.users && d.users.length > 0 && (
            <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
              <h2 className="text-lg font-bold tracking-tight mb-4">Registered Users</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-ink-soft border-b border-[rgba(11,26,47,0.08)]">
                      <th className="pb-2 font-bold">Name</th>
                      <th className="pb-2 font-bold">Email</th>
                      <th className="pb-2 font-bold">Role</th>
                      <th className="pb-2 font-bold text-right">Submissions</th>
                      <th className="pb-2 font-bold">Joined</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[rgba(11,26,47,0.06)]">
                    {d.users.map((u) => (
                      <tr key={u.id} className="hover:bg-white/60 transition-colors">
                        <td className="py-2.5 font-medium">{u.name || "—"}</td>
                        <td className="py-2.5 text-ink-soft">{u.email}</td>
                        <td className="py-2.5">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold ${
                            u.isAdmin ? "bg-[rgba(25,108,255,0.12)] text-[#196cff]" : "bg-[rgba(11,26,47,0.06)] text-ink-soft"
                          }`}>
                            {u.isAdmin ? "Admin" : "User"}
                          </span>
                        </td>
                        <td className="py-2.5 text-right font-bold">{u.submissionCount}</td>
                        <td className="py-2.5 text-ink-soft text-xs">{timeAgo(u.createdAt)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* ===== ACTIVITY ===== */}
      {d && tab === "Activity" && (
        <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
          <h2 className="text-lg font-bold tracking-tight mb-4">Recent Portal Events</h2>
          {d.recent_events.length === 0 ? (
            <p className="text-ink-soft text-sm py-6 text-center">No events yet.</p>
          ) : (
            <div className="space-y-3">
              {d.recent_events.map((ev, i) => (
                <article key={i} className="p-4 rounded-[18px] border border-[rgba(11,26,47,0.08)] bg-white/90 hover:shadow-sm transition-shadow">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <strong className="block text-sm capitalize">{ev.event.replace(/_/g, " ")}</strong>
                      <span className="block mt-1 text-xs text-ink-soft">
                        {ev.company || ev.industry || "Portal event"}
                      </span>
                    </div>
                    <span className="text-xs text-ink-faint whitespace-nowrap">{formatDate(ev.ts)}</span>
                  </div>
                  {(ev.renderer_used || ev.duration_s || ev.warning_count || ev.top_warning || ev.verdict || ev.score != null) && (
                    <div className="mt-3">
                      <div className="flex flex-wrap gap-2">
                        {ev.renderer_used && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-bold bg-[rgba(11,26,47,0.06)] text-ink-soft">
                            renderer: {ev.renderer_used}
                          </span>
                        )}
                        {ev.duration_s != null && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-bold bg-[rgba(25,108,255,0.12)] text-[#196cff]">
                            runtime: {formatDuration(ev.duration_s)}
                          </span>
                        )}
                        {typeof ev.research_quality_score === "number" && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-bold bg-[rgba(15,123,108,0.12)] text-[#0f7b6c]">
                            research: {formatScore01(ev.research_quality_score)}
                          </span>
                        )}
                        {typeof ev.warning_count === "number" && ev.warning_count > 0 && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-bold bg-[rgba(243,177,63,0.16)] text-[#8a5a00]">
                            {ev.warning_count} warning{ev.warning_count === 1 ? "" : "s"}
                          </span>
                        )}
                        {ev.report_generation_status && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-bold bg-[rgba(11,26,47,0.06)] text-ink-soft">
                            report: {ev.report_generation_status}
                          </span>
                        )}
                        {ev.verdict && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-[11px] font-bold bg-[rgba(52,199,160,0.12)] text-[#1b8f73]">
                            {ev.verdict}{typeof ev.score === "number" ? ` • ${ev.score.toFixed(1)}` : ""}
                          </span>
                        )}
                      </div>
                      {ev.low_coverage_dimensions?.length ? (
                        <p className="mt-3 text-sm text-ink-soft">
                          Low coverage: {ev.low_coverage_dimensions.slice(0, 4).join(", ")}
                        </p>
                      ) : null}
                      {ev.top_warning && (
                        <p className="mt-3 text-sm text-ink-soft">{ev.top_warning}</p>
                      )}
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
