interface Props {
  totals: Record<string, number>;
}

export default function StatsGrid({ totals }: Props) {
  const cards = [
    { label: "Submissions", value: totals.submissions ?? 0, meta: "Total requests" },
    { label: "Queued", value: totals.queued ?? 0, meta: "Waiting review" },
    { label: "Reviewing", value: totals.reviewing ?? 0, meta: "In progress" },
    { label: "Sent", value: totals.report_sent ?? 0, meta: "Reports delivered" },
    { label: "Last 7d", value: totals.submissions_last_7d ?? 0, meta: "Recent volume" },
    {
      label: "Completion",
      value: `${totals.completion_rate ?? 0}%`,
      meta: `${totals.unique_requesters ?? 0} unique requesters`,
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mt-6">
      {cards.map((c) => (
        <div
          key={c.label}
          className="p-5 rounded-[26px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg"
        >
          <span className="block text-xs font-bold tracking-[0.14em] uppercase text-ink-soft">
            {c.label}
          </span>
          <strong className="block mt-2.5 text-2xl tracking-tight">{c.value}</strong>
          <em className="block mt-1.5 text-sm text-ink-soft not-italic">{c.meta}</em>
        </div>
      ))}
    </div>
  );
}
