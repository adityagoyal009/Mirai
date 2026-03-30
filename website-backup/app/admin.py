"""
Mirai Portal — Admin routes.

GET  /analytics              — dashboard stats, charts, breakdowns
GET  /submissions            — all submissions with filters
POST /submissions/{id}/status — update status + admin notes
"""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func, distinct

from .auth import require_admin
from .db import (
    get_db, User, Submission, Event, utcnow,
    VALID_STATUSES, AsyncSession,
)

router = APIRouter(tags=["admin"])


def _submission_dict(sub: Submission, user: User | None = None) -> dict:
    """Serialize a Submission to the shape admin.html expects."""
    d = {
        "id": sub.id,
        "company_name": sub.company_name,
        "website_url": sub.website_url,
        "industry": sub.industry,
        "stage": sub.stage,
        "one_liner": sub.one_liner,
        "customers": sub.customers,
        "business_model": sub.business_model,
        "traction": sub.traction,
        "deck_url": sub.deck_url,
        "advantage": sub.advantage,
        "risk": sub.risk,
        "status": sub.status,
        "admin_notes": sub.admin_notes,
        "created_at": sub.created_at,
        "updated_at": sub.updated_at,
    }
    if user:
        d["requester_name"] = user.name
        d["requester_email"] = user.email
    return d


# ── Analytics ────────────────────────────────────────────────────

@router.get("/analytics")
async def analytics(request: Request, db: AsyncSession = Depends(get_db)):
    """Dashboard-level stats: totals, daily chart, breakdowns, events."""
    require_admin(request)
    days = int(request.query_params.get("days", "14"))
    limit = int(request.query_params.get("limit", "100"))
    now = datetime.now(timezone.utc)

    # ── Totals ──
    total = (await db.execute(select(func.count(Submission.id)))).scalar() or 0

    status_counts: dict[str, int] = {}
    for st in VALID_STATUSES:
        cnt = (await db.execute(
            select(func.count(Submission.id)).where(Submission.status == st)
        )).scalar() or 0
        status_counts[st] = cnt

    cutoff_7d = (now - timedelta(days=7)).isoformat()
    last_7d = (await db.execute(
        select(func.count(Submission.id)).where(Submission.created_at >= cutoff_7d)
    )).scalar() or 0

    unique_requesters = (await db.execute(
        select(func.count(distinct(Submission.user_id)))
    )).scalar() or 0

    completion_rate = round(status_counts.get("report_sent", 0) / total * 100) if total else 0

    totals = {
        "submissions": total,
        "queued": status_counts.get("queued", 0),
        "reviewing": status_counts.get("reviewing", 0),
        "report_sent": status_counts.get("report_sent", 0),
        "archived": status_counts.get("archived", 0),
        "submissions_last_7d": last_7d,
        "completion_rate": completion_rate,
        "unique_requesters": unique_requesters,
    }

    # ── Daily submissions (gap-filled) ──
    cutoff_daily = (now - timedelta(days=days)).date()
    daily_raw = await db.execute(
        select(
            func.substr(Submission.created_at, 1, 10).label("day"),
            func.count(Submission.id).label("cnt"),
        )
        .where(Submission.created_at >= cutoff_daily.isoformat())
        .group_by("day")
        .order_by("day")
    )
    daily_map = {row.day: row.cnt for row in daily_raw}
    daily_submissions = [
        {"date": (cutoff_daily + timedelta(days=i)).isoformat(),
         "count": daily_map.get((cutoff_daily + timedelta(days=i)).isoformat(), 0)}
        for i in range(days)
    ]

    # ── Breakdowns ──
    status_bd = await db.execute(
        select(Submission.status, func.count(Submission.id).label("cnt"))
        .group_by(Submission.status)
        .order_by(func.count(Submission.id).desc())
    )
    status_breakdown = [{"label": r.status, "count": r.cnt} for r in status_bd]

    industry_bd = await db.execute(
        select(Submission.industry, func.count(Submission.id).label("cnt"))
        .where(Submission.industry != "")
        .group_by(Submission.industry)
        .order_by(func.count(Submission.id).desc())
    )
    industry_breakdown = [{"label": r.industry, "count": r.cnt} for r in industry_bd]

    stage_bd = await db.execute(
        select(Submission.stage, func.count(Submission.id).label("cnt"))
        .where(Submission.stage != "")
        .group_by(Submission.stage)
        .order_by(func.count(Submission.id).desc())
    )
    stage_breakdown = [{"label": r.stage, "count": r.cnt} for r in stage_bd]

    # ── Recent events ──
    events_result = await db.execute(
        select(Event).order_by(Event.created_at.desc()).limit(limit)
    )
    recent_events = []
    for ev in events_result.scalars().all():
        meta = {}
        try:
            meta = json.loads(ev.meta) if ev.meta else {}
        except (json.JSONDecodeError, TypeError):
            pass
        recent_events.append({
            "event": ev.event,
            "company": meta.get("company", ""),
            "industry": meta.get("industry", ""),
            "ts": ev.created_at,
        })

    return {
        "totals": totals,
        "daily_submissions": daily_submissions,
        "status_breakdown": status_breakdown,
        "industry_breakdown": industry_breakdown,
        "stage_breakdown": stage_breakdown,
        "recent_events": recent_events,
    }


# ── Submissions list ─────────────────────────────────────────────

@router.get("/submissions")
async def list_submissions(request: Request, db: AsyncSession = Depends(get_db)):
    """All submissions, optionally filtered by status."""
    require_admin(request)
    limit = int(request.query_params.get("limit", "100"))
    status_filter = (request.query_params.get("status") or "").strip()

    query = select(Submission, User).join(User, Submission.user_id == User.id)
    if status_filter in VALID_STATUSES:
        query = query.where(Submission.status == status_filter)
    query = query.order_by(Submission.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return {"submissions": [_submission_dict(sub, user) for sub, user in result.all()]}


# ── Status update ────────────────────────────────────────────────

@router.post("/submissions/{submission_id}/status")
async def update_status(
    submission_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Admin sets a new status and optional notes on a submission."""
    admin = require_admin(request)
    body = await request.json()

    new_status = (body.get("status") or "").strip()
    if new_status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be: {', '.join(sorted(VALID_STATUSES))}")

    admin_notes = (body.get("adminNotes") or "").strip()

    result = await db.execute(
        select(Submission, User)
        .join(User, Submission.user_id == User.id)
        .where(Submission.id == submission_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(404, "Submission not found.")

    sub, user = row
    old_status = sub.status
    sub.status = new_status
    sub.admin_notes = admin_notes
    sub.updated_at = utcnow()

    db.add(Event(
        event="status_changed",
        submission_id=sub.id,
        user_id=admin["user_id"],
        meta=json.dumps({
            "company": sub.company_name,
            "old_status": old_status,
            "new_status": new_status,
            "admin_email": admin["email"],
        }),
        created_at=utcnow(),
    ))

    return {"submission": _submission_dict(sub, user)}
