"""
Mirai Portal helpers.

Provides:
- Concierge-style submission storage for the landing page
- Admin analytics aggregation
- Google OAuth helpers using the standard web-server OAuth flow
"""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional

from ..utils.logger import get_logger
from .analytics import analytics

logger = get_logger("mirai.portal")

_PORTAL_DIR = os.path.expanduser(
    os.environ.get("MIRAI_PORTAL_DIR", "~/.mirai/portal")
)
_DB_PATH = os.path.join(_PORTAL_DIR, "portal.db")
_EVENTS_FILE = os.path.join(
    os.path.expanduser(os.environ.get("MIRAI_ANALYTICS_DIR", "~/.mirai/analytics")),
    "events.jsonl",
)

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

VALID_SUBMISSION_STATUSES = {
    "queued",
    "reviewing",
    "report_sent",
    "archived",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _clean_text(value: Any, max_len: int = 8000) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) > max_len:
        return text[:max_len].strip()
    return text


def _connect() -> sqlite3.Connection:
    os.makedirs(_PORTAL_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_portal_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                requester_sub TEXT NOT NULL,
                requester_email TEXT NOT NULL,
                requester_name TEXT,
                company_name TEXT NOT NULL,
                website_url TEXT,
                industry TEXT,
                stage TEXT,
                one_liner TEXT NOT NULL,
                customers TEXT,
                business_model TEXT,
                traction TEXT,
                advantage TEXT,
                risk TEXT,
                deck_url TEXT,
                brief_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                admin_notes TEXT NOT NULL DEFAULT '',
                source_ip TEXT,
                user_agent TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_created_at ON submissions(created_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_requester_sub ON submissions(requester_sub)"
        )


def _row_to_submission(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "requester_sub": row["requester_sub"],
        "requester_email": row["requester_email"],
        "requester_name": row["requester_name"],
        "company_name": row["company_name"],
        "website_url": row["website_url"],
        "industry": row["industry"],
        "stage": row["stage"],
        "one_liner": row["one_liner"],
        "customers": row["customers"],
        "business_model": row["business_model"],
        "traction": row["traction"],
        "advantage": row["advantage"],
        "risk": row["risk"],
        "deck_url": row["deck_url"],
        "brief_text": row["brief_text"],
        "status": row["status"],
        "admin_notes": row["admin_notes"],
        "source_ip": row["source_ip"],
        "user_agent": row["user_agent"],
    }


def build_submission_brief(payload: Dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Company: {_clean_text(payload.get('company_name')) or 'N/A'}",
            f"Website: {_clean_text(payload.get('website_url')) or 'N/A'}",
            f"Industry: {_clean_text(payload.get('industry')) or 'N/A'}",
            f"Stage: {_clean_text(payload.get('stage')) or 'N/A'}",
            "",
            "One-line pitch:",
            _clean_text(payload.get("one_liner")) or "N/A",
            "",
            "Customer and market:",
            _clean_text(payload.get("customers")) or "N/A",
            "",
            "Business model:",
            _clean_text(payload.get("business_model")) or "N/A",
            "",
            "Traction or proof:",
            _clean_text(payload.get("traction")) or "N/A",
            "",
            "Why this team might win:",
            _clean_text(payload.get("advantage")) or "N/A",
            "",
            "Main open question:",
            _clean_text(payload.get("risk")) or "N/A",
            "",
            "Deck or data room link:",
            _clean_text(payload.get("deck_url")) or "N/A",
        ]
    )


def get_submission(submission_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()
    return _row_to_submission(row) if row else None


def create_submission(
    *,
    user: Dict[str, Any],
    payload: Dict[str, Any],
    source_ip: str = "",
    user_agent: str = "",
) -> Dict[str, Any]:
    init_portal_db()

    company_name = _clean_text(payload.get("company_name"), 240)
    one_liner = _clean_text(payload.get("one_liner"), 1000)
    if not company_name:
        raise ValueError("company_name is required")
    if not one_liner:
        raise ValueError("one_liner is required")

    normalized = {
        "company_name": company_name,
        "website_url": _clean_text(payload.get("website_url"), 500),
        "industry": _clean_text(payload.get("industry"), 120),
        "stage": _clean_text(payload.get("stage"), 120),
        "one_liner": one_liner,
        "customers": _clean_text(payload.get("customers")),
        "business_model": _clean_text(payload.get("business_model")),
        "traction": _clean_text(payload.get("traction")),
        "advantage": _clean_text(payload.get("advantage")),
        "risk": _clean_text(payload.get("risk")),
        "deck_url": _clean_text(payload.get("deck_url"), 500),
    }
    brief_text = build_submission_brief(normalized)
    now = _utc_now_iso()

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO submissions (
                created_at,
                updated_at,
                requester_sub,
                requester_email,
                requester_name,
                company_name,
                website_url,
                industry,
                stage,
                one_liner,
                customers,
                business_model,
                traction,
                advantage,
                risk,
                deck_url,
                brief_text,
                status,
                admin_notes,
                source_ip,
                user_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', '', ?, ?)
            """,
            (
                now,
                now,
                _clean_text(user.get("sub"), 200),
                _clean_text(user.get("email"), 320).lower(),
                _clean_text(user.get("name"), 240),
                normalized["company_name"],
                normalized["website_url"],
                normalized["industry"],
                normalized["stage"],
                normalized["one_liner"],
                normalized["customers"],
                normalized["business_model"],
                normalized["traction"],
                normalized["advantage"],
                normalized["risk"],
                normalized["deck_url"],
                brief_text,
                _clean_text(source_ip, 120),
                _clean_text(user_agent, 500),
            ),
        )
        submission_id = int(cursor.lastrowid)

    analytics.track(
        "portal_submission_created",
        {
            "submission_id": submission_id,
            "industry": normalized["industry"],
            "stage": normalized["stage"],
            "status": "queued",
        },
    )
    return get_submission(submission_id) or {"id": submission_id}


def list_user_submissions(requester_sub: str, limit: int = 10) -> list[Dict[str, Any]]:
    init_portal_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM submissions
            WHERE requester_sub = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (_clean_text(requester_sub, 200), max(1, min(limit, 100))),
        ).fetchall()
    return [_row_to_submission(row) for row in rows]


def list_submissions(limit: int = 50, status: str = "") -> list[Dict[str, Any]]:
    init_portal_db()
    params: list[Any] = []
    query = "SELECT * FROM submissions"
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(max(1, min(limit, 500)))
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_submission(row) for row in rows]


def update_submission_status(
    submission_id: int,
    *,
    status: str,
    admin_notes: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    init_portal_db()
    normalized_status = _clean_text(status, 64)
    if normalized_status not in VALID_SUBMISSION_STATUSES:
        raise ValueError(f"invalid status '{normalized_status}'")

    current = get_submission(submission_id)
    if not current:
        return None

    notes_value = current["admin_notes"] if admin_notes is None else _clean_text(admin_notes)
    with _connect() as conn:
        conn.execute(
            """
            UPDATE submissions
            SET status = ?, admin_notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (normalized_status, notes_value, _utc_now_iso(), submission_id),
        )

    analytics.track(
        "portal_submission_status_updated",
        {
            "submission_id": submission_id,
            "status": normalized_status,
        },
    )
    return get_submission(submission_id)


def _all_submissions() -> list[Dict[str, Any]]:
    init_portal_db()
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM submissions ORDER BY created_at DESC").fetchall()
    return [_row_to_submission(row) for row in rows]


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _date_range_counts(rows: Iterable[Dict[str, Any]], days: int = 14) -> list[Dict[str, Any]]:
    today = _utc_now().date()
    counts = {today - timedelta(days=offset): 0 for offset in range(days - 1, -1, -1)}
    for row in rows:
        created_at = _parse_iso(row.get("created_at", ""))
        if not created_at:
            continue
        row_date = created_at.astimezone(timezone.utc).date()
        if row_date in counts:
            counts[row_date] += 1
    return [
        {"date": day.isoformat(), "count": counts[day]}
        for day in sorted(counts.keys())
    ]


def _top_counts(rows: Iterable[Dict[str, Any]], key: str, limit: int = 8) -> list[Dict[str, Any]]:
    counter = Counter()
    for row in rows:
        value = _clean_text(row.get(key), 120)
        if value:
            counter[value] += 1
    return [
        {"label": label, "count": count}
        for label, count in counter.most_common(limit)
    ]


def _load_recent_events(limit: int = 5000) -> list[Dict[str, Any]]:
    if not os.path.exists(_EVENTS_FILE):
        return []
    events: list[Dict[str, Any]] = []
    try:
        with open(_EVENTS_FILE, "r", encoding="utf-8") as handle:
            lines = handle.readlines()[-limit:]
    except OSError as exc:
        logger.warning(f"[Portal] Could not read analytics events: {exc}")
        return []

    for line in lines:
        try:
            payload = json.loads(line.strip())
        except json.JSONDecodeError:
            continue
        events.append(payload)
    return events


def portal_dashboard_data(days: int = 14, limit: int = 100) -> Dict[str, Any]:
    rows = _all_submissions()
    recent_rows = rows[: max(1, min(limit, 300))]
    now = _utc_now()
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    status_counter = Counter(row["status"] for row in rows)
    unique_requesters = len({row["requester_sub"] for row in rows if row["requester_sub"]})
    last_7d = 0
    last_30d = 0
    for row in rows:
        created_at = _parse_iso(row.get("created_at", ""))
        if not created_at:
            continue
        if created_at >= cutoff_7d:
            last_7d += 1
        if created_at >= cutoff_30d:
            last_30d += 1

    recent_events = []
    event_counter = Counter()
    for event in reversed(_load_recent_events()):
        event_name = _clean_text(event.get("event"), 120)
        event_ts = _parse_iso(_clean_text(event.get("ts"), 64))
        if not event_name or not event_ts:
            continue
        if event_ts >= cutoff_30d:
            event_counter[event_name] += 1
        if len(recent_events) < 20:
            recent_events.append(
                {
                    "event": event_name,
                    "ts": event_ts.isoformat(),
                    "company": _clean_text(event.get("company"), 240),
                    "status": _clean_text(event.get("status"), 64),
                    "industry": _clean_text(event.get("industry"), 120),
                }
            )

    report_sent = status_counter.get("report_sent", 0)
    total_submissions = len(rows)
    completion_rate = round((report_sent / total_submissions) * 100, 1) if total_submissions else 0.0

    return {
        "totals": {
            "submissions": total_submissions,
            "queued": status_counter.get("queued", 0),
            "reviewing": status_counter.get("reviewing", 0),
            "report_sent": report_sent,
            "archived": status_counter.get("archived", 0),
            "unique_requesters": unique_requesters,
            "submissions_last_7d": last_7d,
            "submissions_last_30d": last_30d,
            "completion_rate": completion_rate,
        },
        "status_breakdown": [
            {"label": label, "count": count}
            for label, count in status_counter.items()
        ],
        "industry_breakdown": _top_counts(rows, "industry"),
        "stage_breakdown": _top_counts(rows, "stage"),
        "daily_submissions": _date_range_counts(rows, days=days),
        "recent_submissions": recent_rows,
        "event_counts_30d": [
            {"label": label, "count": count}
            for label, count in event_counter.most_common(12)
        ],
        "recent_events": recent_events,
        "usage_summary": analytics.summary(),
    }


def build_google_auth_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
            "include_granted_scopes": "true",
        }
    )
    return f"{GOOGLE_AUTH_ENDPOINT}?{query}"


def _request_json(
    url: str,
    *,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    payload = None
    final_headers = dict(headers or {})
    if data is not None:
        payload = urllib.parse.urlencode(data).encode("utf-8")
        final_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

    req = urllib.request.Request(url, data=payload, method=method, headers=final_headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google OAuth request failed ({exc.code}): {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Google OAuth request failed: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Google OAuth returned invalid JSON") from exc


def exchange_google_code(
    *,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> Dict[str, Any]:
    return _request_json(
        GOOGLE_TOKEN_ENDPOINT,
        method="POST",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )


def fetch_google_userinfo(access_token: str) -> Dict[str, Any]:
    return _request_json(
        GOOGLE_USERINFO_ENDPOINT,
        headers={"Authorization": f"Bearer {access_token}"},
    )
