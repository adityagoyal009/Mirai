"use client";

import { useSession } from "next-auth/react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

interface Submission {
  id: number;
  company_name: string;
  one_liner: string;
  industry: string;
  stage: string;
  status: string;
  score: number | null;
  verdict: string;
  report_url: string;
  admin_notes: string;
  created_at: string;
  updated_at: string;
}

interface QueueStatus {
  queueLength: number;
  processing: boolean;
  currentSubmissionId: number | null;
  pending: number[];
  dailyUsed: number;
  dailyLimit: number;
  dailyRemaining: number;
}

interface DashboardData {
  submissions: Submission[];
  totals: { total: number; queued: number; reviewing: number; report_sent: number };
}

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  queued: { label: "Queued", bg: "rgba(243,177,63,0.12)", text: "#b86a11", dot: "#f3b13f" },
  reviewing: { label: "In Review", bg: "rgba(25,108,255,0.1)", text: "#196cff", dot: "#196cff" },
  report_sent: { label: "Report Ready", bg: "rgba(52,199,160,0.12)", text: "#167c61", dot: "#34c7a0" },
  archived: { label: "Archived", bg: "rgba(110,127,151,0.1)", text: "#6e7f97", dot: "#6e7f97" },
};

function StatusPill({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.queued;
  return (
    <span
      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold"
      style={{ background: cfg.bg, color: cfg.text }}
    >
      <span className="w-2 h-2 rounded-full" style={{ background: cfg.dot }} />
      {cfg.label}
    </span>
  );
}

function formatDate(val: string): string {
  return new Date(val).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function timeAgo(val: string): string {
  const diff = Math.floor((Date.now() - new Date(val).getTime()) / 1000);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function DashboardPage() {
  const { data: session, status: authStatus } = useSession();
  const [data, setData] = useState<DashboardData | null>(null);
  const [queue, setQueue] = useState<QueueStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [dashRes, queueRes] = await Promise.all([
        fetch("/api/portal/dashboard"),
        fetch("/api/portal/queue"),
      ]);
      if (!dashRes.ok) throw new Error("Failed to load dashboard.");
      setData(await dashRes.json());
      if (queueRes.ok) setQueue(await queueRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authStatus === "authenticated") loadData();
  }, [authStatus, loadData]);

  // Auto-refresh every 15s when there are active analyses
  useEffect(() => {
    const hasActive = data?.submissions.some((s) => s.status === "queued" || s.status === "reviewing");
    if (!hasActive) return;
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [data, loadData]);

  if (authStatus === "loading" || (loading && !data)) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center text-ink-soft">
        Loading your dashboard...
      </div>
    );
  }

  const user = session?.user;
  const subs = data?.submissions || [];
  const totals = data?.totals || { total: 0, queued: 0, reviewing: 0, report_sent: 0 };
  const readyReports = subs.filter((s) => s.status === "report_sent" && s.report_url);

  return (
    <div className="max-w-[1080px] mx-auto px-5 py-8">
      {/* Hero */}
      <section className="hero-gradient text-white rounded-[34px] p-8 shadow-lg">
        <div className="flex items-center gap-2.5 text-xs font-bold tracking-[0.14em] uppercase text-white/70">
          <span className="w-8 h-px bg-white/30" />
          Your Dashboard
        </div>
        <h1 className="mt-4 font-display text-4xl md:text-5xl leading-[0.92] tracking-tight">
          Welcome back, <span className="text-sky italic">{user?.name?.split(" ")[0] || "there"}</span>
        </h1>
        <p className="mt-3 text-white/70 max-w-[600px]">
          Track your submitted companies, check evaluation status, and download completed reports.
        </p>
        <div className="flex flex-wrap gap-2.5 mt-5">
          <Link
            href="/submit"
            className="inline-flex items-center justify-center px-5 py-3 rounded-full font-bold text-[#0f2440] bg-white shadow-lg hover:-translate-y-0.5 transition-transform"
          >
            Submit New Company
          </Link>
          <button
            onClick={loadData}
            disabled={loading}
            className="inline-flex items-center justify-center px-5 py-3 rounded-full font-bold text-white border border-white/20 bg-white/10 hover:bg-white/20 transition-colors"
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </section>

      {error && (
        <div className="mt-5 p-4 rounded-[18px] border border-red-200 bg-red-50 text-red-800">{error}</div>
      )}

      {/* Queue Status Banner */}
      {queue && (queue.processing || queue.queueLength > 0) && (
        <div className="mt-5 p-4 rounded-[22px] border border-[rgba(25,108,255,0.2)] bg-[rgba(25,108,255,0.05)]">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#196cff] opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-[#196cff]" />
            </span>
            <div>
              <strong className="text-sm text-ink">
                {queue.processing ? "Analysis in progress" : "Queue active"}
              </strong>
              <span className="text-sm text-ink-soft ml-2">
                {queue.queueLength > 0
                  ? `${queue.queueLength} waiting in queue`
                  : "Processing current submission"}
              </span>
            </div>
          </div>
          <p className="mt-1.5 text-xs text-ink-faint ml-6">
            Dashboard auto-refreshes every 15 seconds while analyses are running.
            {queue.dailyRemaining != null && (
              <span className="ml-2">
                Daily capacity: {queue.dailyUsed}/{queue.dailyLimit} used ({queue.dailyRemaining} remaining)
              </span>
            )}
          </p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
        {[
          { label: "Total", value: totals.total, accent: undefined },
          { label: "Queued", value: totals.queued, accent: "#f3b13f" },
          { label: "In Review", value: totals.reviewing, accent: "#196cff" },
          { label: "Reports Ready", value: totals.report_sent, accent: "#34c7a0" },
        ].map((s) => (
          <div key={s.label} className="p-5 rounded-[26px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
            <span className="block text-xs font-bold tracking-[0.14em] uppercase text-ink-soft">{s.label}</span>
            <strong className="block mt-2 text-2xl tracking-tight" style={s.accent ? { color: s.accent } : {}}>
              {s.value}
            </strong>
          </div>
        ))}
      </div>

      {/* Reports Ready for Download */}
      {readyReports.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-bold tracking-tight mb-4 flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#34c7a0]" />
            Reports Ready
          </h2>
          <div className="grid gap-4">
            {readyReports.map((sub) => (
              <div
                key={sub.id}
                className="p-6 rounded-[30px] border border-[rgba(52,199,160,0.2)] bg-gradient-to-r from-[rgba(52,199,160,0.06)] to-white/85 shadow-lg"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                      <h3 className="text-lg font-bold tracking-tight">{sub.company_name}</h3>
                      {sub.score != null && (
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-bold bg-[rgba(25,108,255,0.1)] text-[#196cff]">
                          {sub.score.toFixed(1)}
                        </span>
                      )}
                      {sub.verdict && (
                        <span className="text-sm font-bold text-ink-soft">{sub.verdict}</span>
                      )}
                    </div>
                    <p className="mt-1.5 text-sm text-ink-soft truncate">{sub.one_liner}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-ink-faint">
                      {sub.industry && <span>{sub.industry}</span>}
                      {sub.stage && <span>{sub.stage}</span>}
                      <span>Submitted {formatDate(sub.created_at)}</span>
                    </div>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <a
                      href={sub.report_url}
                      target="_blank"
                      rel="noreferrer"
                      className="btn-primary !text-sm !min-h-[44px] !px-6"
                    >
                      View Report
                    </a>
                    <a
                      href={`${sub.report_url}?print=1`}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-[20px] border border-[rgba(11,26,47,0.15)] bg-white/80 px-5 min-h-[44px] flex items-center text-sm font-semibold text-ink hover:bg-white/95 transition-all"
                    >
                      Save PDF
                    </a>
                  </div>
                </div>
                {sub.admin_notes && (
                  <div className="mt-4 p-3.5 rounded-[16px] bg-white/80 border border-[rgba(11,26,47,0.06)] text-sm text-ink-soft">
                    <strong className="text-xs uppercase tracking-[0.08em] text-ink-faint block mb-1">Note from Mirai</strong>
                    {sub.admin_notes}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* All Submissions */}
      <section className="mt-8">
        <h2 className="text-lg font-bold tracking-tight mb-4">All Submissions</h2>
        {subs.length === 0 ? (
          <div className="p-8 rounded-[30px] border border-dashed border-[rgba(11,26,47,0.12)] bg-white/60 text-center">
            <p className="text-ink-soft">No submissions yet.</p>
            <Link href="/submit" className="btn-primary mt-4 !text-sm">
              Submit Your First Company
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {subs.map((sub) => (
              <article
                key={sub.id}
                className="p-5 rounded-[26px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg hover:-translate-y-0.5 transition-transform"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                      <h3 className="font-bold tracking-tight">{sub.company_name}</h3>
                      <StatusPill status={sub.status} />
                      {sub.status === "reviewing" && queue?.currentSubmissionId === sub.id && (
                        <span className="text-xs font-bold text-[#196cff] animate-pulse">Analyzing now...</span>
                      )}
                      {sub.status === "queued" && queue?.pending.includes(sub.id) && (
                        <span className="text-xs text-ink-faint">
                          Position {(queue.pending.indexOf(sub.id) + 1) + (queue.processing ? 1 : 0)} in queue
                        </span>
                      )}
                      {sub.score != null && (
                        <span className="text-sm font-bold text-[#196cff]">{sub.score.toFixed(1)}</span>
                      )}
                      {sub.verdict && (
                        <span className="text-sm text-ink-soft">{sub.verdict}</span>
                      )}
                    </div>
                    <p className="mt-1.5 text-sm text-ink-soft">{sub.one_liner}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-ink-faint flex-wrap">
                      {sub.industry && <span className="px-2 py-0.5 rounded-full bg-[rgba(11,26,47,0.04)]">{sub.industry}</span>}
                      {sub.stage && <span className="px-2 py-0.5 rounded-full bg-[rgba(11,26,47,0.04)]">{sub.stage}</span>}
                      <span>{formatDate(sub.created_at)}</span>
                      <span className="text-ink-faint">{timeAgo(sub.created_at)}</span>
                    </div>
                    {sub.admin_notes && (
                      <div className="mt-3 p-3 rounded-[14px] bg-[rgba(25,108,255,0.04)] border border-[rgba(25,108,255,0.08)] text-sm text-ink-soft">
                        {sub.admin_notes}
                      </div>
                    )}
                  </div>
                  {sub.status === "report_sent" && sub.report_url && (
                    <div className="flex gap-2 flex-shrink-0">
                      <a
                        href={sub.report_url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-primary !text-sm !min-h-[40px] !px-5"
                      >
                        View
                      </a>
                      <a
                        href={`${sub.report_url}?print=1`}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-[18px] border border-[rgba(11,26,47,0.15)] bg-white/80 px-4 min-h-[40px] flex items-center text-sm font-semibold text-ink hover:bg-white/95 transition-all"
                      >
                        PDF
                      </a>
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
