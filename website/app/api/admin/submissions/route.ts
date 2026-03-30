import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import { serializeSubmission, VALID_STATUSES } from "@/lib/utils";

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.isAdmin) {
    return NextResponse.json({ error: "Admin access required." }, { status: 403 });
  }

  const params = request.nextUrl.searchParams;
  const limit = parseInt(params.get("limit") || "100", 10);
  const statusFilter = (params.get("status") || "").trim();

  const where: Record<string, unknown> = {};
  if (statusFilter && (VALID_STATUSES as readonly string[]).includes(statusFilter)) {
    where.status = statusFilter;
  }

  const subs = await prisma.submission.findMany({
    where,
    include: { user: { select: { name: true, email: true } } },
    orderBy: { createdAt: "desc" },
    take: limit,
  });

  return NextResponse.json({
    submissions: subs.map((s) => serializeSubmission(s, s.user)),
  });
}
