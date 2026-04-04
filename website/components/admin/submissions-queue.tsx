"use client";

import { useState } from "react";
import StatusPill from "@/components/ui/status-pill";
import { formatDate, VALID_STATUSES, statusLabel } from "@/lib/utils";

interface Submission {
  id: number;
  company_name: string;
  website_url: string;
  industry: string;
  stage: string;
  country: string;
  year_founded: string;
  one_liner: string;
  customers: string;
  end_user: string;
  economic_buyer: string;
  switching_trigger: string;
  business_model: string;
  current_substitute: string;
  pricing: string;
  pricing_model: string;
  starting_price: string;
  sales_motion: string;
  typical_contract_size: string;
  implementation_complexity: string;
  time_to_value: string;
  traction: string;
  pilot_count: string;
  loi_count: string;
  active_customer_count: string;
  paid_customer_count: string;
  monthly_revenue_value: string;
  growth_rate: string;
  has_customers: string;
  generating_revenue: string;
  currently_fundraising: string;
  revenue: string;
  funding: string;
  team: string;
  founder_problem_fit: string;
  founder_years_in_industry: string;
  technical_founder: string;
  advantage: string;
  competitors: string;
  primary_risk_category: string;
  risk: string;
  ask: string;
  extra_context: string;
  status: string;
  requester_name: string;
  requester_email: string;
  deck_url: string;
  demo_url: string;
  customer_proof_url: string;
  pilot_docs_url: string;
  industry_priority_areas: string;
  keywords: string;
  referral_source: string;
  admin_notes: string;
  report_url: string;
  score: number | null;
  verdict: string;
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

function InfoGrid({
  items,
}: {
  items: Array<{ label: string; value?: string | number | null }>;
}) {
  const visible = items.filter((item) => {
    if (item.value == null) return false;
    return String(item.value).trim().length > 0;
  });

  if (!visible.length) return null;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {visible.map((item) => (
        <div key={item.label} className="rounded-[16px] border border-[rgba(11,26,47,0.08)] bg-slate-50/80 px-4 py-3">
          <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-ink-faint">{item.label}</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-ink">{item.value}</p>
        </div>
      ))}
    </div>
  );
}

function LinkRow({ submission: sub }: { submission: Submission }) {
  const links = [
    { label: "Website", href: sub.website_url },
    { label: "Deck", href: sub.deck_url },
    { label: "Demo", href: sub.demo_url },
    { label: "Customer Proof", href: sub.customer_proof_url },
    { label: "Pilot Docs", href: sub.pilot_docs_url },
    { label: "Report", href: sub.report_url },
  ].filter((item) => item.href);

  if (!links.length) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {links.map((link) => (
        <a
          key={link.label}
          href={link.href}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center rounded-full border border-[rgba(25,108,255,0.18)] bg-[#196cff]/5 px-3 py-1.5 text-xs font-bold text-[#196cff] hover:bg-[#196cff]/10"
        >
          {link.label}
        </a>
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
        {[
          sub.requester_name || sub.requester_email,
          sub.requester_email,
          sub.industry,
          sub.stage,
          sub.country,
          sub.year_founded ? `Founded ${sub.year_founded}` : "",
          formatDate(sub.created_at),
        ].filter(Boolean).map((v, i) => (
          <span key={i} className="px-2.5 py-1.5 rounded-full bg-slate-100 text-ink-soft text-xs">{v}</span>
        ))}
      </div>

      <LinkRow submission={sub} />

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-[18px] border border-[rgba(11,26,47,0.08)] bg-slate-50/80 p-4">
          <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-ink-faint">Target Market & Pain</p>
          <p className="mt-1 text-sm text-ink whitespace-pre-wrap">{sub.customers || "Not provided."}</p>
        </div>
        <div className="rounded-[18px] border border-[rgba(11,26,47,0.08)] bg-slate-50/80 p-4">
          <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-ink-faint">Pressure-Test Ask</p>
          <p className="mt-1 text-sm text-ink whitespace-pre-wrap">{sub.ask || "Not provided."}</p>
        </div>
      </div>

      <details className="mt-4 overflow-hidden rounded-[20px] border border-[rgba(11,26,47,0.08)] bg-white/70">
        <summary className="cursor-pointer list-none px-4 py-3 text-sm font-bold text-ink">
          Full intake details
        </summary>
        <div className="space-y-4 border-t border-[rgba(11,26,47,0.08)] px-4 py-4">
          <InfoGrid
            items={[
              { label: "What Are You Building?", value: sub.one_liner },
              { label: "End User", value: sub.end_user },
              { label: "Economic Buyer", value: sub.economic_buyer },
              { label: "Why They Switch Now", value: sub.switching_trigger },
              { label: "Current Substitute", value: sub.current_substitute },
              { label: "Business Model", value: sub.business_model },
            ]}
          />

          <InfoGrid
            items={[
              { label: "Pricing", value: sub.pricing },
              { label: "Pricing Model", value: sub.pricing_model },
              { label: "Starting Price", value: sub.starting_price },
              { label: "Sales Motion", value: sub.sales_motion },
              { label: "Typical Contract Size", value: sub.typical_contract_size },
              { label: "Implementation Complexity", value: sub.implementation_complexity },
              { label: "Time To First Value", value: sub.time_to_value },
            ]}
          />

          <InfoGrid
            items={[
              { label: "Traction Notes", value: sub.traction },
              { label: "Pilots", value: sub.pilot_count },
              { label: "LOIs", value: sub.loi_count },
              { label: "Active Customers", value: sub.active_customer_count },
              { label: "Paid Customers", value: sub.paid_customer_count },
              { label: "Current Monthly Revenue", value: sub.monthly_revenue_value },
              { label: "Revenue / ARR", value: sub.revenue },
              { label: "Growth Rate", value: sub.growth_rate },
              { label: "Capital Raised", value: sub.funding },
              { label: "Have Customers?", value: sub.has_customers },
              { label: "Generating Revenue?", value: sub.generating_revenue },
              { label: "Currently Fundraising?", value: sub.currently_fundraising },
            ]}
          />

          <InfoGrid
            items={[
              { label: "Team", value: sub.team },
              { label: "Founder Fit", value: sub.founder_problem_fit },
              { label: "Years In Industry", value: sub.founder_years_in_industry },
              { label: "Technical Founder?", value: sub.technical_founder },
              { label: "Why You Win / Moat", value: sub.advantage },
            ]}
          />

          <InfoGrid
            items={[
              { label: "Known Competitors", value: sub.competitors },
              { label: "Main Risk Category", value: sub.primary_risk_category },
              { label: "What Could Break?", value: sub.risk },
              { label: "Evidence Links / Notes", value: sub.extra_context },
              { label: "Industry Priority Areas", value: sub.industry_priority_areas },
              { label: "Keywords", value: sub.keywords },
              { label: "Referral Source", value: sub.referral_source },
            ]}
          />
        </div>
      </details>

      {(sub.verdict || sub.score != null) && (
        <div className="mt-4 flex flex-wrap gap-2">
          {sub.verdict && (
            <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700">
              Verdict: {sub.verdict}
            </span>
          )}
          {sub.score != null && (
            <span className="rounded-full bg-sky-50 px-3 py-1.5 text-xs font-bold text-sky-700">
              Score: {sub.score.toFixed(1)}
            </span>
          )}
        </div>
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
