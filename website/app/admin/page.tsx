"use client";

import { useSession } from "next-auth/react";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import StatsGrid from "@/components/admin/stats-grid";
import DailyChart from "@/components/admin/daily-chart";
import SubmissionsQueue from "@/components/admin/submissions-queue";
import ActivityFeed from "@/components/admin/activity-feed";


interface Analytics {
  totals: Record<string, number>;
  daily_submissions: Array<{ date: string; count: number }>;
  status_breakdown: Array<{ label: string; count: number }>;
  industry_breakdown: Array<{ label: string; count: number }>;
  stage_breakdown: Array<{ label: string; count: number }>;
  recent_events: Array<{ event: string; company: string; industry: string; ts: string }>;
}

interface Submission {
  id: number;
  company_name: string;
  one_liner: string;
  status: string;
  requester_name: string;
  requester_email: string;
  industry: string;
  stage: string;
  deck_url: string;
  admin_notes: string;
  created_at: string;
}

export default function AdminPage() {
  const { data: session } = useSession();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [analyticsRes, subsRes] = await Promise.all([
        fetch(`/api/admin/analytics?days=14&limit=100`),
        fetch(`/api/admin/submissions?limit=100&status=${encodeURIComponent(filter)}`),
      ]);

      if (!analyticsRes.ok || !subsRes.ok) {
        throw new Error("Failed to load admin data.");
      }

      const analyticsData = await analyticsRes.json();
      const subsData = await subsRes.json();

      setAnalytics(analyticsData);
      setSubmissions(subsData.submissions || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load admin board.");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="max-w-container-wide mx-auto px-5 py-6">
      {/* Hero */}
      <section className="hero-gradient text-white rounded-[34px] p-8 shadow-lg">
        <div className="flex items-center gap-2.5 text-xs font-bold tracking-[0.14em] uppercase text-white/70">
          <span className="w-8 h-px bg-white/30" />
          Admin only
        </div>
        <h1 className="mt-5 font-display text-4xl md:text-5xl leading-[0.92] tracking-tight">
          Landing-page intake <span className="italic text-sky">control room</span>
        </h1>
        <p className="mt-4 text-white/75 max-w-[780px]">
          Track public report requests, status throughput, and recent activity.
          Access restricted to admin emails.
        </p>
        <div className="flex flex-wrap gap-2.5 mt-5">
          <span className="inline-flex items-center gap-2 px-3 py-2.5 rounded-full border border-white/10 bg-white/5 text-sm font-bold">
            {session?.user
              ? `Signed in as ${session.user.name || session.user.email}`
              : "Checking admin session..."}
          </span>
          <Link
            href="/admin/analytics"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full border border-white/20 bg-white/10 text-sm font-bold hover:bg-white/20 transition-colors"
          >
            Analytics Dashboard
          </Link>
          <Link
            href="/analytics"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full border border-white/20 bg-white/10 text-sm font-bold hover:bg-white/20 transition-colors"
          >
            Site Analytics
          </Link>
        </div>
      </section>

      {/* Error */}
      {error && (
        <div className="mt-5 p-4 rounded-[18px] border border-red-200 bg-red-50 text-red-800">
          {error}
        </div>
      )}

      {/* Stats */}
      {analytics && <StatsGrid totals={analytics.totals} />}

      {/* Charts + Breakdowns */}
      {analytics && (
        <div className="grid grid-cols-1 lg:grid-cols-[1.15fr_0.85fr] gap-5 mt-5">
          <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
            <h2 className="text-lg font-bold tracking-tight">Submission Velocity</h2>
            <p className="text-sm text-ink-soft mt-1">Daily request volume, last 14 days.</p>
            <DailyChart rows={analytics.daily_submissions} />
          </div>
          <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
            <h2 className="text-lg font-bold tracking-tight">Breakdowns</h2>
            <p className="text-sm text-ink-soft mt-1">Queue shape by status, industry, stage.</p>
            <div className="mt-4 space-y-6">
              {[
                { title: "Statuses", rows: analytics.status_breakdown },
                { title: "Industries", rows: analytics.industry_breakdown },
                { title: "Stages", rows: analytics.stage_breakdown },
              ].map(({ title, rows }) => (
                <div key={title}>
                  <p className="font-bold text-sm mb-2">{title}</p>
                  {rows.length === 0 ? (
                    <p className="text-ink-soft text-sm">No data yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {rows.map((r) => {
                        const max = Math.max(...rows.map((x) => x.count), 1);
                        return (
                          <div key={r.label} className="grid grid-cols-[minmax(120px,1fr)_minmax(0,1fr)_36px] gap-3 items-center">
                            <span className="text-sm">{r.label}</span>
                            <div className="bar-track">
                              <div className="bar-track-fill" style={{ width: `${(r.count / max) * 100}%` }} />
                            </div>
                            <span className="text-sm text-ink-soft text-right">{r.count}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Submissions + Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-[1.15fr_0.85fr] gap-5 mt-5">
        <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
          <div className="flex items-center justify-between gap-4 mb-4">
            <div>
              <h2 className="text-lg font-bold tracking-tight">Requests Queue</h2>
              <p className="text-sm text-ink-soft">Review, update statuses, and keep notes.</p>
            </div>
            <button onClick={loadData} disabled={loading} className="btn-secondary text-sm !min-h-[40px] !px-4">
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-2.5 mb-4">
            {["", "queued", "reviewing", "report_sent", "archived"].map((st) => (
              <button
                key={st}
                onClick={() => setFilter(st)}
                className={`px-3.5 py-2 rounded-full text-sm font-bold border transition-all ${
                  filter === st
                    ? "text-white bg-gradient-to-br from-blue to-[#4b95ff] border-transparent"
                    : "text-ink-soft bg-white/80 border-[rgba(11,26,47,0.1)]"
                }`}
              >
                {st === "" ? "All" : st === "report_sent" ? "Report Sent" : st.charAt(0).toUpperCase() + st.slice(1)}
              </button>
            ))}
          </div>

          <SubmissionsQueue submissions={submissions} onRefresh={loadData} />
        </div>

        <div className="p-6 rounded-[30px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
          <h2 className="text-lg font-bold tracking-tight">Recent Activity</h2>
          <p className="text-sm text-ink-soft mt-1">Portal events and usage traces.</p>
          <ActivityFeed events={analytics?.recent_events || []} />
        </div>
      </div>
    </div>
  );
}
