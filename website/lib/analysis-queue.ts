/**
 * Simple in-memory FIFO queue for Mirai analysis jobs.
 * Processes ONE analysis at a time to avoid overloading the backend.
 * Survives across API calls (module-level singleton) but not server restarts.
 * On restart, any "reviewing" submissions get picked up automatically.
 */

import prisma from "./prisma";

const MIRAI_API = process.env.MIRAI_API_URL || "http://127.0.0.1:5000";
const DAILY_LIMIT = 50;
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 10_000; // 10 seconds between retries
const FETCH_TIMEOUT_MS = 3_600_000; // 60 minute timeout per attempt (full analysis with council/swarm)

interface StructuredFields {
  company: string;
  industry: string;
  product: string;
  target_market: string;
  business_model: string;
  stage: string;
  traction: string;
  ask: string;
  website_url: string;
  year_founded: string;
  location: string;
  revenue: string;
  known_competitors: string[];
  funding: string;
  team: string;
  pricing: string;
  country: string;
  keywords: string;
  industry_priority_areas: string;
  has_customers: string;
  generating_revenue: string;
  currently_fundraising: string;
}

interface QueueJob {
  submissionId: number;
  execSummary: string;
  structuredFields: StructuredFields;
  addedAt: number;
  retries: number;
}

class AnalysisQueue {
  private queue: QueueJob[] = [];
  private processing = false;
  private currentJob: QueueJob | null = null;
  private initialized = false;

  constructor() {
    // Recover stuck submissions on startup (handles server restarts)
    this.recoverStuck().catch((err) =>
      console.error("[queue] Startup recovery failed:", err)
    );
  }

  private async recoverStuck() {
    const stuck = await prisma.submission.findMany({
      where: { status: "reviewing" },
      select: { id: true, companyName: true },
    });
    if (stuck.length > 0) {
      console.log(`[queue] Found ${stuck.length} stuck "reviewing" submission(s) — resetting to queued`);
      await prisma.submission.updateMany({
        where: { status: "reviewing" },
        data: { status: "queued", adminNotes: "Reset after server restart — will be re-queued on next submission." },
      });
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
      const res = await fetch(`${MIRAI_API}/health`, {
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
            meta: JSON.stringify({ automated: true, queueRemaining: this.queue.length }),
          },
        });
      }

      // Submit job to Mirai BI engine (async mode — returns immediately with job ID)
      const submitRes = await fetch(`${MIRAI_API}/api/bi/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          exec_summary: execSummary,
          structured_fields: structuredFields || null,
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
          const pollRes = await fetch(`${MIRAI_API}/api/bi/job/${jobId}`, {
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
            meta: JSON.stringify({ fields_missing: analysis.fields_missing }),
          },
        });
        return;
      }

      // Extract score and verdict
      const council = analysis.council || {};
      const score = council.overall ?? analysis.prediction?.score ?? null;
      const verdict = council.verdict ?? analysis.prediction?.verdict ?? "";

      // Generate shareable HTML report
      let reportUrl = "";
      const reportHtml = analysis.report_html || analysis.html_report;
      if (reportHtml) {
        try {
          const shareRes = await fetch(`${MIRAI_API}/api/report/share`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              html: reportHtml,
              company: analysis.extraction?.company || `Submission #${submissionId}`,
            }),
          });
          if (shareRes.ok) {
            const shareData = await shareRes.json();
            reportUrl = shareData.url || "";
            if (reportUrl && !reportUrl.startsWith("http")) {
              reportUrl = `${MIRAI_API}${reportUrl}`;
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
            score,
            verdict,
            has_report: Boolean(reportUrl),
            analysis_id: analysis.analysis_id,
          }),
        },
      });

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
            meta: JSON.stringify({ error: errMsg, attempts: retries + 1 }),
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
