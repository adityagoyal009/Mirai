import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const subs = await prisma.submission.findMany({
    where: { userId: session.user.id },
    orderBy: { createdAt: "desc" },
  });

  return NextResponse.json({
    submissions: subs.map((s) => ({
      id: s.id,
      company_name: s.companyName,
      one_liner: s.oneLiner,
      status: s.status,
      admin_notes: s.adminNotes,
      created_at: s.createdAt.toISOString(),
    })),
  });
}
