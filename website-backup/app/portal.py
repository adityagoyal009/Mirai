"""
Mirai Portal — User-facing submission routes.

POST /submit      — queue a startup brief
GET  /submissions/mine — list the user's own requests
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from .auth import require_user
from .db import get_db, Submission, Event, utcnow, AsyncSession

router = APIRouter(tags=["portal"])


@router.post("/submit")
async def submit_brief(request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticated user submits a startup brief for review."""
    user = require_user(request)
    body = await request.json()

    company_name = (body.get("companyName") or "").strip()
    if not company_name:
        raise HTTPException(400, "Company name is required.")

    one_liner = (body.get("oneLiner") or "").strip()
    if not one_liner:
        raise HTTPException(400, "One-line pitch is required.")

    sub = Submission(
        user_id=user["user_id"],
        company_name=company_name,
        website_url=(body.get("websiteUrl") or "").strip(),
        industry=(body.get("industry") or "").strip(),
        stage=(body.get("stage") or "").strip(),
        one_liner=one_liner,
        customers=(body.get("customers") or "").strip(),
        business_model=(body.get("businessModel") or "").strip(),
        traction=(body.get("traction") or "").strip(),
        deck_url=(body.get("deckUrl") or "").strip(),
        advantage=(body.get("advantage") or "").strip(),
        risk=(body.get("risk") or "").strip(),
        status="queued",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(sub)
    await db.flush()

    db.add(Event(
        event="submission_created",
        submission_id=sub.id,
        user_id=user["user_id"],
        meta=json.dumps({"company": company_name, "industry": sub.industry}),
        created_at=utcnow(),
    ))

    return {
        "message": "Request received and queued for review.",
        "submission": {"id": sub.id, "created_at": sub.created_at},
    }


@router.get("/submissions/mine")
async def my_submissions(request: Request, db: AsyncSession = Depends(get_db)):
    """List the current user's submissions, newest first."""
    user = require_user(request)

    result = await db.execute(
        select(Submission)
        .where(Submission.user_id == user["user_id"])
        .order_by(Submission.created_at.desc())
    )
    subs = result.scalars().all()

    return {
        "submissions": [
            {
                "id": s.id,
                "company_name": s.company_name,
                "one_liner": s.one_liner,
                "status": s.status,
                "admin_notes": s.admin_notes,
                "created_at": s.created_at,
            }
            for s in subs
        ]
    }
