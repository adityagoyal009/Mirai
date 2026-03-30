import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import {
  INDUSTRY_OPTIONS,
  STAGE_OPTIONS,
  BUSINESS_MODEL_OPTIONS,
  REVENUE_OPTIONS,
  FUNDING_OPTIONS,
  REFERRAL_SOURCE_OPTIONS,
} from "@/lib/form-options";

function s(val: unknown): string {
  return (typeof val === "string" ? val : "").trim();
}

const MAX_TEXT_LENGTH = 100_000;

function buildExecSummary(d: Record<string, string>): string {
  const lines: string[] = [];
  const add = (label: string, val: string) => { if (val) lines.push(`${label}: ${val}`); };

  add("Company", d.companyName);
  add("Website", d.websiteUrl);
  add("Industry", d.industry);
  add("Industry Priority Areas", d.industryPriorityAreas);
  add("Stage", d.stage);
  add("Location", d.location);
  add("Country", d.country);
  add("Year Founded", d.yearFounded);
  add("Product", d.oneLiner);
  add("Target Market", d.customers);
  add("Business Model", d.businessModel);
  add("Pricing", d.pricing);
  add("Traction", d.traction);
  add("Has Customers", d.hasCustomers);
  add("Generating Revenue", d.generatingRevenue);
  add("Revenue / ARR", d.revenue);
  add("Funding Raised", d.funding);
  add("Currently Fundraising", d.currentlyFundraising);
  add("Team", d.team);
  add("Ask", d.ask);
  add("Moat / Advantage", d.advantage);
  add("Known Competitors", d.competitors);
  add("Key Risks", d.risk);
  add("Keywords", d.keywords);
  if (d.deckUrl) add("Deck", d.deckUrl);
  add("Referral Source", d.referralSource);
  if (d.extraContext) lines.push(`\nAdditional Context:\n${d.extraContext}`);

  return lines.join("\n\n");
}

export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const body = await request.json();

  // Required field validation
  const companyName = s(body.companyName);
  if (!companyName) {
    return NextResponse.json({ error: "Company name is required." }, { status: 400 });
  }

  const oneLiner = s(body.oneLiner);
  if (!oneLiner) {
    return NextResponse.json({ error: "Product / service description is required." }, { status: 400 });
  }

  const industry = s(body.industry);
  if (!industry) {
    return NextResponse.json({ error: "Industry is required." }, { status: 400 });
  }

  const stage = s(body.stage);
  if (!stage) {
    return NextResponse.json({ error: "Stage is required." }, { status: 400 });
  }

  const businessModel = s(body.businessModel);
  if (!businessModel) {
    return NextResponse.json({ error: "Business model is required." }, { status: 400 });
  }

  const customers = s(body.customers);
  if (!customers) {
    return NextResponse.json({ error: "Target market is required." }, { status: 400 });
  }

  // Enum validation for select fields
  if (!(INDUSTRY_OPTIONS as readonly string[]).includes(industry)) {
    return NextResponse.json({ error: "Invalid industry selection." }, { status: 400 });
  }
  if (!(STAGE_OPTIONS as readonly string[]).includes(stage)) {
    return NextResponse.json({ error: "Invalid stage selection." }, { status: 400 });
  }
  if (!(BUSINESS_MODEL_OPTIONS as readonly string[]).includes(businessModel)) {
    return NextResponse.json({ error: "Invalid business model selection." }, { status: 400 });
  }

  const revenue = s(body.revenue);
  if (revenue && !(REVENUE_OPTIONS as readonly string[]).includes(revenue)) {
    return NextResponse.json({ error: "Invalid revenue selection." }, { status: 400 });
  }

  const funding = s(body.funding);
  if (funding && !(FUNDING_OPTIONS as readonly string[]).includes(funding)) {
    return NextResponse.json({ error: "Invalid funding selection." }, { status: 400 });
  }

  const referralSource = s(body.referralSource);
  if (referralSource && !(REFERRAL_SOURCE_OPTIONS as readonly string[]).includes(referralSource)) {
    return NextResponse.json({ error: "Invalid referral source selection." }, { status: 400 });
  }

  // URL validation
  const websiteUrl = s(body.websiteUrl);
  if (websiteUrl && !/^https?:\/\/.+/.test(websiteUrl)) {
    return NextResponse.json({ error: "Website URL must start with http:// or https://" }, { status: 400 });
  }

  const deckUrl = s(body.deckUrl);
  if (deckUrl && !/^https?:\/\/.+/.test(deckUrl)) {
    return NextResponse.json({ error: "Pitch deck URL must start with http:// or https://" }, { status: 400 });
  }

  // Length limits on text fields
  const textKeys = ["oneLiner", "customers", "pricing", "traction", "team", "advantage", "risk", "extraContext"];
  for (const key of textKeys) {
    if (typeof body[key] === "string" && body[key].length > MAX_TEXT_LENGTH) {
      return NextResponse.json({ error: `${key} exceeds maximum length of ${MAX_TEXT_LENGTH} characters.` }, { status: 400 });
    }
  }

  const fields: Record<string, string> = {
    companyName,
    oneLiner,
    websiteUrl,
    industry,
    stage,
    location: s(body.location),
    yearFounded: s(body.yearFounded),
    customers,
    businessModel,
    pricing: s(body.pricing),
    traction: s(body.traction),
    revenue,
    funding,
    team: s(body.team),
    ask: s(body.ask),
    deckUrl,
    advantage: s(body.advantage),
    competitors: s(body.competitors),
    risk: s(body.risk),
    extraContext: s(body.extraContext),
    country: s(body.country),
    industryPriorityAreas: s(body.industryPriorityAreas),
    keywords: s(body.keywords),
    hasCustomers: s(body.hasCustomers),
    generatingRevenue: s(body.generatingRevenue),
    currentlyFundraising: s(body.currentlyFundraising),
    referralSource,
  };

  // Atomic transaction: create submission + event together
  const sub = await prisma.$transaction(async (tx) => {
    const submission = await tx.submission.create({
      data: {
        userId: session.user.id,
        companyName: fields.companyName,
        websiteUrl: fields.websiteUrl,
        industry: fields.industry,
        stage: fields.stage,
        oneLiner: fields.oneLiner,
        customers: fields.customers,
        businessModel: fields.businessModel,
        traction: fields.traction,
        deckUrl: fields.deckUrl,
        advantage: fields.advantage,
        risk: fields.risk,
        location: fields.location,
        yearFounded: fields.yearFounded,
        pricing: fields.pricing,
        revenue: fields.revenue,
        funding: fields.funding,
        team: fields.team,
        ask: fields.ask,
        competitors: fields.competitors,
        extraContext: fields.extraContext,
        country: fields.country,
        industryPriorityAreas: fields.industryPriorityAreas,
        keywords: fields.keywords,
        hasCustomers: fields.hasCustomers,
        generatingRevenue: fields.generatingRevenue,
        currentlyFundraising: fields.currentlyFundraising,
        referralSource: fields.referralSource,
        status: "queued",
      },
    });

    await tx.event.create({
      data: {
        event: "submission_created",
        submissionId: submission.id,
        userId: session.user.id,
        meta: JSON.stringify({ company: companyName, industry: fields.industry }),
      },
    });

    return submission;
  });

  // Build structured fields for direct passthrough (skips LLM extraction on backend)
  const structuredFields = {
    company: fields.companyName,
    industry: fields.industry,
    product: fields.oneLiner,
    target_market: fields.customers,
    business_model: fields.businessModel,
    stage: fields.stage,
    traction: fields.traction,
    ask: fields.ask,
    website_url: fields.websiteUrl,
    year_founded: fields.yearFounded,
    location: fields.location,
    revenue: fields.revenue,
    known_competitors: fields.competitors ? fields.competitors.split(",").map((c: string) => c.trim()).filter(Boolean) : [],
    funding: fields.funding,
    team: fields.team,
    pricing: fields.pricing,
    country: fields.country,
    keywords: fields.keywords,
    industry_priority_areas: fields.industryPriorityAreas,
    has_customers: fields.hasCustomers,
    generating_revenue: fields.generatingRevenue,
    currently_fundraising: fields.currentlyFundraising,
  };

  // Enqueue for analysis (processes one at a time, 50/day limit)
  const { analysisQueue } = await import("@/lib/analysis-queue");
  const execSummary = buildExecSummary(fields);
  const enqueueResult = await analysisQueue.enqueue(sub.id, execSummary, structuredFields);

  if (!enqueueResult.ok) {
    // Submission is saved but analysis won't run today
    await prisma.submission.update({
      where: { id: sub.id },
      data: { adminNotes: enqueueResult.reason || "Daily limit reached." },
    });

    return NextResponse.json({
      message: `Submission saved. ${enqueueResult.reason} Your request will be processed when capacity is available.`,
      submission: { id: sub.id, created_at: sub.createdAt.toISOString() },
      queue: { position: -1, dailyLimitReached: true },
    });
  }

  const queueStatus = await analysisQueue.status();
  const position = analysisQueue.positionOf(sub.id);
  const waitMsg = position <= 1
    ? "Analysis is starting now"
    : `Queued at position ${position} (${position - 1} ahead of you)`;

  return NextResponse.json({
    message: `Submission received. ${waitMsg} — check your dashboard for updates.`,
    submission: { id: sub.id, created_at: sub.createdAt.toISOString() },
    queue: { position, length: queueStatus.queueLength, dailyRemaining: queueStatus.dailyRemaining },
  });
}
