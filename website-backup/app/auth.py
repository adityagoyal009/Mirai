"""
Mirai Portal — Auth routes.

Google OAuth flow + session endpoints.
"""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from .config import settings
from .db import get_db, User, Event, utcnow, AsyncSession

router = APIRouter(tags=["auth"])


# ── Session helpers (used by other modules) ──────────────────────

def get_current_user(request: Request) -> dict | None:
    """Read user from session cookie. Returns None if not logged in."""
    uid = request.session.get("user_id")
    if not uid:
        return None
    return {
        "user_id": uid,
        "email": request.session.get("email", ""),
        "name": request.session.get("name", ""),
        "is_admin": request.session.get("is_admin", False),
    }


def require_user(request: Request) -> dict:
    """Dependency — raises 401 if not authenticated."""
    from fastapi import HTTPException
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, "Authentication required.")
    return user


def require_admin(request: Request) -> dict:
    """Dependency — raises 403 if not admin."""
    from fastapi import HTTPException
    user = require_user(request)
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin access required.")
    return user


def _safe_next(raw: str | None, fallback: str = "/landing/") -> str:
    """Validate redirect target — block open redirects."""
    if not raw or not raw.startswith("/") or raw.startswith("//"):
        return fallback
    return raw


# ── Routes ───────────────────────────────────────────────────────

@router.get("/api/auth/session")
async def session_check(request: Request):
    """Frontend polls this to know auth state."""
    user = get_current_user(request)
    if user:
        return {
            "authenticated": True,
            "google_oauth_configured": settings.google_configured,
            "user": {
                "name": user["name"],
                "email": user["email"],
                "is_admin": user["is_admin"],
            },
        }
    return {
        "authenticated": False,
        "google_oauth_configured": settings.google_configured,
        "user": None,
    }


@router.get("/auth/google/start")
async def google_start(request: Request):
    """Redirect to Google consent screen."""
    if not settings.google_configured:
        return RedirectResponse("/signin/?error=google_not_configured")

    next_url = _safe_next(request.query_params.get("next"))
    request.session["oauth_next"] = next_url

    redirect_uri = str(request.base_url).rstrip("/") + "/auth/google/callback"
    oauth = request.app.state.oauth
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Google's redirect back with auth code."""
    oauth = request.app.state.oauth

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return RedirectResponse("/signin/?error=oauth_failed")

    userinfo = token.get("userinfo") or {}
    if not userinfo:
        return RedirectResponse("/signin/?error=oauth_failed")

    email = (userinfo.get("email") or "").strip()
    if not email or not userinfo.get("email_verified"):
        return RedirectResponse("/signin/?error=email_not_verified")

    name = userinfo.get("name", "")
    picture = userinfo.get("picture", "")
    is_admin = settings.is_admin(email)

    # Upsert user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        user.name = name
        user.picture = picture
        user.is_admin = is_admin
        user.updated_at = utcnow()
    else:
        user = User(
            email=email, name=name, picture=picture,
            is_admin=is_admin, created_at=utcnow(), updated_at=utcnow(),
        )
        db.add(user)

    await db.flush()

    # Log login event
    db.add(Event(
        event="user_login", user_id=user.id,
        meta=json.dumps({"email": email}), created_at=utcnow(),
    ))

    # Set session cookie
    request.session["user_id"] = user.id
    request.session["email"] = email
    request.session["name"] = name
    request.session["is_admin"] = is_admin

    next_url = _safe_next(request.session.pop("oauth_next", None))
    return RedirectResponse(next_url)


@router.get("/auth/logout")
async def logout(request: Request):
    """Clear session and redirect."""
    next_url = _safe_next(request.query_params.get("next"))
    request.session.clear()
    return RedirectResponse(next_url)
