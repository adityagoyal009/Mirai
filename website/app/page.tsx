import Link from "next/link";

const pillars = [
  {
    title: "Evidence-heavy research",
    body: "Mirai does not stop at a one-shot model opinion. It runs structured web research, checks competitive claims, pulls market context, and pressures the case from multiple angles before scoring.",
  },
  {
    title: "Multi-layer judgment",
    body: "Council scoring, swarm pressure-testing, deterministic risk panels, and market trajectory simulation combine into one coherent verdict instead of a single brittle prompt result.",
  },
  {
    title: "Outcome-aware system",
    body: "Every analysis can be tracked, reviewed, calibrated, and compared over time. That makes Mirai an intelligence system, not just a report generator.",
  },
];

const buyerPoints = [
  "Should we take this meeting seriously?",
  "What are we missing behind the founder story?",
  "Where does this break under pressure?",
  "What would make this fundable in the next 6 to 12 months?",
];

const outputs = [
  "Founder-ready diligence report",
  "Structured risk panel across 10 domains",
  "Top fixes that increase fundability",
  "Comparable funded companies and pattern matches",
  "Admin-side outcome tracking for calibration",
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#f8fafc] text-slate-950">
      <section className="max-w-6xl mx-auto px-6 pt-20 pb-16">
        <div className="max-w-4xl">
          <div className="inline-flex items-center rounded-full border border-[#196cff]/20 bg-[#196cff]/5 px-4 py-1 text-xs font-semibold tracking-[0.18em] text-[#196cff] uppercase">
            VCLabs • Mirai Intelligence Engine
          </div>
          <h1 className="mt-6 text-5xl md:text-7xl font-semibold tracking-tight leading-[0.95]">
            AI due diligence that thinks like an investment committee, not a chatbot.
          </h1>
          <p className="mt-6 text-xl md:text-2xl text-slate-600 leading-relaxed max-w-3xl">
            Mirai evaluates startups through evidence-heavy research, council judgment, swarm pressure-testing, domain risk analysis, and market simulation to produce a verdict investors and founders can actually use.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <Link
              href="/submit"
              className="inline-flex items-center justify-center rounded-2xl bg-[#196cff] px-6 py-4 text-white font-semibold shadow-lg shadow-[#196cff]/20 transition hover:bg-[#1152d6]"
            >
              Submit a company
            </Link>
            <Link
              href="/signin"
              className="inline-flex items-center justify-center rounded-2xl border border-slate-300 bg-white px-6 py-4 font-semibold text-slate-800 transition hover:border-slate-400 hover:bg-slate-50"
            >
              Sign in
            </Link>
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-16 grid gap-6 md:grid-cols-2">
        <div className="rounded-3xl bg-white border border-slate-200 p-8 shadow-sm">
          <p className="text-sm font-semibold tracking-[0.16em] uppercase text-slate-500">Built for real decisions</p>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight">Mirai is for moments where conviction is expensive.</h2>
          <ul className="mt-6 space-y-4 text-slate-600 text-lg">
            {buyerPoints.map((point) => (
              <li key={point} className="flex gap-3">
                <span className="mt-1 h-2.5 w-2.5 rounded-full bg-[#196cff] shrink-0" />
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-3xl bg-slate-950 text-white p-8 shadow-sm">
          <p className="text-sm font-semibold tracking-[0.16em] uppercase text-slate-400">What you get</p>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight">A final report with pressure-tested judgment, not generic summary fluff.</h2>
          <ul className="mt-6 space-y-4 text-slate-300 text-lg">
            {outputs.map((item) => (
              <li key={item} className="flex gap-3">
                <span className="mt-1 h-2.5 w-2.5 rounded-full bg-cyan-400 shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-20">
        <div className="grid gap-6 md:grid-cols-3">
          {pillars.map((pillar) => (
            <div key={pillar.title} className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
              <h3 className="text-xl font-semibold tracking-tight">{pillar.title}</h3>
              <p className="mt-4 text-slate-600 leading-relaxed">{pillar.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="rounded-[2rem] border border-slate-200 bg-gradient-to-br from-white to-slate-100 p-10 md:p-14 shadow-sm">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold tracking-[0.16em] uppercase text-slate-500">Founder workflow</p>
            <h2 className="mt-4 text-4xl font-semibold tracking-tight">Submit once. Get a serious verdict, clear risks, and the fastest path to stronger investor readiness.</h2>
            <p className="mt-5 text-lg text-slate-600 leading-relaxed">
              The strongest products are not hard to copy because of UI. They are hard to copy because they accumulate evidence, judgment, calibration, and outcome data over time. Mirai is being built as that kind of system.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <Link
                href="/submit"
                className="inline-flex items-center justify-center rounded-2xl bg-slate-950 px-6 py-4 text-white font-semibold transition hover:bg-slate-800"
              >
                Start analysis
              </Link>
              <Link
                href="/dashboard"
                className="inline-flex items-center justify-center rounded-2xl border border-slate-300 bg-white px-6 py-4 font-semibold text-slate-800 transition hover:border-slate-400 hover:bg-slate-50"
              >
                View dashboard
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
