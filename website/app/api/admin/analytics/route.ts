import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import { VALID_STATUSES } from "@/lib/utils";

type EventMeta = Record<string, unknown>;

function parseEventMeta(raw: string): EventMeta {
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed as EventMeta : {};
  } catch {
    return {};
  }
}

function readString(meta: EventMeta, key: string): string {
  const value = meta[key];
  return typeof value === "string" ? value : "";
}

function readNumber(meta: EventMeta, key: string): number | null {
  const value = meta[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function readStringArray(meta: EventMeta, key: string): string[] {
  const value = meta[key];
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.isAdmin) {
    return NextResponse.json({ error: "Admin access required." }, { status: 403 });
  }

  const params = request.nextUrl.searchParams;
  const days = parseInt(params.get("days") || "14", 10);
  const limit = parseInt(params.get("limit") || "100", 10);
  const now = new Date();

  // Totals
  const total = await prisma.submission.count();

  const statusCounts: Record<string, number> = {};
  for (const st of VALID_STATUSES) {
    statusCounts[st] = await prisma.submission.count({ where: { status: st } });
  }

  const cutoff7d = new Date(now.getTime() - 7 * 86400000);
  const last7d = await prisma.submission.count({
    where: { createdAt: { gte: cutoff7d } },
  });

  const uniqueRequesters = await prisma.submission
    .findMany({ distinct: ["userId"], select: { userId: true } })
    .then((r) => r.length);

  const completionRate = total > 0
    ? Math.round(((statusCounts.report_sent || 0) / total) * 100)
    : 0;

  // Daily submissions (gap-filled)
  const cutoffDaily = new Date(now.getTime() - days * 86400000);
  const dailyRaw: Array<{ day: string; cnt: number }> = await prisma.$queryRawUnsafe(
    `SELECT substr(created_at, 1, 10) as day, COUNT(*) as cnt
     FROM submissions
     WHERE created_at >= ?
     GROUP BY day ORDER BY day`,
    cutoffDaily.toISOString()
  );

  const dailyMap = new Map(dailyRaw.map((r) => [r.day, Number(r.cnt)]));
  const dailySubmissions = [];
  for (let i = 0; i < days; i++) {
    const d = new Date(cutoffDaily.getTime() + i * 86400000);
    const key = d.toISOString().slice(0, 10);
    dailySubmissions.push({ date: key, count: dailyMap.get(key) || 0 });
  }

  // Breakdowns
  const statusBd = await prisma.submission.groupBy({
    by: ["status"],
    _count: { id: true },
    orderBy: { _count: { id: "desc" } },
  });

  const industryBd = await prisma.submission.groupBy({
    by: ["industry"],
    where: { industry: { not: "" } },
    _count: { id: true },
    orderBy: { _count: { id: "desc" } },
  });

  const stageBd = await prisma.submission.groupBy({
    by: ["stage"],
    where: { stage: { not: "" } },
    _count: { id: true },
    orderBy: { _count: { id: "desc" } },
  });

  // Recent events
  const events = await prisma.event.findMany({
    orderBy: { createdAt: "desc" },
    take: limit,
  });

  const recentEvents = events.map((ev) => {
    const meta = parseEventMeta(ev.meta);
    const warnings = readStringArray(meta, "warnings");
    const lowCoverageDimensions = readStringArray(meta, "low_coverage_dimensions");
    const missingEvidenceFlags = readStringArray(meta, "missing_evidence_flags");
    return {
      event: ev.event,
      company: readString(meta, "company"),
      industry: readString(meta, "industry"),
      ts: ev.createdAt.toISOString(),
      submission_id: ev.submissionId,
      renderer_used: readString(meta, "renderer_used"),
      report_generation_status: readString(meta, "report_generation_status"),
      duration_s: readNumber(meta, "duration_s"),
      warning_count: readNumber(meta, "warning_count") || 0,
      has_report: Boolean(meta.has_report),
      enhancement_keys: readStringArray(meta, "enhancement_keys"),
      llm_preview_status: readString(meta, "llm_preview_status"),
      top_warning: readString(meta, "top_warning") || warnings[0] || "",
      research_quality_score: readNumber(meta, "research_quality_score"),
      research_coverage_score: readNumber(meta, "research_coverage_score"),
      research_source_quality_score: readNumber(meta, "research_source_quality_score"),
      research_freshness_score: readNumber(meta, "research_freshness_score"),
      low_coverage_dimensions: lowCoverageDimensions,
      missing_evidence_flags: missingEvidenceFlags,
      audit_path: readString(meta, "audit_path"),
      verdict: readString(meta, "verdict"),
      score: readNumber(meta, "score"),
    };
  });

  const backendEvents = await prisma.event.findMany({
    where: {
      createdAt: { gte: cutoffDaily },
      event: { in: ["analysis_complete", "analysis_degraded", "analysis_failed", "analysis_needs_info"] },
    },
    orderBy: { createdAt: "desc" },
    take: Math.max(limit * 10, 500),
  });

  const backendRuns = backendEvents
    .filter((ev) => ev.event === "analysis_complete")
    .map((ev) => {
      const meta = parseEventMeta(ev.meta);
      const warnings = readStringArray(meta, "warnings");
      const lowCoverageDimensions = readStringArray(meta, "low_coverage_dimensions");
      const missingEvidenceFlags = readStringArray(meta, "missing_evidence_flags");
      return {
        ts: ev.createdAt.toISOString(),
        submission_id: ev.submissionId,
        company: readString(meta, "company"),
        industry: readString(meta, "industry"),
        renderer_used: readString(meta, "renderer_used") || "legacy",
        duration_s: readNumber(meta, "duration_s"),
        warning_count: readNumber(meta, "warning_count") || 0,
        has_report: Boolean(meta.has_report),
        report_generation_status: readString(meta, "report_generation_status") || "unknown",
        enhancement_keys: readStringArray(meta, "enhancement_keys"),
        llm_preview_status: readString(meta, "llm_preview_status") || "not_requested",
        top_warning: readString(meta, "top_warning") || warnings[0] || "",
        research_quality_score: readNumber(meta, "research_quality_score"),
        research_coverage_score: readNumber(meta, "research_coverage_score"),
        research_source_quality_score: readNumber(meta, "research_source_quality_score"),
        research_freshness_score: readNumber(meta, "research_freshness_score"),
        low_coverage_dimensions: lowCoverageDimensions,
        missing_evidence_flags: missingEvidenceFlags,
        audit_path: readString(meta, "audit_path"),
        verdict: readString(meta, "verdict"),
        score: readNumber(meta, "score"),
      };
    });

  const durations = backendRuns
    .map((run) => run.duration_s)
    .filter((value): value is number => typeof value === "number" && value > 0);
  const avgDuration = durations.length
    ? Math.round((durations.reduce((sum, value) => sum + value, 0) / durations.length) * 10) / 10
    : 0;
  const researchScores = backendRuns
    .map((run) => run.research_quality_score)
    .filter((value): value is number => typeof value === "number" && value >= 0);
  const avgResearchQuality = researchScores.length
    ? Math.round((researchScores.reduce((sum, value) => sum + value, 0) / researchScores.length) * 100) / 100
    : 0;
  const lowResearchRuns = backendRuns.filter(
    (run) =>
      (typeof run.research_quality_score === "number" && run.research_quality_score < 0.65) ||
      run.low_coverage_dimensions.length > 0
  );

  const degradedRuns = backendRuns.filter(
    (run) =>
      run.warning_count > 0 ||
      run.report_generation_status !== "success" ||
      !run.has_report ||
      (typeof run.research_quality_score === "number" && run.research_quality_score < 0.65)
  );

  const rendererCounts = new Map<string, number>();
  const enhancementCounts = new Map<string, number>();
  const coverageGapCounts = new Map<string, number>();
  let llmPreviewRuns = 0;
  let reportFailures = 0;
  for (const run of backendRuns) {
    rendererCounts.set(run.renderer_used, (rendererCounts.get(run.renderer_used) || 0) + 1);
    if (run.llm_preview_status === "generated") {
      llmPreviewRuns += 1;
    }
    if (run.report_generation_status !== "success" || !run.has_report) {
      reportFailures += 1;
    }
    for (const key of run.enhancement_keys) {
      enhancementCounts.set(key, (enhancementCounts.get(key) || 0) + 1);
    }
    for (const key of run.low_coverage_dimensions) {
      coverageGapCounts.set(key, (coverageGapCounts.get(key) || 0) + 1);
    }
  }

  const failedRuns = backendEvents.filter((ev) => ev.event === "analysis_failed").length;
  const needsInfoRuns = backendEvents.filter((ev) => ev.event === "analysis_needs_info").length;

  // Users with submission counts
  const users = await prisma.user.findMany({
    orderBy: { createdAt: "desc" },
    include: { _count: { select: { submissions: true } } },
  });

  const userList = users.map((u) => ({
    id: u.id,
    name: u.name,
    email: u.email,
    isAdmin: u.isAdmin,
    submissionCount: u._count.submissions,
    createdAt: u.createdAt.toISOString(),
  }));

  // Hourly submission distribution
  const hourlyRaw: Array<{ hour: string; cnt: number }> = await prisma.$queryRawUnsafe(
    `SELECT substr(created_at, 12, 2) as hour, COUNT(*) as cnt
     FROM submissions
     GROUP BY hour ORDER BY hour`
  );

  const hourlyMap = new Map(hourlyRaw.map((r) => [parseInt(r.hour, 10), Number(r.cnt)]));
  const hourlySubmissions = [];
  for (let h = 0; h < 24; h++) {
    hourlySubmissions.push({ hour: h, count: hourlyMap.get(h) || 0 });
  }

  return NextResponse.json({
    totals: {
      submissions: total,
      queued: statusCounts.queued || 0,
      reviewing: statusCounts.reviewing || 0,
      report_sent: statusCounts.report_sent || 0,
      archived: statusCounts.archived || 0,
      submissions_last_7d: last7d,
      completion_rate: completionRate,
      unique_requesters: uniqueRequesters,
    },
    daily_submissions: dailySubmissions,
    status_breakdown: statusBd.map((r) => ({ label: r.status, count: r._count.id })),
    industry_breakdown: industryBd.map((r) => ({ label: r.industry, count: r._count.id })),
    stage_breakdown: stageBd.map((r) => ({ label: r.stage, count: r._count.id })),
    recent_events: recentEvents,
    backend: {
      total_runs: backendRuns.length,
      avg_duration_s: avgDuration,
      avg_research_quality_score: avgResearchQuality,
      degraded_runs: degradedRuns.length,
      low_research_runs: lowResearchRuns.length,
      report_failures: reportFailures,
      llm_preview_runs: llmPreviewRuns,
      failed_runs: failedRuns,
      needs_info_runs: needsInfoRuns,
      legacy_renderer_runs: rendererCounts.get("legacy") || 0,
      llm_renderer_runs: rendererCounts.get("llm") || 0,
      renderer_breakdown: Array.from(rendererCounts.entries()).map(([label, count]) => ({ label, count })),
      enhancement_coverage: Array.from(enhancementCounts.entries())
        .sort((a, b) => b[1] - a[1])
        .map(([label, count]) => ({ label, count })),
      coverage_gap_breakdown: Array.from(coverageGapCounts.entries())
        .sort((a, b) => b[1] - a[1])
        .map(([label, count]) => ({ label, count })),
      recent_runs: backendRuns.slice(0, limit),
      recent_degraded_runs: degradedRuns.slice(0, Math.min(limit, 12)),
    },
    users: userList,
    hourly_submissions: hourlySubmissions,
  });
}
