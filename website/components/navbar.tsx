"use client";

import { useSession, signOut } from "next-auth/react";
import Link from "next/link";

export default function Navbar() {
  const { data: session } = useSession();
  const user = session?.user;

  return (
    <nav className="flex items-center justify-between gap-4 px-5 py-4 max-w-[1280px] mx-auto w-full">
      <Link href="/" className="flex items-center gap-3">
        <span className="w-12 h-12 rounded-2xl grid place-items-center font-extrabold text-lg bg-gradient-to-br from-blue-100 to-orange-100 text-[#0f2440]">
          未来
        </span>
        <span>
          <strong className="block tracking-[0.14em] text-sm">MIRAI</strong>
          <span className="block text-xs text-slate-500 mt-0.5">AI due diligence</span>
        </span>
      </Link>

      <div className="flex items-center gap-3 flex-wrap">
        <Link
          href="/blog"
          className="px-4 py-2 rounded-full border border-slate-200 bg-white/80 text-sm font-bold hover:-translate-y-0.5 transition-transform"
        >
          Blog
        </Link>
        <Link
          href="/submit"
          className="px-4 py-2 rounded-full border border-slate-200 bg-white/80 text-sm font-bold hover:-translate-y-0.5 transition-transform"
        >
          Submit
        </Link>
        {user && (
          <Link
            href="/dashboard"
            className="px-4 py-2 rounded-full border border-slate-200 bg-white/80 text-sm font-bold hover:-translate-y-0.5 transition-transform"
          >
            Dashboard
          </Link>
        )}
        {user && (
          <span className="inline-flex items-center gap-2 px-3 py-2 rounded-full border border-slate-200 bg-white/80 text-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <strong className="truncate max-w-[160px]">{user.name || user.email}</strong>
          </span>
        )}
        {user?.isAdmin && (
          <Link
            href="/admin"
            className="px-4 py-2 rounded-full border border-slate-200 bg-white/80 text-sm font-bold hover:-translate-y-0.5 transition-transform"
          >
            Admin
          </Link>
        )}
        {user ? (
          <button
            onClick={() => signOut({ callbackUrl: "/" })}
            className="px-4 py-2 rounded-full border border-slate-200 bg-white/80 text-sm font-bold hover:-translate-y-0.5 transition-transform"
          >
            Sign Out
          </button>
        ) : (
          <Link
            href="/signin"
            className="px-5 py-2.5 rounded-full text-white font-bold text-sm bg-gradient-to-br from-[#196cff] to-[#4b95ff] shadow-lg shadow-blue-500/20 hover:-translate-y-0.5 transition-transform"
          >
            Sign In
          </Link>
        )}
      </div>
    </nav>
  );
}
