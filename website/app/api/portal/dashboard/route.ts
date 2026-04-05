import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import { serializeFounderSubmission } from "@/lib/utils";

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const userId = session.user.id;

  const subs = await prisma.submission.findMany({
    where: { userId },
    orderBy: { createdAt: "desc" },
    include: {
      followUps: { where: { status: "pending" }, orderBy: { dueAt: "asc" }, take: 1 },
      outcomes: { select: { id: true } },
    },
  });

  const now = new Date();
  const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

  const submissions = subs.map((s) => {
    const base = serializeFounderSubmission(s);
    const nextFollowUp = s.followUps[0];
    const analysisOldEnough = s.status === "report_sent" && s.createdAt < thirtyDaysAgo;
    return {
      ...base,
      has_pending_follow_up: nextFollowUp ? nextFollowUp.dueAt <= now : false,
      can_report_outcome: analysisOldEnough,
      outcomes_reported: s.outcomes.length,
    };
  });

  const totals = {
    total: subs.length,
    queued: subs.filter((s) => s.status === "queued").length,
    reviewing: subs.filter((s) => s.status === "reviewing").length,
    report_sent: subs.filter((s) => s.status === "report_sent").length,
  };

  return NextResponse.json({ submissions, totals });
}
