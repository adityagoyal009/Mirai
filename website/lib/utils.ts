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
    country: sub.country,
    year_founded: sub.yearFounded,
    one_liner: sub.oneLiner,
    customers: sub.customers,
    end_user: sub.endUser,
    economic_buyer: sub.economicBuyer,
    switching_trigger: sub.switchingTrigger,
    business_model: sub.businessModel,
    current_substitute: sub.currentSubstitute,
    pricing: sub.pricing,
    pricing_model: sub.pricingModel,
    starting_price: sub.startingPrice,
    sales_motion: sub.salesMotion,
    typical_contract_size: sub.typicalContractSize,
    implementation_complexity: sub.implementationComplexity,
    time_to_value: sub.timeToValue,
    traction: sub.traction,
    pilot_count: sub.pilotCount,
    loi_count: sub.loiCount,
    active_customer_count: sub.activeCustomerCount,
    paid_customer_count: sub.paidCustomerCount,
    monthly_revenue_value: sub.monthlyRevenueValue,
    growth_rate: sub.growthRate,
    has_customers: sub.hasCustomers,
    generating_revenue: sub.generatingRevenue,
    currently_fundraising: sub.currentlyFundraising,
    revenue: sub.revenue,
    funding: sub.funding,
    team: sub.team,
    founder_problem_fit: sub.founderProblemFit,
    founder_years_in_industry: sub.founderYearsInIndustry,
    technical_founder: sub.technicalFounder,
    ask: sub.ask,
    deck_url: sub.deckUrl,
    demo_url: sub.demoUrl,
    customer_proof_url: sub.customerProofUrl,
    pilot_docs_url: sub.pilotDocsUrl,
    advantage: sub.advantage,
    competitors: sub.competitors,
    primary_risk_category: sub.primaryRiskCategory,
    risk: sub.risk,
    extra_context: sub.extraContext,
    industry_priority_areas: sub.industryPriorityAreas,
    keywords: sub.keywords,
    referral_source: sub.referralSource,
    status: sub.status,
    admin_notes: sub.adminNotes,
    report_url: sub.reportUrl,
    score: sub.score,
    verdict: sub.verdict,
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
