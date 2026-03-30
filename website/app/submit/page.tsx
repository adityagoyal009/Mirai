"use client";

import { useSession, signIn } from "next-auth/react";
import Link from "next/link";
import { useState, useRef, useEffect } from "react";
import {
  INDUSTRY_OPTIONS,
  INDUSTRY_PRIORITY_OPTIONS,
  KEYWORD_OPTIONS,
  COUNTRY_OPTIONS,
  STAGE_OPTIONS,
  BUSINESS_MODEL_OPTIONS,
  REVENUE_OPTIONS,
  FUNDING_OPTIONS,
  REFERRAL_SOURCE_OPTIONS,
} from "@/lib/form-options";

/* ── Field definition ──────────────────────────────────────────── */

interface Field {
  key: string;
  label: string;
  required: boolean;
  placeholder: string;
  type: "text" | "url" | "select" | "searchable-select" | "multiselect" | "radio" | "textarea";
  options?: readonly string[];
  half?: boolean;
  maxSelections?: number;
  hint?: string;
}

const FIELDS: Field[] = [
  { key: "companyName", label: "Company Name", required: true, placeholder: "Acme Corp", type: "text", half: true },
  { key: "websiteUrl", label: "Website URL", required: false, placeholder: "https://example.com", type: "url", half: true },
  { key: "industry", label: "Industry", required: true, placeholder: "Search industries...", type: "searchable-select", half: true, options: INDUSTRY_OPTIONS },
  { key: "stage", label: "Stage", required: true, placeholder: "", type: "select", half: true, options: ["", ...STAGE_OPTIONS] },
  { key: "location", label: "City", required: false, placeholder: "San Francisco", type: "text", half: true },
  { key: "country", label: "Country", required: false, placeholder: "Search countries...", type: "searchable-select", half: true, options: COUNTRY_OPTIONS },
  { key: "yearFounded", label: "Year Founded", required: false, placeholder: "2024", type: "text", half: true },
  { key: "businessModel", label: "Business Model", required: true, placeholder: "", type: "select", half: true, options: ["", ...BUSINESS_MODEL_OPTIONS] },
  { key: "industryPriorityAreas", label: "Industry Priority Areas", required: false, placeholder: "Select priority areas...", type: "multiselect", options: INDUSTRY_PRIORITY_OPTIONS, hint: "Select all that apply." },
  { key: "oneLiner", label: "Product / Service", required: true, placeholder: "Describe the product, what it does, key differentiators, and how it works.", type: "textarea" },
  { key: "customers", label: "Target Market", required: true, placeholder: "Who buys this, why now, and what problem is painful enough to matter?", type: "textarea" },
  { key: "pricing", label: "Pricing Strategy", required: false, placeholder: "Tier breakdown, price points, free tier details...", type: "textarea" },
  { key: "traction", label: "Traction", required: false, placeholder: "Revenue, users, pilots, waitlist, growth, partnerships, LOIs...", type: "textarea" },
  { key: "hasCustomers", label: "Have Customers?", required: false, placeholder: "", type: "radio", half: true, options: ["Yes", "No"], hint: "Do you currently have customers using your product or service?" },
  { key: "generatingRevenue", label: "Generating Revenue?", required: false, placeholder: "", type: "radio", half: true, options: ["Yes", "No"], hint: "Is the company generating revenue?" },
  { key: "revenue", label: "Revenue / ARR", required: false, placeholder: "", type: "select", half: true, options: ["", ...REVENUE_OPTIONS] },
  { key: "funding", label: "Funding Raised", required: false, placeholder: "", type: "select", half: true, options: ["", ...FUNDING_OPTIONS] },
  { key: "currentlyFundraising", label: "Currently Fundraising?", required: false, placeholder: "", type: "radio", half: true, options: ["Yes", "No"] },
  { key: "team", label: "Team", required: false, placeholder: "Key team members, roles, relevant background...", type: "textarea" },
  { key: "ask", label: "Ask", required: false, placeholder: "What do you want assessed? Market viability, investor readiness, competitive landscape...", type: "text" },
  { key: "advantage", label: "Moat / Advantage", required: false, placeholder: "What makes this defensible? IP, network effects, data moat, speed...", type: "textarea" },
  { key: "competitors", label: "Known Competitors", required: false, placeholder: "List known competitors, separated by commas", type: "text" },
  { key: "deckUrl", label: "Pitch Deck URL", required: false, placeholder: "https://docsend.com/...", type: "url" },
  { key: "risk", label: "Key Risks", required: false, placeholder: "What could kill this? Sales cycle, regulation, incumbents...", type: "textarea" },
  { key: "keywords", label: "Keywords", required: false, placeholder: "Search keywords...", type: "multiselect", maxSelections: 15, options: KEYWORD_OPTIONS, hint: "Select up to 15 keywords that describe your business." },
  { key: "referralSource", label: "How did you hear about Mirai?", required: false, placeholder: "", type: "select", half: true, options: ["", ...REFERRAL_SOURCE_OPTIONS] },
  { key: "extraContext", label: "Additional Context", required: false, placeholder: "Paste your full pitch, exec summary, or any extra detail. This text is sent verbatim to the analysis.", type: "textarea" },
];

/* ── Shared styles ─────────────────────────────────────────────── */

const inputCls =
  "w-full rounded-[16px] border border-[rgba(11,26,47,0.12)] bg-white/80 px-4 py-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-[#196cff]/30 focus:border-[#196cff]/40 transition-all";

/* ── SearchableSelect ──────────────────────────────────────────── */

function SearchableSelect({
  id,
  value,
  onChange,
  options,
  placeholder,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  options: readonly string[];
  placeholder: string;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filtered = search
    ? options.filter((o) => o.toLowerCase().includes(search.toLowerCase()))
    : options;

  return (
    <div ref={ref} className="relative">
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={`${id}-listbox`}
        value={open ? search : value}
        onChange={(e) => { setSearch(e.target.value); if (!open) setOpen(true); }}
        onFocus={() => { setOpen(true); setSearch(""); }}
        placeholder={value || placeholder}
        className={inputCls}
        autoComplete="off"
      />
      {open && (
        <ul id={`${id}-listbox`} role="listbox" className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-[12px] border border-[rgba(11,26,47,0.1)] bg-white shadow-lg">
          {filtered.length === 0 && (
            <li className="px-4 py-2.5 text-sm text-ink-faint">No matches</li>
          )}
          {filtered.slice(0, 50).map((opt) => (
            <li
              key={opt}
              role="option"
              aria-selected={opt === value}
              tabIndex={0}
              onClick={() => { onChange(opt); setOpen(false); setSearch(""); }}
              onKeyDown={(e) => { if (e.key === "Enter") { onChange(opt); setOpen(false); setSearch(""); } }}
              className={`cursor-pointer px-4 py-2.5 text-sm hover:bg-[#196cff]/5 ${opt === value ? "bg-[#196cff]/10 font-medium" : ""}`}
            >
              {opt}
            </li>
          ))}
          {filtered.length > 50 && (
            <li className="px-4 py-2 text-xs text-ink-faint">
              Type to narrow {filtered.length - 50} more results...
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

/* ── MultiSelect ───────────────────────────────────────────────── */

function MultiSelect({
  id,
  value,
  onChange,
  options,
  placeholder,
  maxSelections,
  hint,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  options: readonly string[];
  placeholder: string;
  maxSelections?: number;
  hint?: string;
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  const selected = value ? value.split(", ").filter(Boolean) : [];
  const atLimit = maxSelections ? selected.length >= maxSelections : false;

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const toggle = (opt: string) => {
    let next: string[];
    if (opt === "None") {
      next = selected.includes("None") ? [] : ["None"];
    } else {
      const withoutNone = selected.filter((s) => s !== "None");
      next = withoutNone.includes(opt)
        ? withoutNone.filter((s) => s !== opt)
        : atLimit
          ? withoutNone
          : [...withoutNone, opt];
    }
    onChange(next.join(", "));
  };

  const remove = (opt: string) => {
    onChange(selected.filter((s) => s !== opt).join(", "));
  };

  const filtered = search
    ? options.filter((o) => o.toLowerCase().includes(search.toLowerCase()))
    : [...options];

  return (
    <div ref={ref} className="relative">
      {hint && <p className="text-xs text-ink-faint mb-1.5">{hint}</p>}

      {/* Selected tags */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {selected.map((s) => (
            <span
              key={s}
              className="inline-flex items-center gap-1 rounded-full bg-[#196cff]/10 px-2.5 py-1 text-xs font-medium text-[#196cff]"
            >
              {s}
              <button
                type="button"
                onClick={() => remove(s)}
                className="hover:text-red-500 font-bold"
              >
                x
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`${inputCls} text-left flex items-center justify-between`}
      >
        <span className={selected.length ? "text-ink" : "text-ink-faint"}>
          {selected.length
            ? `${selected.length} selected${maxSelections ? ` / ${maxSelections} max` : ""}`
            : placeholder}
        </span>
        <span className="text-ink-faint text-xs">{open ? "\u25B2" : "\u25BC"}</span>
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-[12px] border border-[rgba(11,26,47,0.1)] bg-white shadow-lg">
          <div className="p-2 border-b border-[rgba(11,26,47,0.06)]">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search..."
              className="w-full rounded-[10px] border border-[rgba(11,26,47,0.1)] px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#196cff]/30"
              autoFocus
            />
          </div>
          <ul id={`${id}-listbox`} role="listbox" aria-multiselectable="true" className="max-h-52 overflow-auto">
            {filtered.length === 0 && (
              <li className="px-4 py-2.5 text-sm text-ink-faint">No matches</li>
            )}
            {filtered.slice(0, 80).map((opt) => {
              const isSelected = selected.includes(opt);
              const isDisabled = atLimit && !isSelected;
              return (
                <li
                  key={opt}
                  role="option"
                  aria-selected={isSelected}
                  tabIndex={0}
                  onClick={() => !isDisabled && toggle(opt)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !isDisabled) toggle(opt); }}
                  className={`flex items-center gap-2.5 px-4 py-2 text-sm cursor-pointer
                    ${isDisabled ? "opacity-40 cursor-not-allowed" : "hover:bg-[#196cff]/5"}
                    ${isSelected ? "bg-[#196cff]/10 font-medium" : ""}`}
                >
                  <span className={`w-4 h-4 rounded border flex items-center justify-center text-[10px]
                    ${isSelected ? "bg-[#196cff] border-[#196cff] text-white" : "border-[rgba(11,26,47,0.2)]"}`}>
                    {isSelected && "\u2713"}
                  </span>
                  {opt}
                </li>
              );
            })}
            {filtered.length > 80 && (
              <li className="px-4 py-2 text-xs text-ink-faint">
                Type to narrow {filtered.length - 80} more results...
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

/* ── RadioGroup ────────────────────────────────────────────────── */

function RadioGroup({
  name,
  value,
  onChange,
  options,
  hint,
  legend,
}: {
  name: string;
  value: string;
  onChange: (v: string) => void;
  options: readonly string[];
  hint?: string;
  legend: string;
}) {
  return (
    <fieldset>
      <legend className="sr-only">{legend}</legend>
      {hint && <p className="text-xs text-ink-faint mb-2">{hint}</p>}
      <div className="flex gap-4">
        {options.map((opt) => (
          <label
            key={opt}
            className={`flex items-center gap-2 cursor-pointer rounded-[12px] border px-4 py-2.5 text-sm transition-all
              ${value === opt
                ? "border-[#196cff]/40 bg-[#196cff]/5 text-[#196cff] font-medium"
                : "border-[rgba(11,26,47,0.12)] bg-white/80 text-ink hover:border-[#196cff]/20"}`}
          >
            <input
              type="radio"
              name={name}
              value={opt}
              checked={value === opt}
              onChange={(e) => onChange(e.target.value)}
              className="sr-only"
            />
            <span className={`w-4 h-4 rounded-full border-2 flex items-center justify-center
              ${value === opt ? "border-[#196cff]" : "border-[rgba(11,26,47,0.2)]"}`}>
              {value === opt && <span className="w-2 h-2 rounded-full bg-[#196cff]" />}
            </span>
            {opt}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/* ── Main page ─────────────────────────────────────────────────── */

type FormData = Record<string, string>;

export default function SubmitPage() {
  const { data: session, status } = useSession();
  const [form, setForm] = useState<FormData>(
    Object.fromEntries(FIELDS.map((f) => [f.key, ""])) as FormData
  );
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  const update = (key: string, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Explicit validation for all required fields (including searchable-selects)
    const requiredFields = FIELDS.filter((f) => f.required);
    for (const f of requiredFields) {
      if (!form[f.key]?.trim()) {
        setResult({ ok: false, message: `${f.label} is required.` });
        return;
      }
    }

    setSubmitting(true);
    setResult(null);

    try {
      const res = await fetch("/api/portal/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Submission failed.");
      setResult({ ok: true, message: data.message || "Submitted successfully. Analysis is starting — check your dashboard." });
      setForm(Object.fromEntries(FIELDS.map((f) => [f.key, ""])) as FormData);
    } catch (err) {
      setResult({ ok: false, message: err instanceof Error ? err.message : "Something went wrong." });
    } finally {
      setSubmitting(false);
    }
  };

  if (status === "loading") {
    return <div className="min-h-[60vh] flex items-center justify-center text-ink-soft">Checking session...</div>;
  }

  if (!session?.user) {
    return (
      <div className="max-w-[640px] mx-auto px-5 py-16 text-center">
        <div className="p-8 rounded-[34px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg">
          <h1 className="text-2xl font-bold tracking-tight">Sign in to submit</h1>
          <p className="mt-3 text-ink-soft">
            Mirai requires a Google account to associate your submission with a real identity.
          </p>
          <button onClick={() => signIn("google", { callbackUrl: "/submit" })} className="btn-primary mt-6">
            Sign In With Google
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[820px] mx-auto px-5 py-8">
      <section className="hero-gradient text-white rounded-[34px] p-8 shadow-lg mb-8">
        <div className="flex items-center gap-2.5 text-xs font-bold tracking-[0.14em] uppercase text-white/70">
          <span className="w-8 h-px bg-white/30" />
          Submit for evaluation
        </div>
        <h1 className="mt-4 font-display text-4xl md:text-5xl leading-[0.92] tracking-tight">
          Tell us about the <span className="text-sky italic">startup</span>
        </h1>
        <p className="mt-4 text-white/70 max-w-[600px]">
          Fill in what you know. The more context you provide, the sharper the evaluation.
          Analysis starts automatically after submission.
        </p>
      </section>

      <form
        onSubmit={handleSubmit}
        className="p-8 rounded-[34px] border border-[rgba(11,26,47,0.1)] bg-white/85 shadow-lg"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-5">
          {FIELDS.map((f) => {
            const isFullWidth = !f.half;
            return (
              <div key={f.key} className={isFullWidth ? "sm:col-span-2" : ""}>
                <label htmlFor={f.key} className="block text-xs font-bold text-ink-faint uppercase tracking-[0.1em] mb-1.5">
                  {f.label}
                  {f.required && <span className="text-coral ml-1">*</span>}
                </label>

                {f.type === "searchable-select" ? (
                  <SearchableSelect
                    id={f.key}
                    value={form[f.key]}
                    onChange={(v) => update(f.key, v)}
                    options={f.options || []}
                    placeholder={f.placeholder}
                  />
                ) : f.type === "multiselect" ? (
                  <MultiSelect
                    id={f.key}
                    value={form[f.key]}
                    onChange={(v) => update(f.key, v)}
                    options={f.options || []}
                    placeholder={f.placeholder}
                    maxSelections={f.maxSelections}
                    hint={f.hint}
                  />
                ) : f.type === "radio" ? (
                  <RadioGroup
                    name={f.key}
                    value={form[f.key]}
                    onChange={(v) => update(f.key, v)}
                    options={f.options || []}
                    hint={f.hint}
                    legend={f.label}
                  />
                ) : f.type === "select" ? (
                  <select
                    id={f.key}
                    value={form[f.key]}
                    onChange={(e) => update(f.key, e.target.value)}
                    required={f.required}
                    className={inputCls}
                  >
                    {f.options?.map((opt) => (
                      <option key={opt} value={opt}>{opt || `Select ${f.label.toLowerCase()}...`}</option>
                    ))}
                  </select>
                ) : f.type === "textarea" ? (
                  <textarea
                    id={f.key}
                    value={form[f.key]}
                    onChange={(e) => update(f.key, e.target.value)}
                    placeholder={f.placeholder}
                    required={f.required}
                    rows={f.key === "extraContext" ? 5 : 3}
                    className={`${inputCls} resize-y`}
                  />
                ) : (
                  <input
                    id={f.key}
                    type={f.type}
                    value={form[f.key]}
                    onChange={(e) => update(f.key, e.target.value)}
                    placeholder={f.placeholder}
                    required={f.required}
                    className={inputCls}
                  />
                )}
              </div>
            );
          })}
        </div>

        {result && (
          <div className={`mt-5 p-4 rounded-[18px] border text-sm ${
            result.ok
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-red-200 bg-red-50 text-red-800"
          }`}>
            {result.message}
            {result.ok && (
              <Link href="/dashboard" className="block mt-2 font-bold text-emerald-700 hover:underline">
                Go to Dashboard →
              </Link>
            )}
          </div>
        )}

        <button type="submit" disabled={submitting} className="btn-primary w-full mt-6">
          {submitting ? "Submitting..." : "Submit for Evaluation"}
        </button>
      </form>
    </div>
  );
}
