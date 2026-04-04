## Mirai Website

Next.js founder portal and admin interface for Mirai submissions.

## Environment

Required:

```bash
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
NEXTAUTH_SECRET=
NEXTAUTH_URL=http://localhost:3000
MIRAI_ADMIN_EMAILS=your-email@example.com
DATABASE_URL=file:./data/mirai_portal.db
MIRAI_API_INTERNAL_URL=http://127.0.0.1:5000
MIRAI_API_PUBLIC_URL=https://vclabs.org
```

Optional:

```bash
# Dedicated shared secret for website -> swarm calls.
MIRAI_INTERNAL_API_KEY=
```

If the website and swarm run as separate services, set the same `MIRAI_INTERNAL_API_KEY` in both environments.

## Getting Started

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Operational Notes

- Founder intake is now rating-oriented, not just summary-oriented. The form captures structured buyer, proof, pricing/GTM, implementation, substitute, evidence, founder-fit, and risk fields.
- Website submissions send those fields as structured passthrough payloads to the swarm backend instead of relying on backend-side LLM extraction.
- Submissions are serialized through a single-worker in-memory queue to protect downstream model capacity.
- Daily operating target is `50 analyses / 24h`.
- On restart, resumable `queued` and `reviewing` submissions are rebuilt from the database into the queue automatically.
- Founder-facing APIs return safe `status_message` values instead of raw internal admin notes.
- Founder queue responses expose only the current user's queue positions.
- Website analyses persist the final blended verdict and score (`composite_score` / `overall_score`), not just the raw council score.
- Shared report HTML is generated after OASIS and final-verdict enrichment so the saved report reflects the final state.
- Fact-check data can be surfaced from top-level, prediction-level, or swarm-level payloads during report rendering.
