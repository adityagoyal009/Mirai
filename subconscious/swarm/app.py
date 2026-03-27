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
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse

from .config import Config
from .utils.logger import get_logger

logger = get_logger('mirai.app')

# ── Paths ──
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DASHBOARD_DIST = os.path.join(_BASE, "dashboard", "dist")
_GAME_DIST = os.path.join(_BASE, "dashboard-game", "dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Redirect websocket.py's sync broadcast to app.py's async WebSocket broadcast.
    # websocket.py broadcast() pushes to sync queues; this bridges to async WebSocket.
    # All analysis/chat threads resolve broadcast() via module global at runtime,
    # so this single patch ensures every call reaches FastAPI WebSocket clients.
    import subconscious.swarm.api.websocket as ws_module
    ws_module.broadcast = _sync_broadcast
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


@app.post("/api/bi/analyze")
async def bi_analyze(request: Request):
    body = await request.json()
    exec_summary = body.get("exec_summary", "")
    depth = body.get("depth", "standard")
    if not exec_summary:
        return JSONResponse({"error": "Missing exec_summary"}, status_code=400)

    from .services.business_intel import BusinessIntelEngine
    bi = BusinessIntelEngine()
    result = await asyncio.to_thread(bi.analyze, exec_summary, depth)
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
    body = await request.json()
    report_html = body.get("html", "")
    company_name = body.get("company", "")
    if not report_html:
        return JSONResponse({"error": "No HTML provided"}, status_code=400)

    report_id = save_shared_report(report_html, company_name)
    return {"report_id": report_id, "url": f"/report/{report_id}"}


# ══════════════════════════════════════════════════════════════════
# RATE LIMITING — Simple IP-based throttle
# ══════════════════════════════════════════════════════════════════

import time as _time_mod
from collections import defaultdict as _defaultdict

_rate_limit_store: Dict = {}  # {ip: [timestamp, ...]}
_RATE_LIMIT_MAX = 3           # max analyses per window
_RATE_LIMIT_WINDOW = 3600     # 1 hour window


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
