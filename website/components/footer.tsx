import Link from "next/link";

export default function Footer() {
  return (
    <footer className="px-5 py-8 max-w-[1280px] mx-auto w-full">
      <div className="flex items-center justify-between gap-5 pt-6 border-t border-slate-200/60 text-slate-500 text-sm flex-wrap">
        <div>
          <strong className="block tracking-[0.14em] text-slate-700">MIRAI</strong>
          <span>AI due diligence for startup evaluation.</span>
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <Link href="/signin" className="hover:text-[#196cff] transition-colors">Sign In</Link>

        </div>
      </div>
    </footer>
  );
}
