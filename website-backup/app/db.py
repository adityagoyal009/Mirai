"""
Mirai Portal — Database layer.

Async SQLAlchemy with SQLite (aiosqlite).
Three tables: users, submissions, events.
"""

import os
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "mirai_portal.db",
)
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DB_URL, echo=False)
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)


def utcnow() -> str:
    """ISO 8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


# ── ORM Base ─────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(Text, unique=True, nullable=False, index=True)
    name = Column(Text, default="")
    picture = Column(Text, default="")
    is_admin = Column(Boolean, default=False)
    created_at = Column(Text, default=utcnow)
    updated_at = Column(Text, default=utcnow, onupdate=utcnow)

    submissions = relationship("Submission", back_populates="user", lazy="selectin")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_name = Column(Text, nullable=False)
    website_url = Column(Text, default="")
    industry = Column(Text, default="", index=True)
    stage = Column(Text, default="", index=True)
    one_liner = Column(Text, default="")
    customers = Column(Text, default="")
    business_model = Column(Text, default="")
    traction = Column(Text, default="")
    deck_url = Column(Text, default="")
    advantage = Column(Text, default="")
    risk = Column(Text, default="")
    status = Column(Text, default="queued", index=True)
    admin_notes = Column(Text, default="")
    created_at = Column(Text, default=utcnow, index=True)
    updated_at = Column(Text, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="submissions", lazy="selectin")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event = Column(Text, nullable=False)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    meta = Column(Text, default="{}")
    created_at = Column(Text, default=utcnow, index=True)


# ── DB lifecycle ─────────────────────────────────────────────────

VALID_STATUSES = {"queued", "reviewing", "report_sent", "archived"}


async def init_db():
    """Create tables if they don't exist. Idempotent."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency — yields an AsyncSession, auto-commits on success."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
