import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

const FOUNDER_OUTCOME_TYPES = [
  "raised_round",
  "revenue_milestone",
  "shut_down",
  "pivoted",
  "operating",
] as const;

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const submissionId = parseInt(params.id, 10);
  if (isNaN(submissionId)) {
    return NextResponse.json({ error: "Invalid submission ID." }, { status: 400 });
  }

  const submission = await prisma.submission.findUnique({
    where: { id: submissionId },
  });
  if (!submission) {
    return NextResponse.json({ error: "Submission not found." }, { status: 404 });
  }
  if (submission.userId !== (session.user as { id?: number }).id) {
    return NextResponse.json({ error: "Not your submission." }, { status: 403 });
  }

  const body = await request.json();
  const outcomeType = (body.outcome_type || "").trim();

  if (!(FOUNDER_OUTCOME_TYPES as readonly string[]).includes(outcomeType)) {
    return NextResponse.json(
      { error: `Invalid outcome_type. Allowed: ${FOUNDER_OUTCOME_TYPES.join(", ")}` },
      { status: 400 }
    );
  }

  const now = new Date();
  const monthsAfter = Math.round(
    (now.getTime() - submission.createdAt.getTime()) / (30 * 24 * 60 * 60 * 1000)
  );

  const outcome = await prisma.outcome.create({
    data: {
      submissionId,
      outcomeType,
      details: (body.details || "").trim().slice(0, 2000),
      roundType: (body.round_type || "").trim(),
      amountRaised: (body.amount_raised || "").trim(),
      revenueRange: (body.revenue_range || "").trim(),
      monthsAfterAnalysis: monthsAfter,
      recordedBy: "founder",
      recordedByUserId: (session.user as { id?: number }).id ?? null,
      verified: false,
    },
  });

  await prisma.event.create({
    data: {
      event: "founder_outcome_reported",
      submissionId,
      meta: JSON.stringify({
        outcome_id: outcome.id,
        outcome_type: outcomeType,
        months_after: monthsAfter,
        company: submission.companyName,
      }),
    },
  });

  // Mark matching pending follow-up
  const pendingFollowUps = await prisma.followUp.findMany({
    where: { submissionId, status: "pending" },
    orderBy: { monthsAfter: "asc" },
  });
  for (const fu of pendingFollowUps) {
    if (monthsAfter >= fu.monthsAfter - 1) {
      await prisma.followUp.update({
        where: { id: fu.id },
        data: { status: "completed", completedAt: now },
      });
      break;
    }
  }

  return NextResponse.json({ outcome, message: "Thank you for the update!" });
}
