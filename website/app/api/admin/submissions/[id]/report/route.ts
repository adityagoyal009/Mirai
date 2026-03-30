import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

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

  const existing = await prisma.submission.findUnique({ where: { id: submissionId } });
  if (!existing) {
    return NextResponse.json({ error: "Submission not found." }, { status: 404 });
  }

  const body = await request.json();
  const reportUrl = (body.reportUrl || "").trim();
  const score = body.score != null ? parseFloat(body.score) : null;
  const verdict = (body.verdict || "").trim();
  const adminNotes = body.adminNotes !== undefined ? (body.adminNotes || "").trim() : existing.adminNotes;

  const updated = await prisma.submission.update({
    where: { id: submissionId },
    data: {
      reportUrl,
      score: score != null && !isNaN(score) ? score : null,
      verdict,
      adminNotes,
      status: reportUrl ? "report_sent" : existing.status,
    },
  });

  await prisma.event.create({
    data: {
      event: reportUrl ? "report_attached" : "report_updated",
      submissionId: updated.id,
      userId: session.user.id,
      meta: JSON.stringify({
        company: updated.companyName,
        report_url: reportUrl,
        score,
        verdict,
      }),
    },
  });

  return NextResponse.json({
    message: reportUrl ? "Report attached and status set to report_sent." : "Report details updated.",
    submission: {
      id: updated.id,
      company_name: updated.companyName,
      status: updated.status,
      report_url: updated.reportUrl,
      score: updated.score,
      verdict: updated.verdict,
    },
  });
}
