# Intake Audit

Use this whenever you change founder intake fields, submission storage, admin submission displays, backend analysis response metadata, or admin analytics payloads.

## Why

Mirai has a few coupled surfaces that drift easily:

- website intake form
- submit API normalization and validation
- Prisma submission storage
- queue reconstruction of `execSummary` and `structuredFields`
- founder/admin serializers
- admin queue UI
- backend analysis response metadata
- admin analytics events and dashboard

The common failure mode is: one layer is updated, another layer still reflects the old shape, and the product looks stale even though the data is actually stored.

## Fast Audit

Run:

```bash
bash scripts/intake-audit.sh
```

If you changed specific fields, run:

```bash
bash scripts/intake-audit.sh companyName pricingModel founderProblemFit
```

## Surfaces To Check

Core intake path:

- `website/app/submit/page.tsx`
- `website/app/api/portal/submit/route.ts`
- `website/prisma/schema.prisma`
- `website/lib/analysis-queue.ts`

Read / display path:

- `website/lib/utils.ts`
- `website/app/api/admin/submissions/route.ts`
- `website/components/admin/submissions-queue.tsx`
- `website/app/admin/page.tsx`
- `website/app/api/portal/submissions/mine/route.ts`

Backend / report / telemetry path:

- `subconscious/swarm/app.py`
- `website/app/api/admin/analytics/route.ts`
- `website/app/admin/analytics/page.tsx`

## Checklist

1. Write path
   Confirm the live form field exists in the submit page, is accepted by the submit route, and is stored in Prisma.

2. Queue path
   Confirm the saved submission row is reconstructed correctly into `execSummary` and `structuredFields`.

3. Read path
   Confirm admin and founder serializers expose the right shape and the UI expects the same fields.

4. Backend path
   If the backend response shape changed, confirm the queue, analytics route, and analytics page still agree.

5. Verification
   Run the relevant lint / compile checks after patching.

## Required Mindset

Do not stop after fixing the first place you found.

For Mirai, a real fix means tracing the full path:

- user submits
- DB stores
- queue reconstructs
- backend analyzes
- serializers expose
- admin/founder UI renders
- analytics records
