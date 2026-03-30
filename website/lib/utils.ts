import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Submission, User } from "@prisma/client";
import { founderStatusMessage } from "./founder-status";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const VALID_STATUSES = ["queued", "reviewing", "report_sent", "archived"] as const;

export { INDUSTRY_OPTIONS as INDUSTRIES, STAGE_OPTIONS as STAGES } from "./form-options";

export function statusLabel(status: string): string {
  switch (status) {
    case "queued": return "Queued";
    case "reviewing": return "Reviewing";
    case "report_sent": return "Report Sent";
    case "archived": return "Archived";
    default: return "Unknown";
  }
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "Unknown time";
  const date = new Date(value);
  if (isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

/** Convert Prisma Submission (camelCase) to API response (snake_case). */
export function serializeSubmission(
  sub: Submission,
  user?: Pick<User, "name" | "email"> | null
) {
  return {
    id: sub.id,
    company_name: sub.companyName,
    website_url: sub.websiteUrl,
    industry: sub.industry,
    stage: sub.stage,
    one_liner: sub.oneLiner,
    customers: sub.customers,
    business_model: sub.businessModel,
    traction: sub.traction,
    deck_url: sub.deckUrl,
    advantage: sub.advantage,
    risk: sub.risk,
    status: sub.status,
    admin_notes: sub.adminNotes,
    created_at: sub.createdAt.toISOString(),
    updated_at: sub.updatedAt.toISOString(),
    ...(user
      ? { requester_name: user.name, requester_email: user.email }
      : {}),
  };
}

export function serializeFounderSubmission(sub: Submission) {
  return {
    id: sub.id,
    company_name: sub.companyName,
    one_liner: sub.oneLiner,
    industry: sub.industry,
    stage: sub.stage,
    status: sub.status,
    score: sub.score,
    verdict: sub.verdict,
    report_url: sub.reportUrl,
    status_message: founderStatusMessage(sub),
    created_at: sub.createdAt.toISOString(),
    updated_at: sub.updatedAt.toISOString(),
  };
}
