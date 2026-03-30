import { cn, statusLabel } from "@/lib/utils";

const colors: Record<string, string> = {
  queued: "text-amber-700 bg-amber-50 border-amber-200",
  reviewing: "text-blue-600 bg-blue-50 border-blue-200",
  report_sent: "text-emerald-700 bg-emerald-50 border-emerald-200",
  archived: "text-slate-600 bg-slate-100 border-slate-200",
};

export default function StatusPill({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wide border",
        colors[status] || "text-slate-500 bg-slate-50 border-slate-200"
      )}
    >
      <span
        className={cn(
          "w-2 h-2 rounded-full",
          status === "queued" && "bg-amber-500",
          status === "reviewing" && "bg-blue-500",
          status === "report_sent" && "bg-emerald-500",
          status === "archived" && "bg-slate-400"
        )}
      />
      {statusLabel(status)}
    </span>
  );
}
