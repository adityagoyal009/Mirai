import { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import prisma from "./prisma";

const ADMIN_EMAILS = new Set(
  (process.env.MIRAI_ADMIN_EMAILS || "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean)
);

const GOOGLE_CONFIGURED =
  Boolean(process.env.GOOGLE_CLIENT_ID) &&
  Boolean(process.env.GOOGLE_CLIENT_SECRET);

export { GOOGLE_CONFIGURED };

const providers: NextAuthOptions["providers"] = [];

if (GOOGLE_CONFIGURED) {
  providers.push(
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      allowDangerousEmailAccountLinking: true,
    })
  );
}

export const authOptions: NextAuthOptions = {
  providers,
  session: { strategy: "jwt" },
  pages: { signIn: "/signin" },
  callbacks: {
    async signIn({ user, profile }) {
      const email = (user.email || profile?.email || "").toLowerCase().trim();
      if (!email) return false;

      const isAdmin = ADMIN_EMAILS.has(email);

      // Upsert user in database
      const dbUser = await prisma.user.upsert({
        where: { email },
        update: {
          name: user.name || profile?.name || "",
          picture: user.image || "",
          isAdmin,
        },
        create: {
          email,
          name: user.name || profile?.name || "",
          picture: user.image || "",
          isAdmin,
        },
      });

      // Log login event
      await prisma.event.create({
        data: {
          event: "user_login",
          userId: dbUser.id,
          meta: JSON.stringify({ email }),
        },
      });

      // Stash DB id + admin flag on the user object for jwt callback
      user.id = dbUser.id;
      user.isAdmin = isAdmin;
      return true;
    },

    async jwt({ token, user }) {
      if (user) {
        token.userId = user.id as number;
        token.isAdmin = user.isAdmin ?? false;
      }
      return token;
    },

    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.userId;
        session.user.isAdmin = token.isAdmin;
      }
      return session;
    },
  },
};
