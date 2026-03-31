"""
Mirai (未来) + Sensei (先生) — FastAPI Application

Production server with uvicorn for:
- Native async WebSocket
- No port conflict crashes
- Multiple workers for concurrent requests
- Auto-generated API docs at /docs

Run:
  uvicorn subconscious.swarm.app:app --host 0.0.0.0 --port 5000
  uvicorn subconscious.swarm.app:app --host 0.0.0.0 --port 5000 --workers 2
"""

import os
import json
import asyncio
import secrets
import threading
import time
import uuid
import urllib.parse
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from .config import Config
from .services.analytics import analytics
from .services.final_verdict import finalize_prediction
from .services.portal import (
    VALID_SUBMISSION_STATUSES,
    build_google_auth_url,
    create_submission,
    exchange_google_code,
    fetch_google_userinfo,
    init_portal_db,
    list_submissions,
    list_user_submissions,
    portal_dashboard_data,
    update_submission_status,
)
from .utils.logger import get_logger

logger = get_logger('mirai.app')

# ── Paths ──
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DASHBOARD_DIST = os.path.join(_BASE, "dashboard", "dist")
_GAME_DIST = os.path.join(_BASE, "dashboard-game", "dist")
_WEBSITE_DIR = os.path.join(_BASE, "website")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Redirect websocket.py's sync broadcast to app.py's async WebSocket broadcast.
    # websocket.py broadcast() pushes to sync queues; this bridges to async WebSocket.
    # All analysis/chat threads resolve broadcast() via module global at runtime,
    # so this single patch ensures every call reaches FastAPI WebSocket clients.
    import subconscious.swarm.api.websocket as ws_module
    ws_module.broadcast = _sync_broadcast
    init_portal_db()
    logger.info("[Mirai] FastAPI server starting (uvicorn)")
    yield
    logger.info("[Mirai] FastAPI server shutting down")


app = FastAPI(
    title="Mirai (未来) + Sensei (先生)",
    description="AI Due Diligence Reports + AI Mentor Sessions — VCLabs.org",
    version="0.9.0",
    lifespan=lifespan,
    docs_url="/docs",
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _session_secret() -> str:
    secret = os.environ.get("MIRAI_SESSION_SECRET", "").strip()
    if secret:
        return secret
    logger.warning("[Portal] MIRAI_SESSION_SECRET not set; using local development fallback")
    return "mirai-dev-session-secret-change-me"


def _internal_api_key() -> str:
    return (
        os.environ.get("MIRAI_INTERNAL_API_KEY", "").strip()
        or os.environ.get("NEXTAUTH_SECRET", "").strip()
    )


def _request_internal_key(request: Request) -> str:
    header = request.headers.get("x-internal-key", "").strip()
    if header:
        return header

    authorization = request.headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()

    return ""


def _is_loopback_request(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in {"127.0.0.1", "::1", "localhost"}


def _require_internal_request(request: Request, *, throttle_local: bool = False):
    expected = _internal_api_key()
    provided = _request_internal_key(request)

    if expected:
        if provided and secrets.compare_digest(provided, expected):
            return None
        logger.warning("[Security] Rejected internal endpoint request without valid key")
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    if _is_loopback_request(request):
        if throttle_local and not check_rate_limit(request):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)
        return None

    logger.warning("[Security] Rejected non-local internal endpoint request without MIRAI_INTERNAL_API_KEY configured")
    return JSONResponse({"error": "Internal API not configured"}, status_code=503)


app.add_middleware(
    SessionMiddleware,
    secret_key=_session_secret(),
    same_site="lax",
    https_only=_bool_env("MIRAI_SESSION_HTTPS_ONLY", False),
    max_age=60 * 60 * 24 * 30,
)


# ══════════════════════════════════════════════════════════════════
# STATIC FILES — Dashboard + Game
# ══════════════════════════════════════════════════════════════════

if os.path.isdir(os.path.join(_DASHBOARD_DIST, "assets")):
    app.mount("/dashboard/assets", StaticFiles(directory=os.path.join(_DASHBOARD_DIST, "assets")), name="dashboard-assets")

if os.path.isdir(os.path.join(_GAME_DIST, "assets")):
    app.mount("/game/assets", StaticFiles(directory=os.path.join(_GAME_DIST, "assets")), name="game-assets")

# Sprite + sound assets for game
for subdir in ["sprites", "sounds", "maps"]:
    path = os.path.join(_GAME_DIST, subdir)
    if os.path.isdir(path):
        app.mount(f"/{subdir}", StaticFiles(directory=path), name=f"game-{subdir}")


def _google_oauth_configured() -> bool:
    return bool(
        os.environ.get("GOOGLE_CLIENT_ID", "").strip()
        and os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    )


def _admin_emails() -> set[str]:
    raw = os.environ.get("MIRAI_ADMIN_EMAILS") or os.environ.get("MIRAI_ADMIN_EMAIL", "")
    return {
        item.strip().lower()
        for item in raw.split(",")
        if item.strip()
    }


def _safe_next_url(next_url: str | None) -> str:
    candidate = (next_url or "/landing/").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return "/landing/"
    return candidate


def _google_redirect_uri(request: Request) -> str:
    configured = os.environ.get("MIRAI_GOOGLE_REDIRECT_URI") or os.environ.get("GOOGLE_REDIRECT_URI")
    if configured:
        return configured.strip()
    return str(request.url_for("google_auth_callback"))


def _session_user(request: Request) -> dict | None:
    user = request.session.get("user")
    return user if isinstance(user, dict) else None


def _public_user(user: dict | None) -> dict | None:
    if not user:
        return None
    return {
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        "picture": user.get("picture", ""),
        "is_admin": bool(user.get("is_admin")),
    }


def _signin_redirect(next_url: str) -> RedirectResponse:
    quoted = urllib.parse.quote(_safe_next_url(next_url), safe="")
    return RedirectResponse(f"/signin/?next={quoted}")


@app.get("/landing")
@app.get("/landing/")
async def landing_page():
    return FileResponse(os.path.join(_WEBSITE_DIR, "index.html"))


@app.get("/signin")
@app.get("/signin/")
async def signin_page():
    return FileResponse(os.path.join(_WEBSITE_DIR, "signin.html"))


@app.get("/admin")
@app.get("/admin/")
async def admin_page(request: Request):
    user = _session_user(request)
    if not user:
        return _signin_redirect("/admin/")
    if not user.get("is_admin"):
        return JSONResponse({"error": "Admin access required"}, status_code=403)
    analytics.track("portal_admin_page_view", {"role": "admin"})
    return FileResponse(os.path.join(_WEBSITE_DIR, "admin.html"))


@app.get("/api/auth/session")
async def auth_session(request: Request):
    user = _session_user(request)
    return {
        "authenticated": bool(user),
        "google_oauth_configured": _google_oauth_configured(),
        "user": _public_user(user),
    }


@app.get("/auth/google/start")
async def google_auth_start(request: Request, next: str = "/landing/"):
    if not _google_oauth_configured():
        return RedirectResponse("/signin/?error=google_not_configured")

    state = secrets.token_urlsafe(32)
    safe_next = _safe_next_url(next)
    request.session["oauth_state"] = state
    request.session["oauth_next"] = safe_next

    auth_url = build_google_auth_url(
        client_id=os.environ.get("GOOGLE_CLIENT_ID", "").strip(),
        redirect_uri=_google_redirect_uri(request),
        state=state,
    )
    analytics.track("portal_login_started", {"next": safe_next})
    return RedirectResponse(auth_url)


@app.get("/auth/google/callback")
async def google_auth_callback(request: Request, state: str = "", code: str = "", error: str = ""):
    if error:
        return RedirectResponse(f"/signin/?error={urllib.parse.quote(error)}")

    expected_state = request.session.pop("oauth_state", "")
    next_url = _safe_next_url(request.session.pop("oauth_next", "/landing/"))
    if not code or not state or state != expected_state:
        return RedirectResponse("/signin/?error=state_mismatch")

    try:
        token_data = exchange_google_code(
            code=code,
            client_id=os.environ.get("GOOGLE_CLIENT_ID", "").strip(),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", "").strip(),
            redirect_uri=_google_redirect_uri(request),
        )
        access_token = str(token_data.get("access_token", "")).strip()
        if not access_token:
            raise RuntimeError("Missing access token from Google")
        profile = fetch_google_userinfo(access_token)
    except Exception as exc:
        logger.warning(f"[Portal] Google login failed: {exc}")
        return RedirectResponse("/signin/?error=oauth_failed")

    email = str(profile.get("email", "")).strip().lower()
    if not email or not profile.get("email_verified", False):
        return RedirectResponse("/signin/?error=email_not_verified")

    user = {
        "sub": str(profile.get("sub", "")).strip(),
        "email": email,
        "name": str(profile.get("name", "")).strip(),
        "picture": str(profile.get("picture", "")).strip(),
        "is_admin": email in _admin_emails(),
    }
    request.session["user"] = user
    analytics.track("portal_login_success", {"is_admin": user["is_admin"]})
    return RedirectResponse(next_url)


@app.get("/auth/logout")
async def auth_logout(request: Request, next: str = "/landing/"):
    request.session.clear()
    return RedirectResponse(_safe_next_url(next))


@app.post("/api/portal/submit")
async def portal_submit(request: Request):
    user = _session_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    body = await request.json()
    payload = {
        "company_name": body.get("companyName", ""),
        "website_url": body.get("websiteUrl", ""),
        "industry": body.get("industry", ""),
        "stage": body.get("stage", ""),
        "one_liner": body.get("oneLiner", ""),
        "customers": body.get("customers", ""),
        "business_model": body.get("businessModel", ""),
        "traction": body.get("traction", ""),
        "advantage": body.get("advantage", ""),
        "risk": body.get("risk", ""),
        "deck_url": body.get("deckUrl", ""),
    }
    try:
        submission = await asyncio.to_thread(
            create_submission,
            user=user,
            payload=payload,
            source_ip=_get_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        logger.error(f"[Portal] Submission failed: {exc}")
        return JSONResponse({"error": "Could not save submission"}, status_code=500)

    return {
        "ok": True,
        "message": "Request received. We will review it and send the report within 24 hours.",
        "submission": submission,
    }


@app.get("/api/portal/submissions/mine")
async def portal_my_submissions(request: Request, limit: int = 10):
    user = _session_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    submissions = await asyncio.to_thread(
        list_user_submissions,
        user.get("sub", ""),
        limit,
    )
    return {"submissions": submissions}


@app.get("/api/admin/analytics")
async def admin_analytics(request: Request, days: int = 14, limit: int = 100):
    user = _session_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    if not user.get("is_admin"):
        return JSONResponse({"error": "Admin access required"}, status_code=403)
    data = await asyncio.to_thread(portal_dashboard_data, days, limit)
    return data


@app.get("/api/admin/submissions")
async def admin_submissions(request: Request, limit: int = 100, status: str = ""):
    user = _session_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    if not user.get("is_admin"):
        return JSONResponse({"error": "Admin access required"}, status_code=403)
    if status and status not in VALID_SUBMISSION_STATUSES:
        return JSONResponse({"error": "Invalid status filter"}, status_code=400)
    submissions = await asyncio.to_thread(list_submissions, limit, status)
    return {"submissions": submissions}


@app.post("/api/admin/submissions/{submission_id}/status")
async def admin_update_submission_status(request: Request, submission_id: int):
    user = _session_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    if not user.get("is_admin"):
        return JSONResponse({"error": "Admin access required"}, status_code=403)

    body = await request.json()
    status = str(body.get("status", "")).strip()
    admin_notes = body.get("adminNotes")
    try:
        submission = await asyncio.to_thread(
            update_submission_status,
            submission_id,
            status=status,
            admin_notes=admin_notes,
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    if not submission:
        return JSONResponse({"error": "Submission not found"}, status_code=404)
    return {"ok": True, "submission": submission}


@app.get("/")
async def root():
    return RedirectResponse("/dashboard/")


@app.get("/dashboard/{path:path}")
async def dashboard_spa(path: str = ""):
    file_path = os.path.join(_DASHBOARD_DIST, path)
    if path and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(_DASHBOARD_DIST, "index.html"))


@app.get("/dashboard/")
async def dashboard_root():
    return FileResponse(os.path.join(_DASHBOARD_DIST, "index.html"))


@app.get("/game/{path:path}")
async def game_spa(path: str = ""):
    file_path = os.path.join(_GAME_DIST, path)
    if path and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(_GAME_DIST, "index.html"))


@app.get("/game/")
async def game_root():
    return FileResponse(os.path.join(_GAME_DIST, "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Mirai + Sensei API", "framework": "FastAPI"}


# ══════════════════════════════════════════════════════════════════
# WEBSOCKET — /ws/swarm (Mirai Analysis Pipeline)
# ══════════════════════════════════════════════════════════════════

import queue as thread_queue  # thread-safe queue

class ConnectionManager:
    """Manages WebSocket connections with a thread-safe queue for sync→async broadcast."""

    def __init__(self, name: str = "ws"):
        self.connections: list[WebSocket] = []
        self._lock = asyncio.Lock()
        self._queue = thread_queue.Queue()  # Thread-safe!
        self._drain_started = False
        self._name = name

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self.connections.append(ws)
        # Start drain task on first connection
        if not self._drain_started:
            asyncio.create_task(self._drain_queue())
            self._drain_started = True
        logger.info(f"[{self._name}] Client connected ({len(self.connections)} total)")

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self.connections:
                self.connections.remove(ws)
        logger.info(f"[{self._name}] Client disconnected")

    async def broadcast(self, msg: dict):
        data = json.dumps(msg, default=str)
        async with self._lock:
            dead = []
            for ws in self.connections:
                try:
                    await ws.send_text(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.connections.remove(ws)

    def enqueue(self, msg: dict):
        """Thread-safe: put a message in the queue (called from ANY thread)."""
        self._queue.put_nowait(msg)

    async def _drain_queue(self):
        """Background task: poll thread-safe queue and broadcast to WebSocket clients."""
        logger.info(f"[{self._name}] Queue drain task started")
        while True:
            try:
                # Non-blocking check of thread-safe queue
                try:
                    msg = self._queue.get_nowait()
                    await self.broadcast(msg)
                except thread_queue.Empty:
                    await asyncio.sleep(0.05)  # 50ms poll interval
            except Exception as e:
                logger.warning(f"[{self._name}] Drain error: {e}")
                await asyncio.sleep(0.1)

swarm_mgr = ConnectionManager("WS")
sensei_mgr = ConnectionManager("Sensei")

def _sync_broadcast(msg: dict):
    """Thread-safe broadcast — puts in thread-safe queue, drain task picks it up."""
    swarm_mgr.enqueue(msg)


def _sensei_sync_broadcast(msg: dict):
    """Thread-safe broadcast for Sensei."""
    sensei_mgr.enqueue(msg)


@app.websocket("/ws/swarm")
async def swarm_ws(ws: WebSocket):
    await swarm_mgr.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")
            logger.info(f"[WS] Received message type: {msg_type}")

            if msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

            elif msg_type == "startAnalysis":
                # Rate limit check before starting analysis
                _ws_ip = (
                    ws.headers.get("cf-connecting-ip")
                    or (ws.headers.get("x-forwarded-for", "").split(",")[0].strip())
                    or (ws.client.host if ws.client else "unknown")
                )
                _now = _time_mod.time()
                if _ws_ip not in _rate_limit_store:
                    _rate_limit_store[_ws_ip] = []
                _rate_limit_store[_ws_ip] = [t for t in _rate_limit_store[_ws_ip] if _now - t < _RATE_LIMIT_WINDOW]
                if len(_rate_limit_store[_ws_ip]) >= _RATE_LIMIT_MAX:
                    await ws.send_json({
                        "type": "error",
                        "message": f"Rate limit exceeded. Maximum {_RATE_LIMIT_MAX} analyses per hour. Please try again later.",
                    })
                    continue
                _rate_limit_store[_ws_ip].append(_now)

                # Run analysis in background thread (services are sync)
                asyncio.get_running_loop().run_in_executor(
                    None, _run_swarm_analysis, msg
                )

            elif msg_type == "chatWithAgent":
                asyncio.get_running_loop().run_in_executor(
                    None, _handle_agent_chat, msg
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"[WS] Swarm connection error: {e}")
    finally:
        await swarm_mgr.disconnect(ws)


def _run_swarm_analysis(msg: dict):
    """Run the full Mirai pipeline in a thread. broadcast() is patched at startup in lifespan."""
    try:
        import subconscious.swarm.api.websocket as ws_module
        ws_module._handle_full_analysis(msg)
    except Exception as e:
        logger.error(f"[WS] Analysis failed: {e}")
        _sync_broadcast({"type": "error", "error": str(e)})


def _handle_agent_chat(msg: dict):
    """Handle agent chat in a thread. broadcast() is patched at startup in lifespan."""
    try:
        import subconscious.swarm.api.websocket as ws_module
        if hasattr(ws_module, '_handle_agent_chat'):
            ws_module._handle_agent_chat(msg)
    except Exception as e:
        _sync_broadcast({"type": "error", "error": str(e)})


# ══════════════════════════════════════════════════════════════════
# WEBSOCKET — /ws/sensei (Mentor Sessions)
# ══════════════════════════════════════════════════════════════════

# sensei_mgr already created above as ConnectionManager("Sensei")
# _sensei_sync_broadcast already defined above

# Active sensei sessions
_sensei_sessions: dict = {}


@app.websocket("/ws/sensei")
async def sensei_ws(ws: WebSocket):
    await sensei_mgr.connect(ws)
    session_key = id(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

            elif msg_type == "startSession":
                asyncio.get_running_loop().run_in_executor(
                    None, _start_sensei_session, msg, session_key
                )

            elif msg_type == "chatMessage":
                mentor_id = msg.get("mentorId", "")
                user_message = msg.get("message", "")
                session = _sensei_sessions.get(session_key)
                if session and mentor_id and user_message:
                    asyncio.get_running_loop().run_in_executor(
                        None, _sensei_chat, session, mentor_id, user_message
                    )

            elif msg_type == "endMentorChat":
                mentor_id = msg.get("mentorId", "")
                session = _sensei_sessions.get(session_key)
                if session and mentor_id:
                    transcript = session.end_session(mentor_id)
                    _sensei_sync_broadcast({"type": "mentorEnded", "mentorId": mentor_id, "transcript": transcript})

            elif msg_type == "endSession":
                session = _sensei_sessions.get(session_key)
                if session:
                    summary = session.get_session_summary()
                    _sensei_sync_broadcast({"type": "sessionSummary", **summary})

            elif msg_type == "getMentorTypes":
                from .services.mentor_session import MENTOR_TYPES
                _sensei_sync_broadcast({
                    "type": "mentorTypes",
                    "mentors": [
                        {"id": k, "name": v["name"], "tagline": v["tagline"], "zone": v["zone"]}
                        for k, v in MENTOR_TYPES.items()
                    ],
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"[Sensei WS] Connection error: {e}")
    finally:
        await sensei_mgr.disconnect(ws)
        _sensei_sessions.pop(session_key, None)


def _start_sensei_session(msg: dict, session_key):
    """Start a sensei session in a thread."""
    try:
        from .services.mentor_session import MentorSession, MENTOR_TYPES
        from .services.business_intel import BusinessIntelEngine
        from .services.persona_engine import PersonaEngine

        exec_summary = msg.get("execSummary", "")
        selected_mentors = msg.get("selectedMentors", [])

        if not exec_summary or not selected_mentors:
            _sensei_sync_broadcast({"type": "error", "error": "Missing exec summary or mentors"})
            return

        _sensei_sync_broadcast({"type": "researchStarted"})

        # Extract fields
        bi = BusinessIntelEngine()
        extraction = bi.extract_and_validate(exec_summary)
        _sensei_sync_broadcast({"type": "researchProgress", "status": "Extracting startup details..."})

        # Try cached research
        research_context = exec_summary
        try:
            from .services.research_cache import ResearchCache
            cache = ResearchCache()
            cache_key = cache.make_key(
                getattr(extraction, 'company', ''),
                getattr(extraction, 'industry', ''),
            )
            cached = cache.get(cache_key)
            if cached and hasattr(cached, 'summary') and cached.summary:
                research_context = json.dumps({
                    "summary": cached.summary[:2000],
                    "competitors": getattr(cached, 'competitors', [])[:10],
                }, default=str)
                _sensei_sync_broadcast({"type": "researchProgress", "status": "Using cached research"})
        except Exception:
            pass

        _sensei_sync_broadcast({"type": "researchComplete", "status": "Mentors briefed"})

        # Generate mentors
        engine = PersonaEngine()
        session = MentorSession(research_context=research_context, exec_summary=exec_summary)

        ready = []
        for i, mt in enumerate(selected_mentors):
            mdef = MENTOR_TYPES.get(mt)
            if not mdef:
                continue
            try:
                personas = engine._generate_personas(
                    count=1, zone=mdef["zone"],
                    startup_industry=getattr(extraction, 'industry', ''),
                    priority_roles=[mdef["role"]],
                )
                prompt = personas[0].prompt if personas else f"You are a {mdef['name']}."
            except Exception:
                prompt = f"You are a {mdef['name']}."

            mid = f"{mt}_{i}"
            session.create_mentor(mid, mt, prompt)
            ready.append({"id": mid, "name": mdef["name"], "type": mt, "tagline": mdef["tagline"], "zone": mdef["zone"], "room": i + 1})

        _sensei_sessions[session_key] = session
        _sensei_sync_broadcast({"type": "mentorsReady", "mentors": ready})

    except Exception as e:
        logger.error(f"[Sensei] Session start failed: {e}")
        _sensei_sync_broadcast({"type": "error", "error": str(e)})


def _sensei_chat(session, mentor_id: str, user_message: str):
    """Handle a sensei chat message in a thread."""
    try:
        response = session.chat(mentor_id, user_message)
        state = session.sessions.get(mentor_id)
        _sensei_sync_broadcast({
            "type": "mentorResponse",
            "mentorId": mentor_id,
            "message": response,
            "timeRemaining": state.time_remaining if state else 0,
        })
    except Exception as e:
        _sensei_sync_broadcast({"type": "mentorResponse", "mentorId": mentor_id, "message": "Let me think about that...", "timeRemaining": 0})


# ══════════════════════════════════════════════════════════════════
# REST API — Business Intelligence
# ══════════════════════════════════════════════════════════════════

@app.get("/api/bi/template")
async def bi_template():
    return {
        "template": "Company: ...\nIndustry: ...\nProduct: ...\nTarget Market: ...\nBusiness Model: ...\nStage: ...",
        "example": "Company: CleanSentinels\nIndustry: CleanTech\nProduct: AI water quality monitoring",
    }


# ── Async job store for long-running analyses ──
_job_results: dict = {}  # job_id -> {"status": "running"|"complete"|"error", "result": ..., "started": float}
_job_lock = threading.Lock()

def _cleanup_old_jobs():
    """Remove jobs older than 2 hours."""
    cutoff = time.time() - 7200
    with _job_lock:
        expired = [k for k, v in _job_results.items() if v.get("started", 0) < cutoff]
        for k in expired:
            del _job_results[k]


@app.get("/api/bi/job/{job_id}")
async def bi_job_status(job_id: str, request: Request):
    """Poll for async analysis result."""
    auth_error = _require_internal_request(request)
    if auth_error:
        return auth_error
    with _job_lock:
        job = _job_results.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    if job["status"] == "running":
        return {"status": "running", "job_id": job_id, "elapsed": round(time.time() - job["started"], 1)}
    if job["status"] == "error":
        return {"status": "error", "job_id": job_id, "error": job.get("error", "Unknown error")}
    return job["result"]


@app.post("/api/bi/analyze")
async def bi_analyze(request: Request):
    auth_error = _require_internal_request(request, throttle_local=True)
    if auth_error:
        return auth_error
    body = await request.json()
    exec_summary = body.get("exec_summary", "")
    depth = body.get("depth", "deep")
    agent_count = body.get("agent_count", 50)
    simulate_market = body.get("simulate_market", True)
    async_mode = body.get("async", True)  # default async for website
    if not exec_summary:
        return JSONResponse({"error": "Missing exec_summary"}, status_code=400)

    if len(exec_summary) > 50000:
        exec_summary = exec_summary[:50000]

    structured_fields = body.get("structured_fields", None)

    def _run_full_pipeline():
        import threading
        from .services.business_intel import BusinessIntelEngine, ExtractionResult
        from .services.swarm_predictor import SwarmPredictor

        bi = BusinessIntelEngine()

        # Phase 0: Extract & Validate
        # Use structured fields passthrough when available (skips lossy LLM extraction)
        if structured_fields and isinstance(structured_fields, dict) and structured_fields.get("company"):
            extraction = ExtractionResult(
                company=structured_fields.get("company", ""),
                industry=structured_fields.get("industry", ""),
                product=structured_fields.get("product", ""),
                target_market=structured_fields.get("target_market", ""),
                end_user=structured_fields.get("end_user", ""),
                economic_buyer=structured_fields.get("economic_buyer", ""),
                switching_trigger=structured_fields.get("switching_trigger", ""),
                business_model=structured_fields.get("business_model", ""),
                stage=structured_fields.get("stage", ""),
                traction=structured_fields.get("traction", ""),
                loi_count=structured_fields.get("loi_count", ""),
                pilot_count=structured_fields.get("pilot_count", ""),
                active_customer_count=structured_fields.get("active_customer_count", ""),
                paid_customer_count=structured_fields.get("paid_customer_count", ""),
                monthly_revenue_value=structured_fields.get("monthly_revenue_value", ""),
                growth_rate=structured_fields.get("growth_rate", ""),
                ask=structured_fields.get("ask", ""),
                claims=[],
                key_differentiators=[],
                website_url=structured_fields.get("website_url", ""),
                year_founded=structured_fields.get("year_founded", ""),
                location=structured_fields.get("location", ""),
                revenue=structured_fields.get("revenue", ""),
                known_competitors=structured_fields.get("known_competitors", []),
                funding=structured_fields.get("funding", ""),
                team=structured_fields.get("team", ""),
                pricing=structured_fields.get("pricing", ""),
                pricing_model=structured_fields.get("pricing_model", ""),
                starting_price=structured_fields.get("starting_price", ""),
                sales_motion=structured_fields.get("sales_motion", ""),
                typical_contract_size=structured_fields.get("typical_contract_size", ""),
                implementation_complexity=structured_fields.get("implementation_complexity", ""),
                time_to_value=structured_fields.get("time_to_value", ""),
                current_substitute=structured_fields.get("current_substitute", ""),
                demo_url=structured_fields.get("demo_url", ""),
                customer_proof_url=structured_fields.get("customer_proof_url", ""),
                pilot_docs_url=structured_fields.get("pilot_docs_url", ""),
                founder_problem_fit=structured_fields.get("founder_problem_fit", ""),
                founder_years_in_industry=structured_fields.get("founder_years_in_industry", ""),
                technical_founder=structured_fields.get("technical_founder", ""),
                primary_risk_category=structured_fields.get("primary_risk_category", ""),
            )
            extraction = bi._compute_data_quality(extraction)
            logger.info(f"[BI-REST] Structured passthrough: company={extraction.company}, "
                       f"data_quality={extraction.data_quality}")
        else:
            extraction = bi.extract_and_validate(exec_summary)

        critical_missing = [f for f in ["company", "industry", "product"]
                           if f in extraction.fields_missing]
        if critical_missing:
            return {
                "status": "needs_more_info",
                "data_quality": extraction.data_quality,
                "fields_missing": extraction.fields_missing,
                "missing_critical": critical_missing,
                "message": f"Cannot produce a reliable analysis — missing: {', '.join(critical_missing)}.",
            }

        stage = extraction.stage or ""

        # Start blind scoring in parallel with research (same as dashboard)
        _blind_scores = [None]
        _blind_thread = None
        use_council = depth == "deep"
        if use_council:
            from .config import Config as _cfg
            _council_models = _cfg.get_council_models()
            if _council_models and len(_council_models) > 1:
                def _run_blind_scoring():
                    try:
                        from .utils.llm_client import LLMClient
                        from concurrent.futures import ThreadPoolExecutor, as_completed
                        results = {}
                        with ThreadPoolExecutor(max_workers=len(_council_models)) as pool:
                            def _blind_one(mcfg):
                                llm = LLMClient(model=mcfg["model"])
                                return mcfg["label"], bi._predict_blind(exec_summary, llm, stage=stage)
                            futs = [pool.submit(_blind_one, m) for m in _council_models]
                            for f in as_completed(futs):
                                try:
                                    lbl, scores = f.result()
                                    results[lbl] = scores
                                except Exception:
                                    pass
                        _blind_scores[0] = results
                        logger.info(f"[BI-REST] Blind scoring: {len(results)} models (parallel with research)")
                    except Exception as e:
                        logger.warning(f"[BI-REST] Blind scoring failed: {e}")

                _blind_thread = threading.Thread(target=_run_blind_scoring, daemon=True)
                _blind_thread.start()

        # Phase 1: Research (OpenClaw primary, Gemini fallback)
        try:
            research_report = bi.research(exec_summary, depth=depth, extraction=extraction)
            research = research_report.to_dict() if hasattr(research_report, "to_dict") else research_report
            logger.info(
                f"[BI-REST] Live research: {len(research.get('facts', []))} facts, "
                f"{len(research.get('competitors', []))} competitors, {len(research.get('sources', []))} sources"
            )
        except Exception as e:
            logger.error(f"[BI-REST] Live research failed — stopping pipeline: {e}")
            raise RuntimeError(f"Research failed: {e}") from e

        # Wait for blind scoring to fully finish before council/swarm
        # No timeout — blind scoring has its own per-model timeouts (7 min Claude, 3 min others).
        # If we time out here, blind thread keeps running and overlaps with swarm = NVIDIA 429s.
        if _blind_thread is not None:
            _blind_thread.join()
            if _blind_scores[0]:
                logger.info(f"[BI-REST] Blind scores ready: {len(_blind_scores[0])} models")

        # Phase 2: Council prediction (with blind scores from parallel thread)
        prediction = bi.predict(
            exec_summary, research, use_council=use_council,
            industry=extraction.industry, stage=stage,
            data_quality=extraction.data_quality,
            blind_scores_cache=_blind_scores[0],
        )

        # Phase 2b: Swarm prediction
        swarm_result = None
        if agent_count > 0:
            try:
                swarm = SwarmPredictor()
                research_context = json.dumps(research, indent=2, default=str)[:6000]
                enriched_context = (
                    f"RESEARCH FINDINGS:\n{json.dumps(research, indent=2, default=str)}\n\n"
                    f"Given this research, evaluate this startup independently from your unique perspective."
                )
                swarm_result = swarm.predict(
                    exec_summary=exec_summary,
                    research_context=enriched_context,
                    agent_count=agent_count,
                    company=extraction.company,
                    industry=extraction.industry,
                    product=extraction.product,
                    target_market=" | ".join(
                        part for part in [
                            extraction.target_market,
                            f"End user: {extraction.end_user}" if extraction.end_user else "",
                            f"Economic buyer: {extraction.economic_buyer}" if extraction.economic_buyer else "",
                            f"Switching trigger: {extraction.switching_trigger}" if extraction.switching_trigger else "",
                            f"Current substitute: {extraction.current_substitute}" if extraction.current_substitute else "",
                        ]
                        if part
                    ),
                    stage=stage,
                    research_data=research if isinstance(research, dict) else None,
                )
                logger.info(f"[BI-REST] Swarm: {swarm_result.positive_pct}% positive, "
                           f"{swarm_result.negative_pct}% negative")
            except Exception as e:
                logger.warning(f"[BI-REST] Swarm failed (non-fatal): {e}")

        # Phase 3: Strategy plan
        plan_dict = {}
        try:
            plan = bi.plan(exec_summary, research, prediction)
            plan_dict = plan.to_dict() if hasattr(plan, 'to_dict') else plan
        except Exception as e:
            logger.warning(f"[BI-REST] Plan failed (non-fatal): {e}")

        # Build result (matches dashboard structure)
        result = {
            "status": "complete",
            "id": f"bi_{uuid.uuid4().hex[:12]}",
            "exec_summary": exec_summary,
            "extraction": extraction.to_dict() if hasattr(extraction, 'to_dict') else {},
            "research": research,
            "prediction": prediction.to_dict() if hasattr(prediction, 'to_dict') else prediction,
            "plan": plan_dict,
            "data_quality": extraction.data_quality,
            "fields_present": extraction.fields_present,
            "fields_missing": extraction.fields_missing,
        }
        if swarm_result:
            result["swarm"] = swarm_result.to_dict()
            if getattr(swarm_result, "fact_check", None):
                result["fact_check"] = swarm_result.fact_check

        # Phase 4: OASIS Market Simulation
        if simulate_market:
            try:
                from .services.oasis_simulator import OasisSimulator
                oasis_sim = OasisSimulator()
                pred = result.get("prediction", {})
                council_v = f"{pred.get('overall_score', 0)}/10 - {pred.get('verdict', 'Unknown')}"
                res_ctx = json.dumps(result.get("research", {}), default=str)
                stg = result.get("extraction", {}).get("stage", "")
                oasis_swarm_agents = None
                if swarm_result and hasattr(swarm_result, "agent_results"):
                    oasis_swarm_agents = swarm_result.agent_results
                oasis_result = oasis_sim.simulate(
                    exec_summary=exec_summary, research_context=res_ctx,
                    council_verdict=council_v, stage=stg,
                    swarm_agents=oasis_swarm_agents,
                    extraction=result.get("extraction", {}),
                )
                result["oasis"] = oasis_result
                logger.info(f"[BI-REST] OASIS: {oasis_result.get('trajectory')}")
            except Exception as e:
                logger.warning(f"[BI-REST] OASIS failed (non-fatal): {e}")
                result["oasis"] = {}

        prediction_view = result.get("prediction", {})
        if not isinstance(prediction_view, dict):
            prediction_view = prediction.to_dict() if hasattr(prediction, "to_dict") else {}

        final_prediction = finalize_prediction(
            prediction_view,
            swarm=result.get("swarm") if isinstance(result.get("swarm"), dict) else None,
            oasis=result.get("oasis") if isinstance(result.get("oasis"), dict) else None,
        )
        prediction_view.update({
            "verdict": final_prediction["final_verdict"],
            "confidence": final_prediction["final_confidence"],
            "composite_score": final_prediction["composite_score"],
            "council_verdict": final_prediction["council_verdict"],
            "council_confidence": final_prediction["council_confidence"],
            "council_score": final_prediction["council_score"],
            "swarm_verdict": final_prediction["swarm_verdict"],
            "swarm_confidence": final_prediction["swarm_confidence"],
            "swarm_score": final_prediction["swarm_score"],
        })
        result["prediction"] = prediction_view
        result["final_verdict"] = final_prediction["final_verdict"]
        result["final_confidence"] = final_prediction["final_confidence"]
        if final_prediction["warnings"]:
            result["warnings"] = final_prediction["warnings"]
        logger.info(
            f"[BI-REST] Final verdict: {final_prediction['final_verdict']} "
            f"(score={final_prediction['composite_score']}, confidence={final_prediction['final_confidence']})"
        )

        # Generate narrative sections via ReportAgent (same as dashboard WebSocket path)
        try:
            from .services.report_agent import ReportAgent
            report_agent = ReportAgent()
            report_sections = report_agent.generate_report(result)
            result["report_sections"] = report_sections
            result["narrative"] = "\n\n".join(
                f"{title}\n{content}" for title, content in report_sections.items()
            ) if report_sections else ""
            logger.info(f"[BI-REST] ReportAgent: {len(report_sections)} sections generated")
        except Exception as e:
            logger.warning(f"[BI-REST] ReportAgent failed (non-fatal): {e}")

        # Generate HTML report after OASIS/final-verdict enrichment so the shared
        # report includes the full final state.
        try:
            from .services.report_generator import generate_html_report
            html = generate_html_report(result, narrative=result.get("narrative", ""))
            if html:
                result["report_html"] = html
        except Exception as e:
            logger.warning(f"[BI-REST] Report generation failed (non-fatal): {e}")

        return result

    # ── Async mode: return job ID, run in background ──
    if async_mode:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        with _job_lock:
            _job_results[job_id] = {"status": "running", "started": time.time()}
        _cleanup_old_jobs()

        def _background_job():
            try:
                result = _run_full_pipeline()
                with _job_lock:
                    _job_results[job_id] = {"status": "complete", "result": result, "started": time.time()}
                logger.info(f"[BI-REST] Job {job_id} complete")
            except Exception as e:
                logger.error(f"[BI-REST] Job {job_id} failed: {e}")
                with _job_lock:
                    _job_results[job_id] = {"status": "error", "error": str(e), "started": time.time()}

        threading.Thread(target=_background_job, daemon=True).start()
        return {"status": "accepted", "job_id": job_id, "poll_url": f"/api/bi/job/{job_id}"}

    # ── Sync mode: block until complete (for backward compat) ──
    result = await asyncio.to_thread(_run_full_pipeline)
    return result


@app.post("/api/bi/extract-pdf")
async def bi_extract_pdf(file: UploadFile = File(...)):
    content = await file.read()
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        from .services.business_intel import BusinessIntelEngine
        bi = BusinessIntelEngine()
        result = await asyncio.to_thread(bi.extract_pdf, tmp_path)
        return {"success": True, "extraction": result}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        os.unlink(tmp_path)


@app.post("/api/bi/report/pdf")
async def bi_report_pdf(request: Request):
    body = await request.json()
    # Frontend sends { analysis: { ... } }, unwrap if needed
    analysis = body.get("analysis", body)
    from .services.llm_report_generator import generate_pdf_report
    from fastapi.responses import Response
    pdf_bytes = await asyncio.to_thread(generate_pdf_report, analysis)
    if pdf_bytes and isinstance(pdf_bytes, bytes) and pdf_bytes[:5] == b'%PDF-':
        company = analysis.get("extraction", {}).get("company", "report")
        safe_name = ''.join(c if c.isalnum() or c in '-_ ' else '' for c in company).strip().replace(' ', '-').lower()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="mirai-report-{safe_name}.pdf"'},
        )
    return JSONResponse({"error": "PDF generation failed — invalid output"}, status_code=500)


@app.get("/api/bi/report/html/{report_id}")
async def bi_report_html_cached(report_id: str):
    """Serve cached HTML report by ID. Generated during analysis, opened in new tab."""
    from .services.llm_report_generator import _html_cache
    from fastapi.responses import HTMLResponse
    html = _html_cache.get(report_id)
    if html:
        return HTMLResponse(content=html)
    return JSONResponse({"error": "Report not found or expired. Run a new analysis."}, status_code=404)


@app.get("/api/bi/history")
async def bi_history():
    from .services.business_intel import BusinessIntelEngine
    bi = BusinessIntelEngine()
    return await asyncio.to_thread(bi.get_history)


@app.get("/api/bi/accuracy")
async def bi_accuracy():
    from .services.business_intel import BusinessIntelEngine
    bi = BusinessIntelEngine()
    return await asyncio.to_thread(bi.get_accuracy)


# ══════════════════════════════════════════════════════════════════
# SHAREABLE REPORT LINKS — /report/{uuid}
# ══════════════════════════════════════════════════════════════════

import uuid as _uuid_mod
import html as _html_mod

_REPORTS_DIR = os.path.join(os.path.expanduser("~"), ".mirai", "shared_reports")
_MAX_SHARED_REPORT_BYTES = int(os.environ.get("MIRAI_SHARED_REPORT_MAX_BYTES", "1000000"))
os.makedirs(_REPORTS_DIR, exist_ok=True)


def _sanitize_report_html(html: str) -> str:
    """Strip dangerous tags/attributes from LLM-generated report HTML.

    Removes script, iframe, object, embed, form, and event handler attributes
    to prevent stored XSS when serving shared reports."""
    import re
    # Remove script tags and their content
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove other dangerous tags
    for tag in ['iframe', 'object', 'embed', 'form', 'link', 'meta[^>]*http-equiv']:
        html = re.sub(rf'<{tag}[^>]*>.*?</{tag.split("[")[0]}>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(rf'<{tag}[^>]*/?\s*>', '', html, flags=re.IGNORECASE)
    # Remove event handler attributes (onclick, onerror, onload, etc.)
    html = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+on\w+\s*=\s*\S+', '', html, flags=re.IGNORECASE)
    # Remove javascript: URLs
    html = re.sub(r'(href|src|action)\s*=\s*["\']javascript:[^"\']*["\']', r'\1=""', html, flags=re.IGNORECASE)
    return html


def save_shared_report(report_html: str, company_name: str = "") -> str:
    """Save report HTML to disk, return the UUID for the shareable link.

    Sanitizes the HTML to prevent stored XSS from LLM-generated content."""
    report_id = str(_uuid_mod.uuid4())
    safe_path = os.path.join(_REPORTS_DIR, f"{report_id}.html")

    # Sanitize LLM-generated HTML
    report_html = _sanitize_report_html(report_html)

    # Wrap in a minimal page if it's a fragment
    if not report_html.strip().lower().startswith("<!doctype") and not report_html.strip().lower().startswith("<html"):
        report_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Mirai Report — {_html_mod.escape(company_name)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}</style>
</head>
<body>{report_html}</body></html>"""

    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(report_html)

    logger.info(f"[Share] Report saved: {report_id} ({len(report_html)} bytes)")
    return report_id


@app.get("/report/{report_id}")
async def shared_report(report_id: str):
    """Serve a shared report by UUID."""
    # Validate UUID format to prevent path traversal
    try:
        _uuid_mod.UUID(report_id)
    except ValueError:
        return JSONResponse({"error": "Invalid report ID"}, status_code=400)

    file_path = os.path.join(_REPORTS_DIR, f"{report_id}.html")
    if not os.path.isfile(file_path):
        return JSONResponse({"error": "Report not found"}, status_code=404)

    from starlette.responses import Response
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return Response(
        content=content,
        media_type="text/html",
        headers={
            "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'none';",
        },
    )


@app.post("/api/report/share")
async def create_share_link(request: Request):
    """Create a shareable link for a report."""
    auth_error = _require_internal_request(request)
    if auth_error:
        return auth_error
    body = await request.json()
    report_html = body.get("html", "")
    company_name = body.get("company", "")
    if not report_html:
        return JSONResponse({"error": "No HTML provided"}, status_code=400)
    if len(report_html.encode("utf-8")) > _MAX_SHARED_REPORT_BYTES:
        return JSONResponse({"error": "Report HTML too large"}, status_code=413)

    report_id = save_shared_report(report_html, company_name)
    return {"report_id": report_id, "url": f"/report/{report_id}"}


# ══════════════════════════════════════════════════════════════════
# RATE LIMITING — Simple IP-based throttle
# ══════════════════════════════════════════════════════════════════

import time as _time_mod
from collections import defaultdict as _defaultdict

_rate_limit_store: Dict = {}  # {ip: [timestamp, ...]}
_RATE_LIMIT_MAX = int(os.environ.get("MIRAI_ANALYSIS_RATE_LIMIT_MAX", "50"))
_RATE_LIMIT_WINDOW = int(os.environ.get("MIRAI_ANALYSIS_RATE_LIMIT_WINDOW", "86400"))


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, trusting Cloudflare's CF-Connecting-IP header."""
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request) -> bool:
    """Returns True if the request is within rate limits."""
    ip = _get_client_ip(request)
    now = _time_mod.time()

    if ip not in _rate_limit_store:
        _rate_limit_store[ip] = []

    # Clean old entries
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if now - t < _RATE_LIMIT_WINDOW]

    if len(_rate_limit_store[ip]) >= _RATE_LIMIT_MAX:
        return False

    _rate_limit_store[ip].append(now)
    return True


@app.get("/api/rate-limit-status")
async def rate_limit_status(request: Request):
    """Check current rate limit status for the requesting IP."""
    ip = _get_client_ip(request)
    now = _time_mod.time()
    history = [t for t in _rate_limit_store.get(ip, []) if now - t < _RATE_LIMIT_WINDOW]
    return {
        "ip": ip,
        "used": len(history),
        "limit": _RATE_LIMIT_MAX,
        "window_seconds": _RATE_LIMIT_WINDOW,
        "remaining": max(0, _RATE_LIMIT_MAX - len(history)),
    }
