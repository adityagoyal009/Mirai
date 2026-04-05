import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.isAdmin) {
    return NextResponse.json({ error: "Admin access required." }, { status: 403 });
  }

  const followUpId = parseInt(params.id, 10);
  if (isNaN(followUpId)) {
    return NextResponse.json({ error: "Invalid follow-up ID." }, { status: 400 });
  }

  const body = await request.json();
  const action = (body.action || "").trim();

  if (!["completed", "skipped"].includes(action)) {
    return NextResponse.json({ error: "action must be 'completed' or 'skipped'." }, { status: 400 });
  }

  const followUp = await prisma.followUp.findUnique({ where: { id: followUpId } });
  if (!followUp) {
    return NextResponse.json({ error: "Follow-up not found." }, { status: 404 });
  }

  const updated = await prisma.followUp.update({
    where: { id: followUpId },
    data: {
      status: action,
      completedAt: action === "completed" ? new Date() : null,
    },
  });

  return NextResponse.json({ follow_up: updated });
}
