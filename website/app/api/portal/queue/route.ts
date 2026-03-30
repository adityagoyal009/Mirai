import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { analysisQueue } from "@/lib/analysis-queue";
import prisma from "@/lib/prisma";

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const activeSubs = await prisma.submission.findMany({
    where: {
      userId: session.user.id,
      status: { in: ["queued", "reviewing"] },
    },
    select: { id: true },
  });
  const queue = await analysisQueue.status();
  const positions = Object.fromEntries(
    activeSubs
      .map(({ id }) => [String(id), analysisQueue.positionOf(id)] as const)
      .filter(([, position]) => position >= 0)
  );

  return NextResponse.json({
    queueLength: queue.queueLength,
    processing: queue.processing,
    dailyUsed: queue.dailyUsed,
    dailyLimit: queue.dailyLimit,
    dailyRemaining: queue.dailyRemaining,
    positions,
  });
}
