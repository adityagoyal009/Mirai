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
  });

  const submissions = subs.map(serializeFounderSubmission);

  const totals = {
    total: subs.length,
    queued: subs.filter((s) => s.status === "queued").length,
    reviewing: subs.filter((s) => s.status === "reviewing").length,
    report_sent: subs.filter((s) => s.status === "report_sent").length,
  };

  return NextResponse.json({ submissions, totals });
}
