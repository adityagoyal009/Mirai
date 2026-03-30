import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions, GOOGLE_CONFIGURED } from "@/lib/auth";

export async function GET() {
  const session = await getServerSession(authOptions);

  if (session?.user) {
    return NextResponse.json({
      authenticated: true,
      google_oauth_configured: GOOGLE_CONFIGURED,
      user: {
        name: session.user.name || "",
        email: session.user.email || "",
        is_admin: session.user.isAdmin ?? false,
      },
    });
  }

  return NextResponse.json({
    authenticated: false,
    google_oauth_configured: GOOGLE_CONFIGURED,
    user: null,
  });
}
