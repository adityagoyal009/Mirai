"""
Mirai Portal — App factory.

Assembles FastAPI app with middleware, OAuth, routers, and static pages.
"""

from pathlib import Path

from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .db import init_db
from .auth import router as auth_router
from .portal import router as portal_router
from .admin import router as admin_router

STATIC_DIR = Path(__file__).resolve().parent.parent


def create_app() -> FastAPI:
    app = FastAPI(title="Mirai Portal", docs_url="/docs", redoc_url=None)

    # ── Middleware ────────────────────────────────────────────────
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="mirai_session",
        max_age=30 * 24 * 3600,
        same_site="lax",
        https_only=False,  # flip True behind HTTPS in prod
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── OAuth (attached to app.state so routers can access it) ───
    oauth = OAuth()
    if settings.google_configured:
        oauth.register(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    app.state.oauth = oauth
    app.state.settings = settings

    # ── Startup ──────────────────────────────────────────────────
    @app.on_event("startup")
    async def on_startup():
        await init_db()

    # ── Error handling ───────────────────────────────────────────
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
        )

    # ── Routers ──────────────────────────────────────────────────
    app.include_router(auth_router)
    app.include_router(portal_router, prefix="/api/portal")
    app.include_router(admin_router, prefix="/api/admin")

    # ── Static pages ─────────────────────────────────────────────
    @app.get("/")
    async def root():
        return RedirectResponse("/landing/")

    @app.get("/landing/")
    async def landing():
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    @app.get("/signin/")
    async def signin():
        return FileResponse(STATIC_DIR / "signin.html", media_type="text/html")

    @app.get("/admin/")
    async def admin_page():
        return FileResponse(STATIC_DIR / "admin.html", media_type="text/html")

    return app
