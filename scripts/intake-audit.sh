#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FILES=(
  "$ROOT/website/app/submit/page.tsx"
  "$ROOT/website/app/api/portal/submit/route.ts"
  "$ROOT/website/prisma/schema.prisma"
  "$ROOT/website/lib/analysis-queue.ts"
  "$ROOT/website/lib/utils.ts"
  "$ROOT/website/app/api/admin/submissions/route.ts"
  "$ROOT/website/components/admin/submissions-queue.tsx"
  "$ROOT/website/app/admin/page.tsx"
  "$ROOT/website/app/api/portal/submissions/mine/route.ts"
  "$ROOT/subconscious/swarm/app.py"
  "$ROOT/website/app/api/admin/analytics/route.ts"
  "$ROOT/website/app/admin/analytics/page.tsx"
)

echo "Mirai intake audit surfaces:"
printf ' - %s\n' "${FILES[@]#$ROOT/}"
echo

if [ "$#" -gt 0 ]; then
  pattern="$(printf '%s|' "$@")"
  pattern="${pattern%|}"
  echo "Searching for requested fields/patterns:"
  echo "  $pattern"
else
  pattern="buildExecSummary|buildStructuredFields|serializeSubmission|serializeFounderSubmission|submission_created|analysis_started|analysis_complete|analysis_degraded|admin_summary|report_renderer|llm_report_html_preview"
  echo "Searching for key integration points:"
  echo "  $pattern"
fi

echo
rg -n "$pattern" "${FILES[@]}" || true
