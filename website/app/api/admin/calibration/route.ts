import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import prisma from "@/lib/prisma";

const DIMENSIONS = [
  "market_timing",
  "competition_landscape",
  "business_model_viability",
  "team_execution_signals",
  "regulatory_news_env",
  "social_proof_demand",
  "pattern_match",
  "capital_efficiency",
  "scalability_potential",
  "exit_potential",
] as const;

const POSITIVE_OUTCOMES = ["raised_round", "revenue_milestone", "acquired"];
const NEGATIVE_OUTCOMES = ["shut_down", "stalled"];

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.isAdmin) {
    return NextResponse.json({ error: "Admin access required." }, { status: 403 });
  }

  const url = new URL(request.url);
  const industry = url.searchParams.get("industry") || "";
  const stage = url.searchParams.get("stage") || "";
  const targetSubmissionId = url.searchParams.get("submission_id")
    ? parseInt(url.searchParams.get("submission_id")!, 10)
    : null;

  // Get all analysis results, optionally filtered
  const whereClause: Record<string, unknown> = {};
  if (industry || stage) {
    whereClause.submission = {};
    if (industry) (whereClause.submission as Record<string, unknown>).industry = { contains: industry };
    if (stage) (whereClause.submission as Record<string, unknown>).stage = { contains: stage };
  }

  const results = await prisma.analysisResult.findMany({
    where: whereClause,
    include: {
      submission: { select: { id: true, companyName: true, industry: true, stage: true } },
    },
    orderBy: { createdAt: "desc" },
  });

  const totalAnalyses = results.length;

  // Score distribution
  const scores = results.map((r) => r.compositeScore).sort((a, b) => a - b);
  const scoreDistribution = {
    count: scores.length,
    min: scores[0] ?? null,
    max: scores[scores.length - 1] ?? null,
    median: scores.length > 0 ? scores[Math.floor(scores.length / 2)] : null,
    mean: scores.length > 0 ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 100) / 100 : null,
    p25: scores.length >= 4 ? scores[Math.floor(scores.length * 0.25)] : null,
    p75: scores.length >= 4 ? scores[Math.floor(scores.length * 0.75)] : null,
  };

  // Verdict distribution
  const verdictCounts: Record<string, number> = {};
  for (const r of results) {
    const v = r.finalVerdict || "Unknown";
    verdictCounts[v] = (verdictCounts[v] || 0) + 1;
  }

  // Outcome correlation
  const outcomes = await prisma.outcome.findMany({
    where: { submissionId: { in: results.map((r) => r.submissionId) } },
  });

  const outcomesBySubmission: Record<number, string[]> = {};
  for (const o of outcomes) {
    if (!outcomesBySubmission[o.submissionId]) outcomesBySubmission[o.submissionId] = [];
    outcomesBySubmission[o.submissionId].push(o.outcomeType);
  }

  const verdictOutcomes: Record<string, { positive: number; negative: number; neutral: number; total: number }> = {};
  for (const r of results) {
    const v = r.finalVerdict || "Unknown";
    if (!verdictOutcomes[v]) verdictOutcomes[v] = { positive: 0, negative: 0, neutral: 0, total: 0 };

    const types = outcomesBySubmission[r.submissionId] || [];
    if (types.length === 0) continue;

    verdictOutcomes[v].total++;
    if (types.some((t) => POSITIVE_OUTCOMES.includes(t))) verdictOutcomes[v].positive++;
    else if (types.some((t) => NEGATIVE_OUTCOMES.includes(t))) verdictOutcomes[v].negative++;
    else verdictOutcomes[v].neutral++;
  }

  // Dimension predictive power (avg score for positive vs negative outcomes)
  const dimensionPower: Record<string, { positive_avg: number | null; negative_avg: number | null; spread: number | null }> = {};

  const submissionsWithPositive = new Set<number>();
  const submissionsWithNegative = new Set<number>();
  for (const [sid, types] of Object.entries(outcomesBySubmission)) {
    const id = parseInt(sid, 10);
    if (types.some((t) => POSITIVE_OUTCOMES.includes(t))) submissionsWithPositive.add(id);
    else if (types.some((t) => NEGATIVE_OUTCOMES.includes(t))) submissionsWithNegative.add(id);
  }

  for (const dim of DIMENSIONS) {
    const councilKey = `council${dim.split("_").map((w) => w[0].toUpperCase() + w.slice(1)).join("")}` as keyof typeof results[0];

    const positiveScores: number[] = [];
    const negativeScores: number[] = [];

    for (const r of results) {
      const val = r[councilKey];
      if (typeof val !== "number") continue;
      if (submissionsWithPositive.has(r.submissionId)) positiveScores.push(val);
      else if (submissionsWithNegative.has(r.submissionId)) negativeScores.push(val);
    }

    const posAvg = positiveScores.length >= 2
      ? Math.round((positiveScores.reduce((a, b) => a + b, 0) / positiveScores.length) * 100) / 100
      : null;
    const negAvg = negativeScores.length >= 2
      ? Math.round((negativeScores.reduce((a, b) => a + b, 0) / negativeScores.length) * 100) / 100
      : null;

    dimensionPower[dim] = {
      positive_avg: posAvg,
      negative_avg: negAvg,
      spread: posAvg !== null && negAvg !== null ? Math.round((posAvg - negAvg) * 100) / 100 : null,
    };
  }

  // Percentile ranking for a specific submission
  let percentileRanking: Record<string, number> | null = null;
  if (targetSubmissionId) {
    const target = results.find((r) => r.submissionId === targetSubmissionId);
    if (target) {
      percentileRanking = { composite_score: 0 };
      const belowComposite = results.filter((r) => r.compositeScore < target.compositeScore).length;
      percentileRanking.composite_score = Math.round((belowComposite / totalAnalyses) * 100);

      for (const dim of DIMENSIONS) {
        const councilKey = `council${dim.split("_").map((w) => w[0].toUpperCase() + w.slice(1)).join("")}` as keyof typeof target;
        const targetVal = target[councilKey];
        if (typeof targetVal !== "number") continue;
        const below = results.filter((r) => {
          const v = r[councilKey];
          return typeof v === "number" && v < targetVal;
        }).length;
        percentileRanking![dim] = Math.round((below / totalAnalyses) * 100);
      }
    }
  }

  // Summary stats
  const totalOutcomes = outcomes.length;
  const pendingFollowUps = await prisma.followUp.count({
    where: { status: "pending", dueAt: { lte: new Date() } },
  });
  const submissionsWithOutcomes = new Set(outcomes.map((o) => o.submissionId)).size;
  const outcomeCoverageRate = totalAnalyses > 0
    ? Math.round((submissionsWithOutcomes / totalAnalyses) * 100)
    : 0;

  return NextResponse.json({
    total_analyses: totalAnalyses,
    total_outcomes: totalOutcomes,
    pending_follow_ups: pendingFollowUps,
    outcome_coverage_rate: outcomeCoverageRate,
    score_distribution: scoreDistribution,
    verdict_distribution: verdictCounts,
    verdict_outcome_correlation: verdictOutcomes,
    dimension_predictive_power: dimensionPower,
    percentile_ranking: percentileRanking,
    filters: { industry: industry || null, stage: stage || null },
  });
}
