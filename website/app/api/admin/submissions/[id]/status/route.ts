import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import { serializeSubmission, VALID_STATUSES } from "@/lib/utils";

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.isAdmin) {
    return NextResponse.json({ error: "Admin access required." }, { status: 403 });
  }

  const body = await request.json();
  const newStatus = (body.status || "").trim();

  if (!(VALID_STATUSES as readonly string[]).includes(newStatus)) {
    return NextResponse.json(
      { error: `Invalid status. Must be: ${VALID_STATUSES.join(", ")}` },
      { status: 400 }
    );
  }

  const submissionId = parseInt(params.id, 10);
  if (isNaN(submissionId)) {
    return NextResponse.json({ error: "Invalid submission ID." }, { status: 400 });
  }

  const existing = await prisma.submission.findUnique({
    where: { id: submissionId },
    include: { user: { select: { name: true, email: true } } },
  });

  if (!existing) {
    return NextResponse.json({ error: "Submission not found." }, { status: 404 });
  }

  const oldStatus = existing.status;
  const adminNotes = (body.adminNotes || "").trim();

  const updated = await prisma.submission.update({
    where: { id: submissionId },
    data: { status: newStatus, adminNotes },
    include: { user: { select: { name: true, email: true } } },
  });

  await prisma.event.create({
    data: {
      event: "status_changed",
      submissionId: updated.id,
      userId: session.user.id,
      meta: JSON.stringify({
        company: updated.companyName,
        old_status: oldStatus,
        new_status: newStatus,
        admin_email: session.user.email,
      }),
    },
  });

  return NextResponse.json({
    submission: serializeSubmission(updated, updated.user),
  });
}
