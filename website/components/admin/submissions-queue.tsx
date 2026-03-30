"use client";

import { useState } from "react";
import StatusPill from "@/components/ui/status-pill";
import { formatDate, VALID_STATUSES, statusLabel } from "@/lib/utils";

interface Submission {
  id: number;
  company_name: string;
  one_liner: string;
  status: string;
  requester_name: string;
  requester_email: string;
  industry: string;
  stage: string;
  deck_url: string;
  admin_notes: string;
  created_at: string;
}

interface Props {
  submissions: Submission[];
  onRefresh: () => void;
}

export default function SubmissionsQueue({ submissions, onRefresh }: Props) {
  if (!submissions.length) {
    return (
      <div className="p-4 rounded-[18px] border border-dashed border-slate-200 bg-white/60 text-ink-soft text-sm">
        No submissions match this filter.
      </div>
    );
  }

  return (
    <div className="space-y-3.5">
      {submissions.map((sub) => (
        <SubmissionCard key={sub.id} submission={sub} onRefresh={onRefresh} />
      ))}
    </div>
  );
}

function SubmissionCard({ submission: sub, onRefresh }: { submission: Submission; onRefresh: () => void }) {
  const [status, setStatus] = useState(sub.status);
  const [notes, setNotes] = useState(sub.admin_notes);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function handleSave() {
    setSaving(true);
    setMessage("");
    try {
      const res = await fetch(`/api/admin/submissions/${sub.id}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, adminNotes: notes }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to update.");
      setMessage(`Updated to ${statusLabel(data.submission.status)}.`);
      onRefresh();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not update.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="p-5 rounded-[24px] border border-[rgba(11,26,47,0.1)] bg-white/90">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-bold tracking-tight">{sub.company_name}</h3>
          <p className="mt-2 text-ink-soft text-sm">{sub.one_liner || "No one-line pitch."}</p>
        </div>
        <StatusPill status={sub.status} />
      </div>

      <div className="flex flex-wrap gap-2 mt-3">
        {[sub.requester_name || sub.requester_email, sub.requester_email, sub.industry, sub.stage, formatDate(sub.created_at)].filter(Boolean).map((v, i) => (
          <span key={i} className="px-2.5 py-1.5 rounded-full bg-slate-100 text-ink-soft text-xs">{v}</span>
        ))}
      </div>

      {sub.deck_url && (
        <p className="mt-2">
          <a href={sub.deck_url} target="_blank" rel="noreferrer" className="text-blue text-sm hover:underline">
            Deck / data room link
          </a>
        </p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-[180px_1fr_auto] gap-3 items-start mt-4">
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="w-full rounded-[16px] border border-[rgba(11,26,47,0.1)] bg-white p-3 text-sm outline-none"
        >
          {VALID_STATUSES.map((s) => (
            <option key={s} value={s}>{statusLabel(s)}</option>
          ))}
        </select>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Internal notes..."
          className="w-full rounded-[16px] border border-[rgba(11,26,47,0.1)] bg-white p-3 text-sm outline-none min-h-[80px] resize-y"
        />
        <button onClick={handleSave} disabled={saving} className="btn-primary !min-h-[40px] text-sm">
          {saving ? "Saving..." : "Save"}
        </button>
      </div>

      {message && (
        <p className="mt-2 text-sm text-emerald-700">{message}</p>
      )}
    </article>
  );
}
