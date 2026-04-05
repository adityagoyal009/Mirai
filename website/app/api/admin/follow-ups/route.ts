import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.isAdmin) {
    return NextResponse.json({ error: "Admin access required." }, { status: 403 });
  }

  const url = new URL(request.url);
  const status = url.searchParams.get("status") || "pending";
  const limit = Math.min(parseInt(url.searchParams.get("limit") || "50", 10), 200);

  const followUps = await prisma.followUp.findMany({
    where: { status },
    orderBy: { dueAt: "asc" },
    take: limit,
    include: {
      submission: {
        select: {
          id: true,
          companyName: true,
          industry: true,
          stage: true,
          score: true,
          verdict: true,
          createdAt: true,
        },
      },
    },
  });

  const now = new Date();
  const items = followUps.map((fu) => ({
    id: fu.id,
    submission_id: fu.submissionId,
    due_at: fu.dueAt.toISOString(),
    months_after: fu.monthsAfter,
    status: fu.status,
    overdue: fu.dueAt < now,
    company: fu.submission.companyName,
    industry: fu.submission.industry,
    stage: fu.submission.stage,
    score: fu.submission.score,
    verdict: fu.submission.verdict,
    analyzed_at: fu.submission.createdAt.toISOString(),
  }));

  const overdueCount = items.filter((i) => i.overdue).length;

  return NextResponse.json({ follow_ups: items, total: items.length, overdue_count: overdueCount });
}
