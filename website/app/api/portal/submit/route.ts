import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import {
  INDUSTRY_OPTIONS,
  STAGE_OPTIONS,
  BUSINESS_MODEL_OPTIONS,
  PRICING_MODEL_OPTIONS,
  SALES_MOTION_OPTIONS,
  IMPLEMENTATION_COMPLEXITY_OPTIONS,
  CURRENT_SUBSTITUTE_OPTIONS,
  PRIMARY_RISK_OPTIONS,
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
  add("Stage", d.stage);
  add("Country", d.country);
  add("Year Founded", d.yearFounded);
  add("Product", d.oneLiner);
  add("Target Market", d.customers);
  add("End User", d.endUser);
  add("Economic Buyer", d.economicBuyer);
  add("Why They Switch Now", d.switchingTrigger);
  add("Current Substitute", d.currentSubstitute);
  add("Business Model", d.businessModel);
  add("Pricing Model", d.pricingModel);
  add("Starting Price", d.startingPrice);
  add("Sales Motion", d.salesMotion);
  add("Typical Contract Size", d.typicalContractSize);
  add("Implementation Complexity", d.implementationComplexity);
  add("Time To First Value", d.timeToValue);
  add("Traction", d.traction);
  add("LOIs", d.loiCount);
  add("Pilots", d.pilotCount);
  add("Active Customers", d.activeCustomerCount);
  add("Paid Customers", d.paidCustomerCount);
  add("Monthly Revenue", d.monthlyRevenueValue);
  add("Growth Rate", d.growthRate);
  add("Has Customers", d.hasCustomers);
  add("Generating Revenue", d.generatingRevenue);
  add("Revenue / ARR", d.revenue);
  add("Capital Raised To Date", d.funding);
  add("Currently Fundraising", d.currentlyFundraising);
  add("Team", d.team);
  add("Founder Fit", d.founderProblemFit);
  add("Founder Years In Industry", d.founderYearsInIndustry);
  add("Technical Founder", d.technicalFounder);
  add("What Mirai Should Pressure-Test", d.ask);
  add("Why You Win / Moat", d.advantage);
  add("Known Competitors", d.competitors);
  add("What Could Break", d.risk);
  add("Main Risk Category", d.primaryRiskCategory);
  if (d.extraContext) lines.push(`\nEvidence Links / Notes:\n${d.extraContext}`);

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
  const endUser = s(body.endUser);
  if (!endUser) {
    return NextResponse.json({ error: "End user is required." }, { status: 400 });
  }
  const economicBuyer = s(body.economicBuyer);
  if (!economicBuyer) {
    return NextResponse.json({ error: "Economic buyer is required." }, { status: 400 });
  }
  const switchingTrigger = s(body.switchingTrigger);
  if (!switchingTrigger) {
    return NextResponse.json({ error: "Why they switch now is required." }, { status: 400 });
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
  const funding = s(body.funding);

  const pricingModel = s(body.pricingModel);
  if (pricingModel && !(PRICING_MODEL_OPTIONS as readonly string[]).includes(pricingModel)) {
    return NextResponse.json({ error: "Invalid pricing model selection." }, { status: 400 });
  }

  const salesMotion = s(body.salesMotion);
  if (salesMotion && !(SALES_MOTION_OPTIONS as readonly string[]).includes(salesMotion)) {
    return NextResponse.json({ error: "Invalid sales motion selection." }, { status: 400 });
  }

  const implementationComplexity = s(body.implementationComplexity);
  if (
    implementationComplexity &&
    !(IMPLEMENTATION_COMPLEXITY_OPTIONS as readonly string[]).includes(implementationComplexity)
  ) {
    return NextResponse.json({ error: "Invalid implementation complexity selection." }, { status: 400 });
  }

  const currentSubstitute = s(body.currentSubstitute);
  if (currentSubstitute && !(CURRENT_SUBSTITUTE_OPTIONS as readonly string[]).includes(currentSubstitute)) {
    return NextResponse.json({ error: "Invalid current substitute selection." }, { status: 400 });
  }

  const primaryRiskCategory = s(body.primaryRiskCategory);
  if (primaryRiskCategory && !(PRIMARY_RISK_OPTIONS as readonly string[]).includes(primaryRiskCategory)) {
    return NextResponse.json({ error: "Invalid main risk category selection." }, { status: 400 });
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

  const demoUrl = s(body.demoUrl);
  if (demoUrl && !/^https?:\/\/.+/.test(demoUrl)) {
    return NextResponse.json({ error: "Demo URL must start with http:// or https://" }, { status: 400 });
  }

  const customerProofUrl = s(body.customerProofUrl);
  if (customerProofUrl && !/^https?:\/\/.+/.test(customerProofUrl)) {
    return NextResponse.json({ error: "Customer proof URL must start with http:// or https://" }, { status: 400 });
  }

  const pilotDocsUrl = s(body.pilotDocsUrl);
  if (pilotDocsUrl && !/^https?:\/\/.+/.test(pilotDocsUrl)) {
    return NextResponse.json({ error: "Pilot docs URL must start with http:// or https://" }, { status: 400 });
  }

  // Length limits on text fields
  const textKeys = [
    "oneLiner", "customers", "endUser", "economicBuyer", "switchingTrigger",
    "pricing", "startingPrice", "typicalContractSize", "timeToValue", "traction",
    "loiCount", "pilotCount", "activeCustomerCount", "paidCustomerCount",
    "monthlyRevenueValue", "revenue", "growthRate", "funding", "team", "founderProblemFit",
    "founderYearsInIndustry", "advantage", "competitors", "risk", "extraContext",
  ];
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
    endUser,
    economicBuyer,
    switchingTrigger,
    location: s(body.location),
    yearFounded: s(body.yearFounded),
    customers,
    businessModel,
    pricing: s(body.pricing),
    pricingModel,
    startingPrice: s(body.startingPrice),
    salesMotion,
    typicalContractSize: s(body.typicalContractSize),
    implementationComplexity,
    timeToValue: s(body.timeToValue),
    currentSubstitute,
    traction: s(body.traction),
    loiCount: s(body.loiCount),
    pilotCount: s(body.pilotCount),
    activeCustomerCount: s(body.activeCustomerCount),
    paidCustomerCount: s(body.paidCustomerCount),
    monthlyRevenueValue: s(body.monthlyRevenueValue),
    growthRate: s(body.growthRate),
    revenue,
    funding,
    team: s(body.team),
    founderProblemFit: s(body.founderProblemFit),
    founderYearsInIndustry: s(body.founderYearsInIndustry),
    technicalFounder: s(body.technicalFounder),
    ask: s(body.ask),
    deckUrl,
    demoUrl,
    customerProofUrl,
    pilotDocsUrl,
    advantage: s(body.advantage),
    competitors: s(body.competitors),
    risk: s(body.risk),
    primaryRiskCategory,
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
    const createdAt = new Date().toISOString();
    const columns = [
      "user_id", "company_name", "website_url", "industry", "stage", "one_liner",
      "customers", "end_user", "economic_buyer", "switching_trigger", "business_model",
      "traction", "loi_count", "pilot_count", "active_customer_count", "paid_customer_count",
      "monthly_revenue_value", "growth_rate", "deck_url", "demo_url", "customer_proof_url",
      "pilot_docs_url", "advantage", "risk", "primary_risk_category", "location",
      "year_founded", "pricing", "pricing_model", "starting_price", "sales_motion",
      "typical_contract_size", "implementation_complexity", "time_to_value",
      "current_substitute", "revenue", "funding", "team", "founder_problem_fit",
      "founder_years_in_industry", "technical_founder", "ask", "competitors",
      "extra_context", "country", "industry_priority_areas", "keywords",
      "has_customers", "generating_revenue", "currently_fundraising",
      "referral_source", "status", "created_at", "updated_at",
    ];
    const values = [
      session.user.id, fields.companyName, fields.websiteUrl, fields.industry, fields.stage, fields.oneLiner,
      fields.customers, fields.endUser, fields.economicBuyer, fields.switchingTrigger, fields.businessModel,
      fields.traction, fields.loiCount, fields.pilotCount, fields.activeCustomerCount, fields.paidCustomerCount,
      fields.monthlyRevenueValue, fields.growthRate, fields.deckUrl, fields.demoUrl, fields.customerProofUrl,
      fields.pilotDocsUrl, fields.advantage, fields.risk, fields.primaryRiskCategory, fields.location,
      fields.yearFounded, fields.pricing, fields.pricingModel, fields.startingPrice, fields.salesMotion,
      fields.typicalContractSize, fields.implementationComplexity, fields.timeToValue, fields.currentSubstitute,
      fields.revenue, fields.funding, fields.team, fields.founderProblemFit, fields.founderYearsInIndustry,
      fields.technicalFounder, fields.ask, fields.competitors, fields.extraContext, fields.country,
      fields.industryPriorityAreas, fields.keywords, fields.hasCustomers, fields.generatingRevenue,
      fields.currentlyFundraising, fields.referralSource, "queued", createdAt, createdAt,
    ];
    const placeholders = columns.map(() => "?").join(", ");

    await tx.$executeRawUnsafe(
      `INSERT INTO submissions (${columns.join(", ")}) VALUES (${placeholders})`,
      ...values,
    );

    const inserted = await tx.$queryRawUnsafe<Array<{ id: number; created_at: string }>>(
      "SELECT id, created_at FROM submissions WHERE rowid = last_insert_rowid() LIMIT 1"
    );
    const submission = inserted[0];
    if (!submission) {
      throw new Error("Failed to create submission row.");
    }

    await tx.event.create({
      data: {
        event: "submission_created",
        submissionId: submission.id,
        userId: session.user.id,
        meta: JSON.stringify({ company: companyName, industry: fields.industry }),
      },
    });

    return { id: submission.id, createdAt: new Date(submission.created_at) };
  });

  // Build structured fields for direct passthrough (skips LLM extraction on backend)
  const structuredFields = {
    company: fields.companyName,
    industry: fields.industry,
    product: fields.oneLiner,
    target_market: fields.customers,
    end_user: fields.endUser,
    economic_buyer: fields.economicBuyer,
    switching_trigger: fields.switchingTrigger,
    business_model: fields.businessModel,
    stage: fields.stage,
    traction: fields.traction,
    loi_count: fields.loiCount,
    pilot_count: fields.pilotCount,
    active_customer_count: fields.activeCustomerCount,
    paid_customer_count: fields.paidCustomerCount,
    monthly_revenue_value: fields.monthlyRevenueValue,
    growth_rate: fields.growthRate,
    ask: fields.ask,
    website_url: fields.websiteUrl,
    year_founded: fields.yearFounded,
    location: fields.location,
    revenue: fields.revenue,
    known_competitors: fields.competitors ? fields.competitors.split(",").map((c: string) => c.trim()).filter(Boolean) : [],
    funding: fields.funding,
    team: fields.team,
    pricing: fields.pricing,
    pricing_model: fields.pricingModel,
    starting_price: fields.startingPrice,
    sales_motion: fields.salesMotion,
    typical_contract_size: fields.typicalContractSize,
    implementation_complexity: fields.implementationComplexity,
    time_to_value: fields.timeToValue,
    current_substitute: fields.currentSubstitute,
    demo_url: fields.demoUrl,
    customer_proof_url: fields.customerProofUrl,
    pilot_docs_url: fields.pilotDocsUrl,
    founder_problem_fit: fields.founderProblemFit,
    founder_years_in_industry: fields.founderYearsInIndustry,
    technical_founder: fields.technicalFounder,
    primary_risk_category: fields.primaryRiskCategory,
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
