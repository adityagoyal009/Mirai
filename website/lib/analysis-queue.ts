/**
 * Simple in-memory FIFO queue for Mirai analysis jobs.
 * Processes ONE analysis at a time to avoid overloading the backend.
 * Survives across API calls (module-level singleton) but not server restarts.
 * On restart, auto-runnable "queued"/"reviewing" submissions get reconstructed.
 */

import prisma from "./prisma";
import { MIRAI_API_INTERNAL, MIRAI_API_PUBLIC, miraiInternalHeaders, miraiJsonHeaders } from "./mirai-api";
const DAILY_LIMIT = 50;
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 10_000; // 10 seconds between retries
const FETCH_TIMEOUT_MS = 3_600_000; // 60 minute timeout per attempt (full analysis with council/swarm)

export interface StructuredFields {
  company: string;
  industry: string;
  product: string;
  target_market: string;
  end_user: string;
  economic_buyer: string;
  switching_trigger: string;
  business_model: string;
  stage: string;
  traction: string;
  loi_count: string;
  pilot_count: string;
  active_customer_count: string;
  paid_customer_count: string;
  monthly_revenue_value: string;
  growth_rate: string;
  ask: string;
  website_url: string;
  year_founded: string;
  location: string;
  revenue: string;
  known_competitors: string[];
  funding: string;
  team: string;
  pricing: string;
  pricing_model: string;
  starting_price: string;
  sales_motion: string;
  typical_contract_size: string;
  implementation_complexity: string;
  time_to_value: string;
  current_substitute: string;
  demo_url: string;
  customer_proof_url: string;
  pilot_docs_url: string;
  founder_problem_fit: string;
  founder_years_in_industry: string;
  technical_founder: string;
  primary_risk_category: string;
  advantage: string;
  risk: string;
  extra_context: string;
  country: string;
  keywords: string;
  industry_priority_areas: string;
  has_customers: string;
  generating_revenue: string;
  currently_fundraising: string;
}

interface AnalysisAdminSummary {
  analysis_id?: string;
  duration_s?: number;
  renderer_requested?: string;
  renderer_used?: string;
  report_generation_status?: string;
  report_generation_error?: string;
  report_sections_count?: number;
  warning_count?: number;
  warnings?: string[];
  enhancement_keys?: string[];
  enhancement_count?: number;
  has_llm_preview?: boolean;
  llm_preview_status?: string;
  llm_preview_error?: string;
  research_quality_score?: number;
  research_coverage_score?: number;
  research_source_quality_score?: number;
  research_freshness_score?: number;
  low_coverage_dimensions?: string[];
  missing_evidence_flags?: string[];
  audit_path?: string;
}

interface QueueJob {
  submissionId: number;
  execSummary: string;
  structuredFields: StructuredFields;
  addedAt: number;
  retries: number;
}

export interface SubmissionRecord {
  id: number;
  status: string;
  reportUrl: string;
  adminNotes: string;
  companyName: string;
  websiteUrl: string;
  industry: string;
  industryPriorityAreas: string;
  stage: string;
  location: string;
  country: string;
  yearFounded: string;
  oneLiner: string;
  customers: string;
  endUser: string;
  economicBuyer: string;
  switchingTrigger: string;
  currentSubstitute: string;
  businessModel: string;
  pricing: string;
  pricingModel: string;
  startingPrice: string;
  salesMotion: string;
  typicalContractSize: string;
  implementationComplexity: string;
  timeToValue: string;
  traction: string;
  loiCount: string;
  pilotCount: string;
  activeCustomerCount: string;
  paidCustomerCount: string;
  monthlyRevenueValue: string;
  growthRate: string;
  hasCustomers: string;
  generatingRevenue: string;
  revenue: string;
  funding: string;
  currentlyFundraising: string;
  team: string;
  founderProblemFit: string;
  founderYearsInIndustry: string;
  technicalFounder: string;
  ask: string;
  advantage: string;
  competitors: string;
  risk: string;
  primaryRiskCategory: string;
  keywords: string;
  deckUrl: string;
  demoUrl: string;
  customerProofUrl: string;
  pilotDocsUrl: string;
  referralSource: string;
  extraContext: string;
  createdAt: Date;
}

export function buildExecSummaryFromSubmission(submission: SubmissionRecord): string {
  const lines: string[] = [];
  const add = (label: string, value: string) => {
    if (value) lines.push(`${label}: ${value}`);
  };

  add("Company", submission.companyName);
  add("Website", submission.websiteUrl);
  add("Industry", submission.industry);
  add("Stage", submission.stage);
  add("Country", submission.country);
  add("Year Founded", submission.yearFounded);
  add("Product", submission.oneLiner);
  add("Target Market", submission.customers);
  add("End User", submission.endUser);
  add("Economic Buyer", submission.economicBuyer);
  add("Why They Switch Now", submission.switchingTrigger);
  add("Current Substitute", submission.currentSubstitute);
  add("Business Model", submission.businessModel);
  add("Pricing Model", submission.pricingModel);
  add("Starting Price", submission.startingPrice);
  add("Sales Motion", submission.salesMotion);
  add("Typical Contract Size", submission.typicalContractSize);
  add("Implementation Complexity", submission.implementationComplexity);
  add("Time To First Value", submission.timeToValue);
  add("Traction", submission.traction);
  add("LOIs", submission.loiCount);
  add("Pilots", submission.pilotCount);
  add("Active Customers", submission.activeCustomerCount);
  add("Paid Customers", submission.paidCustomerCount);
  add("Monthly Revenue", submission.monthlyRevenueValue);
  add("Growth Rate", submission.growthRate);
  add("Has Customers", submission.hasCustomers);
  add("Generating Revenue", submission.generatingRevenue);
  add("Revenue / ARR", submission.revenue);
  add("Capital Raised To Date", submission.funding);
  add("Currently Fundraising", submission.currentlyFundraising);
  add("Team", submission.team);
  add("Founder Fit", submission.founderProblemFit);
  add("Founder Years In Industry", submission.founderYearsInIndustry);
  add("Technical Founder", submission.technicalFounder);
  add("What Mirai Should Pressure-Test", submission.ask);
  add("Why You Win / Moat", submission.advantage);
  add("Known Competitors", submission.competitors);
  add("What Could Break", submission.risk);
  add("Main Risk Category", submission.primaryRiskCategory);
  if (submission.extraContext) lines.push(`\nEvidence Links / Notes:\n${submission.extraContext}`);

  return lines.join("\n\n");
}

export function buildStructuredFields(submission: SubmissionRecord): StructuredFields {
  return {
    company: submission.companyName,
    industry: submission.industry,
    product: submission.oneLiner,
    target_market: submission.customers,
    end_user: submission.endUser,
    economic_buyer: submission.economicBuyer,
    switching_trigger: submission.switchingTrigger,
    business_model: submission.businessModel,
    stage: submission.stage,
    traction: submission.traction,
    loi_count: submission.loiCount,
    pilot_count: submission.pilotCount,
    active_customer_count: submission.activeCustomerCount,
    paid_customer_count: submission.paidCustomerCount,
    monthly_revenue_value: submission.monthlyRevenueValue,
    growth_rate: submission.growthRate,
    ask: submission.ask,
    website_url: submission.websiteUrl,
    year_founded: submission.yearFounded,
    location: submission.location,
    revenue: submission.revenue,
    known_competitors: submission.competitors
      ? submission.competitors.split(",").map((company: string) => company.trim()).filter(Boolean)
      : [],
    funding: submission.funding,
    team: submission.team,
    pricing: submission.pricing,
    pricing_model: submission.pricingModel,
    starting_price: submission.startingPrice,
    sales_motion: submission.salesMotion,
    typical_contract_size: submission.typicalContractSize,
    implementation_complexity: submission.implementationComplexity,
    time_to_value: submission.timeToValue,
    current_substitute: submission.currentSubstitute,
    demo_url: submission.demoUrl,
    customer_proof_url: submission.customerProofUrl,
    pilot_docs_url: submission.pilotDocsUrl,
    founder_problem_fit: submission.founderProblemFit,
    founder_years_in_industry: submission.founderYearsInIndustry,
    technical_founder: submission.technicalFounder,
    primary_risk_category: submission.primaryRiskCategory,
    advantage: submission.advantage,
    risk: submission.risk,
    extra_context: submission.extraContext,
    country: submission.country,
    keywords: submission.keywords,
    industry_priority_areas: submission.industryPriorityAreas,
    has_customers: submission.hasCustomers,
    generating_revenue: submission.generatingRevenue,
    currently_fundraising: submission.currentlyFundraising,
  };
}

function parseRetryCount(adminNotes: string): number {
  const match = adminNotes.match(/^Retry (\d+)\/\d+:/);
  if (!match) return 0;
  const parsed = parseInt(match[1], 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function shouldAutoResume(submission: SubmissionRecord): boolean {
  if (submission.status === "reviewing") return true;
  if (submission.status !== "queued" || Boolean(submission.reportUrl)) return false;

  const note = submission.adminNotes.trim();
  if (!note) return true;
  if (note.startsWith("Retry ")) return true;
  if (note.startsWith("Reset after server restart")) return true;
  if (note.startsWith("Resumed after server restart")) return true;
  return false;
}

class AnalysisQueue {
  private queue: QueueJob[] = [];
  private processing = false;
  private currentJob: QueueJob | null = null;

  constructor() {
    // Recover auto-runnable submissions on startup (handles server restarts)
    this.recoverStuck().catch((err) =>
      console.error("[queue] Startup recovery failed:", err)
    );
  }

  private async recoverStuck() {
    const recoverable = await prisma.$queryRawUnsafe<SubmissionRecord[]>(`
      SELECT
        id,
        status,
        report_url AS reportUrl,
        admin_notes AS adminNotes,
        company_name AS companyName,
        website_url AS websiteUrl,
        industry,
        industry_priority_areas AS industryPriorityAreas,
        stage,
        location,
        country,
        year_founded AS yearFounded,
        one_liner AS oneLiner,
        customers,
        COALESCE(end_user, '') AS endUser,
        COALESCE(economic_buyer, '') AS economicBuyer,
        COALESCE(switching_trigger, '') AS switchingTrigger,
        COALESCE(current_substitute, '') AS currentSubstitute,
        business_model AS businessModel,
        pricing,
        COALESCE(pricing_model, '') AS pricingModel,
        COALESCE(starting_price, '') AS startingPrice,
        COALESCE(sales_motion, '') AS salesMotion,
        COALESCE(typical_contract_size, '') AS typicalContractSize,
        COALESCE(implementation_complexity, '') AS implementationComplexity,
        COALESCE(time_to_value, '') AS timeToValue,
        traction,
        COALESCE(loi_count, '') AS loiCount,
        COALESCE(pilot_count, '') AS pilotCount,
        COALESCE(active_customer_count, '') AS activeCustomerCount,
        COALESCE(paid_customer_count, '') AS paidCustomerCount,
        COALESCE(monthly_revenue_value, '') AS monthlyRevenueValue,
        COALESCE(growth_rate, '') AS growthRate,
        has_customers AS hasCustomers,
        generating_revenue AS generatingRevenue,
        revenue,
        funding,
        currently_fundraising AS currentlyFundraising,
        team,
        COALESCE(founder_problem_fit, '') AS founderProblemFit,
        COALESCE(founder_years_in_industry, '') AS founderYearsInIndustry,
        COALESCE(technical_founder, '') AS technicalFounder,
        ask,
        advantage,
        competitors,
        risk,
        COALESCE(primary_risk_category, '') AS primaryRiskCategory,
        keywords,
        deck_url AS deckUrl,
        COALESCE(demo_url, '') AS demoUrl,
        COALESCE(customer_proof_url, '') AS customerProofUrl,
        COALESCE(pilot_docs_url, '') AS pilotDocsUrl,
        referral_source AS referralSource,
        extra_context AS extraContext,
        created_at AS createdAt
      FROM submissions
      WHERE status IN ('queued', 'reviewing')
      ORDER BY created_at ASC
    `);

    const resumable = recoverable.filter((submission: SubmissionRecord) =>
      shouldAutoResume(submission)
    );
    const reviewingIds = resumable
      .filter((submission: SubmissionRecord) => submission.status === "reviewing")
      .map((submission: SubmissionRecord) => submission.id);

    if (reviewingIds.length > 0) {
      await prisma.submission.updateMany({
        where: { id: { in: reviewingIds } },
        data: {
          status: "queued",
          adminNotes: "Resumed after server restart — automatically re-queued.",
        },
      });
    }

    for (const submission of resumable) {
      this.queue.push({
        submissionId: submission.id,
        execSummary: buildExecSummaryFromSubmission(submission),
        structuredFields: buildStructuredFields(submission),
        addedAt: Date.now(),
        retries: parseRetryCount(submission.adminNotes),
      });
    }

    if (resumable.length > 0) {
      console.log(
        `[queue] Recovered ${resumable.length} submission(s) after restart (${reviewingIds.length} were mid-analysis)`
      );
      this.tick();
    }
  }

  private getTodayKey(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private async getDailyCount(): Promise<number> {
    const day = this.getTodayKey();
    const row = await prisma.dailyUsage.findUnique({ where: { day } });
    return row?.count ?? 0;
  }

  private async incrementDaily(): Promise<number> {
    const day = this.getTodayKey();
    const row = await prisma.dailyUsage.upsert({
      where: { day },
      update: { count: { increment: 1 } },
      create: { day, count: 1 },
    });
    return row.count;
  }

  /** Add a job to the queue. Returns { ok, reason } */
  async enqueue(submissionId: number, execSummary: string, structuredFields?: StructuredFields): Promise<{ ok: boolean; reason?: string }> {
    // Deduplicate
    if (this.currentJob?.submissionId === submissionId) return { ok: true };
    if (this.queue.some((j) => j.submissionId === submissionId)) return { ok: true };

    // Check daily limit (DB count + in-flight + queued)
    const dbCount = await this.getDailyCount();
    const inFlight = this.queue.length + (this.processing ? 1 : 0);
    const totalToday = dbCount + inFlight;

    if (totalToday >= DAILY_LIMIT) {
      console.log(`[queue] Daily limit reached (${totalToday}/${DAILY_LIMIT}), rejecting submission ${submissionId}`);
      return { ok: false, reason: `Daily analysis limit reached (${DAILY_LIMIT}/day). Please try again tomorrow.` };
    }

    this.queue.push({ submissionId, execSummary, structuredFields: structuredFields!, addedAt: Date.now(), retries: 0 });
    console.log(
      `[queue] Enqueued submission ${submissionId} (position ${this.queue.length}, today=${totalToday + 1}/${DAILY_LIMIT})`
    );
    this.tick();
    return { ok: true };
  }

  /** Get queue status */
  async status() {
    const dbCount = await this.getDailyCount();
    const inFlight = this.queue.length + (this.processing ? 1 : 0);
    const totalToday = dbCount + inFlight;
    return {
      queueLength: this.queue.length,
      processing: this.processing,
      currentSubmissionId: this.currentJob?.submissionId ?? null,
      pending: this.queue.map((j) => j.submissionId),
      dailyUsed: totalToday,
      dailyLimit: DAILY_LIMIT,
      dailyRemaining: Math.max(0, DAILY_LIMIT - totalToday),
    };
  }

  /** Get estimated wait position for a submission */
  positionOf(submissionId: number): number {
    if (this.currentJob?.submissionId === submissionId) return 0;
    const idx = this.queue.findIndex((j) => j.submissionId === submissionId);
    if (idx === -1) return -1; // not in queue
    return idx + 1 + (this.processing ? 1 : 0);
  }

  private async checkBackendHealth(): Promise<boolean> {
    try {
      const res = await fetch(`${MIRAI_API_INTERNAL}/health`, {
        signal: AbortSignal.timeout(5000),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private async tick() {
    if (this.processing || this.queue.length === 0) return;

    this.processing = true;
    this.currentJob = this.queue.shift()!;
    const { submissionId, execSummary, structuredFields, retries } = this.currentJob;

    console.log(
      `[queue] Starting analysis for submission ${submissionId} (${this.queue.length} remaining, attempt ${retries + 1}/${MAX_RETRIES + 1})`
    );

    try {
      // Health check before committing to analysis
      const healthy = await this.checkBackendHealth();
      if (!healthy) {
        throw new Error("Backend health check failed — server unreachable");
      }

      // Update status to reviewing
      await prisma.submission.update({
        where: { id: submissionId },
        data: { status: "reviewing" },
      });

      if (retries === 0) {
        await prisma.event.create({
          data: {
            event: "analysis_started",
            submissionId,
            meta: JSON.stringify({
              automated: true,
              queueRemaining: this.queue.length,
              company: structuredFields.company,
              industry: structuredFields.industry,
            }),
          },
        });
      }

      // Submit job to Mirai BI engine (async mode — returns immediately with job ID)
      const submitRes = await fetch(`${MIRAI_API_INTERNAL}/api/bi/analyze`, {
        method: "POST",
        headers: miraiJsonHeaders(),
        body: JSON.stringify({
          exec_summary: execSummary,
          structured_fields: structuredFields || null,
          submission_id: submissionId,
          depth: "deep",
          agent_count: 50,
          simulate_market: true,
          async: true,
        }),
        signal: AbortSignal.timeout(30_000), // 30s to submit (fast)
      });

      if (!submitRes.ok) {
        const errText = await submitRes.text();
        throw new Error(`BI submit failed (${submitRes.status}): ${errText}`);
      }

      const submitData = await submitRes.json();
      if (!submitData.job_id) {
        throw new Error("No job_id returned from BI engine");
      }

      const jobId = submitData.job_id;
      console.log(`[queue] Job ${jobId} submitted for submission ${submissionId}`);

      // Poll for result (every 15s, up to FETCH_TIMEOUT_MS)
      const pollStart = Date.now();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let analysis: any = null;

      while (Date.now() - pollStart < FETCH_TIMEOUT_MS) {
        await this.delay(15_000); // wait 15s between polls

        try {
          const pollRes = await fetch(`${MIRAI_API_INTERNAL}/api/bi/job/${jobId}`, {
            headers: miraiInternalHeaders(),
            signal: AbortSignal.timeout(10_000),
          });
          const pollData = await pollRes.json() as Record<string, unknown>;

          if (pollData.status === "running") {
            const elapsed = pollData.elapsed as number || 0;
            console.log(`[queue] Job ${jobId} still running (${Math.round(elapsed)}s)`);
            continue;
          }

          if (pollData.status === "error") {
            throw new Error(`BI job failed: ${pollData.error}`);
          }

          // Job complete — pollData IS the result
          analysis = pollData;
          break;
        } catch (pollErr) {
          // Poll network error — keep trying
          console.warn(`[queue] Poll failed for ${jobId}: ${pollErr instanceof Error ? pollErr.message : pollErr}`);
        }
      }

      if (!analysis) {
        throw new Error(`Job ${jobId} timed out after ${FETCH_TIMEOUT_MS / 60000} minutes`);
      }

      const adminSummary: AnalysisAdminSummary =
        analysis.admin_summary && typeof analysis.admin_summary === "object"
          ? analysis.admin_summary
          : {};

      // Check if analysis needs more info
      if (analysis.status === "needs_more_info") {
        await prisma.submission.update({
          where: { id: submissionId },
          data: {
            status: "queued",
            adminNotes: `Analysis needs more info. Missing fields: ${(analysis.fields_missing || []).join(", ")}`,
          },
        });
        await prisma.event.create({
          data: {
            event: "analysis_needs_info",
            submissionId,
            meta: JSON.stringify({
              company: analysis.extraction?.company || structuredFields.company,
              industry: analysis.extraction?.industry || structuredFields.industry,
              fields_missing: analysis.fields_missing,
              analysis_id: analysis.analysis_id || analysis.id || adminSummary.analysis_id || "",
              audit_path:
                typeof adminSummary.audit_path === "string" ? adminSummary.audit_path : "",
            }),
          },
        });
        return;
      }

      // Extract score and verdict
      const warningList = Array.isArray(adminSummary.warnings)
        ? adminSummary.warnings.filter((warning: unknown): warning is string => typeof warning === "string")
        : [];
      const enhancementKeys = Array.isArray(adminSummary.enhancement_keys)
        ? adminSummary.enhancement_keys.filter((key: unknown): key is string => typeof key === "string")
        : [];
      const analysisId =
        analysis.analysis_id ||
        analysis.id ||
        adminSummary.analysis_id ||
        "";
      const durationS =
        typeof adminSummary.duration_s === "number" && Number.isFinite(adminSummary.duration_s)
          ? adminSummary.duration_s
          : null;
      const rendererUsed =
        typeof adminSummary.renderer_used === "string" && adminSummary.renderer_used
          ? adminSummary.renderer_used
          : "legacy";
      const rendererRequested =
        typeof adminSummary.renderer_requested === "string" && adminSummary.renderer_requested
          ? adminSummary.renderer_requested
          : "legacy";
      const reportGenerationStatus =
        typeof adminSummary.report_generation_status === "string" && adminSummary.report_generation_status
          ? adminSummary.report_generation_status
          : "unknown";
      const reportGenerationError =
        typeof adminSummary.report_generation_error === "string"
          ? adminSummary.report_generation_error
          : "";
      const llmPreviewStatus =
        typeof adminSummary.llm_preview_status === "string" && adminSummary.llm_preview_status
          ? adminSummary.llm_preview_status
          : "not_requested";
      const llmPreviewError =
        typeof adminSummary.llm_preview_error === "string"
          ? adminSummary.llm_preview_error
          : "";
      const auditPath =
        typeof adminSummary.audit_path === "string"
          ? adminSummary.audit_path
          : "";
      const researchQualityScore =
        typeof adminSummary.research_quality_score === "number" && Number.isFinite(adminSummary.research_quality_score)
          ? adminSummary.research_quality_score
          : null;
      const researchCoverageScore =
        typeof adminSummary.research_coverage_score === "number" && Number.isFinite(adminSummary.research_coverage_score)
          ? adminSummary.research_coverage_score
          : null;
      const researchSourceQualityScore =
        typeof adminSummary.research_source_quality_score === "number" && Number.isFinite(adminSummary.research_source_quality_score)
          ? adminSummary.research_source_quality_score
          : null;
      const researchFreshnessScore =
        typeof adminSummary.research_freshness_score === "number" && Number.isFinite(adminSummary.research_freshness_score)
          ? adminSummary.research_freshness_score
          : null;
      const lowCoverageDimensions = Array.isArray(adminSummary.low_coverage_dimensions)
        ? adminSummary.low_coverage_dimensions.filter((item: unknown): item is string => typeof item === "string")
        : [];
      const missingEvidenceFlags = Array.isArray(adminSummary.missing_evidence_flags)
        ? adminSummary.missing_evidence_flags.filter((item: unknown): item is string => typeof item === "string")
        : [];
      const council = analysis.council || {};
      const score =
        analysis.prediction?.composite_score ??
        analysis.prediction?.overall_score ??
        council.overall ??
        analysis.prediction?.score ??
        null;
      const verdict =
        analysis.final_verdict ??
        analysis.prediction?.verdict ??
        council.verdict ??
        "";

      // Generate shareable HTML report
      let reportUrl = "";
      const reportHtml = analysis.report_html || analysis.html_report;
      if (reportHtml) {
        try {
          const shareRes = await fetch(`${MIRAI_API_INTERNAL}/api/report/share`, {
            method: "POST",
            headers: miraiJsonHeaders(),
            body: JSON.stringify({
              html: reportHtml,
              company: analysis.extraction?.company || `Submission #${submissionId}`,
            }),
          });
          if (shareRes.ok) {
            const shareData = await shareRes.json();
            reportUrl = shareData.url || "";
            if (reportUrl && !reportUrl.startsWith("http")) {
              reportUrl = `${MIRAI_API_PUBLIC}${reportUrl}`;
            }
          }
        } catch (e) {
          console.error(`[queue] Report share failed for ${submissionId}:`, e);
        }
      }

      // Update submission with results
      await prisma.submission.update({
        where: { id: submissionId },
        data: {
          status: "report_sent",
          score: score != null ? parseFloat(String(score)) : null,
          verdict,
          reportUrl,
          adminNotes: reportUrl
            ? "Report generated automatically by Mirai engine."
            : "Analysis completed but report generation failed.",
        },
      });

      await prisma.event.create({
        data: {
          event: "analysis_complete",
          submissionId,
          meta: JSON.stringify({
            automated: true,
            company: analysis.extraction?.company || "",
            industry: analysis.extraction?.industry || "",
            score,
            verdict,
            has_report: Boolean(reportUrl),
            analysis_id: analysisId,
            duration_s: durationS,
            renderer_requested: rendererRequested,
            renderer_used: rendererUsed,
            report_generation_status: reportGenerationStatus,
            report_generation_error: reportGenerationError,
            report_sections_count:
              typeof adminSummary.report_sections_count === "number" && Number.isFinite(adminSummary.report_sections_count)
                ? adminSummary.report_sections_count
                : 0,
            warning_count: warningList.length,
            warnings: warningList,
            enhancement_keys: enhancementKeys,
            enhancement_count:
              typeof adminSummary.enhancement_count === "number" && Number.isFinite(adminSummary.enhancement_count)
                ? adminSummary.enhancement_count
                : enhancementKeys.length,
            has_llm_preview: Boolean(adminSummary.has_llm_preview),
            llm_preview_status: llmPreviewStatus,
            llm_preview_error: llmPreviewError,
            research_quality_score: researchQualityScore,
            research_coverage_score: researchCoverageScore,
            research_source_quality_score: researchSourceQualityScore,
            research_freshness_score: researchFreshnessScore,
            low_coverage_dimensions: lowCoverageDimensions,
            missing_evidence_flags: missingEvidenceFlags,
            audit_path: auditPath,
          }),
        },
      });

      if (
        warningList.length > 0 ||
        reportGenerationStatus !== "success" ||
        !reportUrl ||
        (typeof researchQualityScore === "number" && researchQualityScore < 0.65)
      ) {
        await prisma.event.create({
          data: {
            event: "analysis_degraded",
            submissionId,
            meta: JSON.stringify({
              company: analysis.extraction?.company || "",
              industry: analysis.extraction?.industry || "",
              verdict,
              score,
              renderer_used: rendererUsed,
              report_generation_status: reportGenerationStatus,
              warning_count: warningList.length,
              top_warning:
                warningList[0] ||
                reportGenerationError ||
                missingEvidenceFlags[0] ||
                (!reportUrl ? "Report share unavailable" : ""),
              research_quality_score: researchQualityScore,
              research_coverage_score: researchCoverageScore,
              low_coverage_dimensions: lowCoverageDimensions,
              missing_evidence_flags: missingEvidenceFlags,
              audit_path: auditPath,
            }),
          },
        });
      }

      console.log(
        `[queue] Completed submission ${submissionId}: score=${score}, verdict=${verdict}`
      );
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err);
      console.error(`[queue] Error for submission ${submissionId} (attempt ${retries + 1}):`, errMsg);

      if (retries < MAX_RETRIES) {
        // Re-queue with incremented retry count
        console.log(`[queue] Will retry submission ${submissionId} in ${RETRY_DELAY_MS / 1000}s (attempt ${retries + 2}/${MAX_RETRIES + 1})`);
        await prisma.submission
          .update({ where: { id: submissionId }, data: { status: "queued", adminNotes: `Retry ${retries + 1}/${MAX_RETRIES}: ${errMsg}` } })
          .catch(() => {});

        this.currentJob = null;
        this.processing = false;
        await this.delay(RETRY_DELAY_MS);
        this.queue.push({ submissionId, execSummary, structuredFields, addedAt: Date.now(), retries: retries + 1 });
        this.tick();
        return;
      }

      // All retries exhausted
      await prisma.submission
        .update({
          where: { id: submissionId },
          data: {
            status: "queued",
            adminNotes: `Analysis failed after ${MAX_RETRIES + 1} attempts: ${errMsg}`,
          },
        })
        .catch(() => {});

      await prisma.event
        .create({
          data: {
            event: "analysis_failed",
            submissionId,
            meta: JSON.stringify({
              company: structuredFields.company,
              industry: structuredFields.industry,
              error: errMsg,
              attempts: retries + 1,
            }),
          },
        })
        .catch(() => {});
    } finally {
      if (this.processing) {
        const newCount = await this.incrementDaily();
        this.currentJob = null;
        this.processing = false;
        console.log(`[queue] Daily usage: ${newCount}/${DAILY_LIMIT}`);
        // Process next in queue
        this.tick();
      }
    }
  }
}

// Module-level singleton
const globalQueue = globalThis as typeof globalThis & { __analysisQueue?: AnalysisQueue };

if (!globalQueue.__analysisQueue) {
  globalQueue.__analysisQueue = new AnalysisQueue();
}

export const analysisQueue = globalQueue.__analysisQueue;
