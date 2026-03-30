import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import { VALID_STATUSES } from "@/lib/utils";

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
    let meta: Record<string, string> = {};
    try { meta = JSON.parse(ev.meta); } catch {}
    return {
      event: ev.event,
      company: meta.company || "",
      industry: meta.industry || "",
      ts: ev.createdAt.toISOString(),
    };
  });

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
    users: userList,
    hourly_submissions: hourlySubmissions,
  });
}
