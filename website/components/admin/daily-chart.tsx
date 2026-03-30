"use client";

interface Props {
  rows: Array<{ date: string; count: number }>;
}

export default function DailyChart({ rows }: Props) {
  if (!rows.length) {
    return <p className="mt-4 text-ink-soft text-sm p-4 rounded-[18px] border border-dashed border-slate-200 bg-white/60">No submissions yet.</p>;
  }

  const max = Math.max(...rows.map((r) => r.count), 1);

  return (
    <div
      className="mt-4 grid items-end gap-2.5"
      style={{
        gridTemplateColumns: `repeat(${rows.length}, minmax(28px, 1fr))`,
        minHeight: 220,
      }}
    >
      {rows.map((r) => {
        const height = Math.max(12, Math.round((r.count / max) * 180));
        return (
          <div key={r.date} className="flex flex-col items-center gap-2.5">
            <strong className="text-xs">{r.count}</strong>
            <div className="chart-bar w-full" style={{ height }} />
            <span className="text-xs text-ink-soft">{r.date.slice(5)}</span>
          </div>
        );
      })}
    </div>
  );
}
