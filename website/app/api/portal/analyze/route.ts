import { NextResponse } from "next/server";
import { MIRAI_API_INTERNAL, MIRAI_API_PUBLIC, getMiraiInternalApiKey, miraiJsonHeaders } from "@/lib/mirai-api";

/**
 * Internal endpoint called after a submission is created.
 * Kicks off the Mirai BI analysis pipeline in the background.
 * Expects: { submissionId, execSummary }
 * This runs server-side only — not exposed to users directly.
 */
export async function POST(request: Request) {
  const authHeader = request.headers.get("x-internal-key");
  const expectedInternalKey = getMiraiInternalApiKey();
  if (expectedInternalKey && authHeader !== expectedInternalKey) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { submissionId, execSummary } = body;

  if (!submissionId || !execSummary) {
    return NextResponse.json({ error: "Missing submissionId or execSummary" }, { status: 400 });
  }

  // Fire and forget — don't block the response
  runAnalysis(submissionId, execSummary).catch((err) => {
    console.error(`[analyze] Pipeline failed for submission ${submissionId}:`, err);
  });

  return NextResponse.json({ message: "Analysis started", submissionId });
}

async function runAnalysis(submissionId: number, execSummary: string) {
  const { PrismaClient } = await import("@prisma/client");
  const prisma = new PrismaClient();

  try {
    // Update status to reviewing
    await prisma.submission.update({
      where: { id: submissionId },
      data: { status: "reviewing" },
    });

    await prisma.event.create({
      data: {
        event: "analysis_started",
        submissionId,
        meta: JSON.stringify({ automated: true }),
      },
    });

    // Call Mirai BI engine
    console.log(`[analyze] Starting analysis for submission ${submissionId}`);
    const analyzeRes = await fetch(`${MIRAI_API_INTERNAL}/api/bi/analyze`, {
      method: "POST",
      headers: miraiJsonHeaders(),
      body: JSON.stringify({ exec_summary: execSummary, depth: "standard" }),
    });

    if (!analyzeRes.ok) {
      const errText = await analyzeRes.text();
      throw new Error(`BI analyze failed (${analyzeRes.status}): ${errText}`);
    }

    const analysis = await analyzeRes.json();

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
        // Make it absolute
        if (reportUrl && !reportUrl.startsWith("http")) {
          reportUrl = `${MIRAI_API_PUBLIC}${reportUrl}`;
        }
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
        adminNotes: reportUrl ? "Report generated automatically by Mirai engine." : "Analysis completed but report generation failed.",
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

    console.log(`[analyze] Completed for submission ${submissionId}: score=${score}, verdict=${verdict}`);
  } catch (err) {
    console.error(`[analyze] Error for submission ${submissionId}:`, err);

    // Mark as queued with error note so admin can handle manually
    await prisma.submission.update({
      where: { id: submissionId },
      data: {
        status: "queued",
        adminNotes: `Automated analysis failed: ${err instanceof Error ? err.message : String(err)}`,
      },
    }).catch(() => {});

    await prisma.event.create({
      data: {
        event: "analysis_failed",
        submissionId,
        meta: JSON.stringify({ error: err instanceof Error ? err.message : String(err) }),
      },
    }).catch(() => {});
  } finally {
    await prisma.$disconnect();
  }
}
