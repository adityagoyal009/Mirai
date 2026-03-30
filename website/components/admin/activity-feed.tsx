import { formatDate } from "@/lib/utils";

interface Event {
  event: string;
  company: string;
  industry: string;
  ts: string;
}

export default function ActivityFeed({ events }: { events: Event[] }) {
  if (!events.length) {
    return (
      <div className="mt-4 p-4 rounded-[18px] border border-dashed border-slate-200 bg-white/60 text-ink-soft text-sm">
        No recent portal events.
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-3">
      {events.map((ev, i) => (
        <article key={i} className="p-3.5 rounded-[18px] border border-[rgba(11,26,47,0.1)] bg-white/90">
          <strong className="block text-sm">{ev.event}</strong>
          <span className="block mt-1.5 text-xs text-ink-soft">
            {ev.company || ev.industry || "Portal event"} &middot; {formatDate(ev.ts)}
          </span>
        </article>
      ))}
    </div>
  );
}
