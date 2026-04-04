import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";
import { analysisQueue, buildExecSummaryFromSubmission, buildStructuredFields, type SubmissionRecord } from "@/lib/analysis-queue";
import { serializeSubmission } from "@/lib/utils";

export async function POST(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.isAdmin) {
    return NextResponse.json({ error: "Admin access required." }, { status: 403 });
  }

  const sourceId = parseInt(params.id, 10);
  if (isNaN(sourceId)) {
    return NextResponse.json({ error: "Invalid submission ID." }, { status: 400 });
  }

  const existing = await prisma.submission.findUnique({
    where: { id: sourceId },
    include: { user: { select: { name: true, email: true } } },
  });

  if (!existing) {
    return NextResponse.json({ error: "Submission not found." }, { status: 404 });
  }

  const cloned = await prisma.submission.create({
    data: {
      userId: existing.userId,
      companyName: existing.companyName,
      websiteUrl: existing.websiteUrl,
      industry: existing.industry,
      stage: existing.stage,
      oneLiner: existing.oneLiner,
      customers: existing.customers,
      endUser: existing.endUser,
      economicBuyer: existing.economicBuyer,
      switchingTrigger: existing.switchingTrigger,
      businessModel: existing.businessModel,
      traction: existing.traction,
      loiCount: existing.loiCount,
      pilotCount: existing.pilotCount,
      activeCustomerCount: existing.activeCustomerCount,
      paidCustomerCount: existing.paidCustomerCount,
      monthlyRevenueValue: existing.monthlyRevenueValue,
      growthRate: existing.growthRate,
      deckUrl: existing.deckUrl,
      demoUrl: existing.demoUrl,
      customerProofUrl: existing.customerProofUrl,
      pilotDocsUrl: existing.pilotDocsUrl,
      advantage: existing.advantage,
      risk: existing.risk,
      primaryRiskCategory: existing.primaryRiskCategory,
      location: existing.location,
      yearFounded: existing.yearFounded,
      pricing: existing.pricing,
      pricingModel: existing.pricingModel,
      startingPrice: existing.startingPrice,
      salesMotion: existing.salesMotion,
      typicalContractSize: existing.typicalContractSize,
      implementationComplexity: existing.implementationComplexity,
      timeToValue: existing.timeToValue,
      currentSubstitute: existing.currentSubstitute,
      revenue: existing.revenue,
      funding: existing.funding,
      team: existing.team,
      founderProblemFit: existing.founderProblemFit,
      founderYearsInIndustry: existing.founderYearsInIndustry,
      technicalFounder: existing.technicalFounder,
      ask: existing.ask,
      competitors: existing.competitors,
      extraContext: existing.extraContext,
      country: existing.country,
      industryPriorityAreas: existing.industryPriorityAreas,
      keywords: existing.keywords,
      hasCustomers: existing.hasCustomers,
      generatingRevenue: existing.generatingRevenue,
      currentlyFundraising: existing.currentlyFundraising,
      referralSource: existing.referralSource,
      status: "queued",
      adminNotes: `Admin rerun requested from submission #${sourceId}.`,
      reportUrl: "",
      score: null,
      verdict: "",
    },
    include: { user: { select: { name: true, email: true } } },
  });

  const submissionRecord: SubmissionRecord = {
    id: cloned.id,
    status: cloned.status,
    reportUrl: cloned.reportUrl,
    adminNotes: cloned.adminNotes,
    companyName: cloned.companyName,
    websiteUrl: cloned.websiteUrl,
    industry: cloned.industry,
    industryPriorityAreas: cloned.industryPriorityAreas,
    stage: cloned.stage,
    location: cloned.location,
    country: cloned.country,
    yearFounded: cloned.yearFounded,
    oneLiner: cloned.oneLiner,
    customers: cloned.customers,
    endUser: cloned.endUser,
    economicBuyer: cloned.economicBuyer,
    switchingTrigger: cloned.switchingTrigger,
    currentSubstitute: cloned.currentSubstitute,
    businessModel: cloned.businessModel,
    pricing: cloned.pricing,
    pricingModel: cloned.pricingModel,
    startingPrice: cloned.startingPrice,
    salesMotion: cloned.salesMotion,
    typicalContractSize: cloned.typicalContractSize,
    implementationComplexity: cloned.implementationComplexity,
    timeToValue: cloned.timeToValue,
    traction: cloned.traction,
    loiCount: cloned.loiCount,
    pilotCount: cloned.pilotCount,
    activeCustomerCount: cloned.activeCustomerCount,
    paidCustomerCount: cloned.paidCustomerCount,
    monthlyRevenueValue: cloned.monthlyRevenueValue,
    growthRate: cloned.growthRate,
    hasCustomers: cloned.hasCustomers,
    generatingRevenue: cloned.generatingRevenue,
    revenue: cloned.revenue,
    funding: cloned.funding,
    currentlyFundraising: cloned.currentlyFundraising,
    team: cloned.team,
    founderProblemFit: cloned.founderProblemFit,
    founderYearsInIndustry: cloned.founderYearsInIndustry,
    technicalFounder: cloned.technicalFounder,
    ask: cloned.ask,
    advantage: cloned.advantage,
    competitors: cloned.competitors,
    risk: cloned.risk,
    primaryRiskCategory: cloned.primaryRiskCategory,
    keywords: cloned.keywords,
    deckUrl: cloned.deckUrl,
    demoUrl: cloned.demoUrl,
    customerProofUrl: cloned.customerProofUrl,
    pilotDocsUrl: cloned.pilotDocsUrl,
    referralSource: cloned.referralSource,
    extraContext: cloned.extraContext,
    createdAt: cloned.createdAt,
  };

  const enqueueResult = await analysisQueue.enqueue(
    cloned.id,
    buildExecSummaryFromSubmission(submissionRecord),
    buildStructuredFields(submissionRecord),
  );

  if (!enqueueResult.ok) {
    await prisma.submission.delete({ where: { id: cloned.id } });
    return NextResponse.json(
      { error: enqueueResult.reason || "Failed to enqueue rerun." },
      { status: 429 }
    );
  }

  await prisma.event.create({
    data: {
      event: "submission_rerun_queued",
      submissionId: cloned.id,
      userId: session.user.id,
      meta: JSON.stringify({
        source_submission_id: sourceId,
        company: cloned.companyName,
        admin_email: session.user.email,
      }),
    },
  });

  const queuePosition = analysisQueue.positionOf(cloned.id);

  return NextResponse.json({
    message: `Rerun queued for ${cloned.companyName}.`,
    queue_position: queuePosition,
    submission: serializeSubmission(cloned, cloned.user),
  });
}
