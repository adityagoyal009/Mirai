import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

const VALID_OUTCOME_TYPES = [
  "raised_round",
  "revenue_milestone",
  "shut_down",
  "pivoted",
  "acquired",
  "operating",
  "stalled",
] as const;

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.isAdmin) {
    return NextResponse.json({ error: "Admin access required." }, { status: 403 });
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

  const body = await request.json();
  const outcomeType = (body.outcome_type || "").trim();

  if (!(VALID_OUTCOME_TYPES as readonly string[]).includes(outcomeType)) {
    return NextResponse.json(
      { error: `Invalid outcome_type. Must be: ${VALID_OUTCOME_TYPES.join(", ")}` },
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
      details: (body.details || "").trim(),
      verificationUrl: (body.verification_url || "").trim(),
      verified: Boolean(body.verified),
      roundType: (body.round_type || "").trim(),
      amountRaised: (body.amount_raised || "").trim(),
      revenueRange: (body.revenue_range || "").trim(),
      outcomeDate: (body.outcome_date || "").trim(),
      monthsAfterAnalysis: monthsAfter,
      recordedBy: "admin",
      recordedByUserId: (session.user as { id?: number }).id ?? null,
    },
  });

  await prisma.event.create({
    data: {
      event: "outcome_recorded",
      submissionId,
      meta: JSON.stringify({
        outcome_id: outcome.id,
        outcome_type: outcomeType,
        months_after: monthsAfter,
        recorded_by: "admin",
        company: submission.companyName,
      }),
    },
  });

  // Mark matching pending follow-up as completed if within range
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

  return NextResponse.json({ outcome, message: "Outcome recorded." });
}

export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.isAdmin) {
    return NextResponse.json({ error: "Admin access required." }, { status: 403 });
  }

  const submissionId = parseInt(params.id, 10);
  if (isNaN(submissionId)) {
    return NextResponse.json({ error: "Invalid submission ID." }, { status: 400 });
  }

  const outcomes = await prisma.outcome.findMany({
    where: { submissionId },
    orderBy: { createdAt: "desc" },
  });

  const analysisResult = await prisma.analysisResult.findUnique({
    where: { submissionId },
  });

  return NextResponse.json({ outcomes, analysisResult });
}
