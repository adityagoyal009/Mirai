"""
Mirai Analytics — tracks all platform usage silently.

Logs every event to ~/.mirai/analytics/events.jsonl
Provides summary stats on demand.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ..utils.logger import get_logger

logger = get_logger('mirofish.analytics')

_ANALYTICS_DIR = os.path.expanduser(
    os.environ.get("MIRAI_ANALYTICS_DIR", "~/.mirai/analytics")
)
_EVENTS_FILE = os.path.join(_ANALYTICS_DIR, "events.jsonl")


class Analytics:
    """Silent usage tracker for Mirai."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            os.makedirs(_ANALYTICS_DIR, exist_ok=True)
        return cls._instance

    def track(self, event: str, data: Optional[Dict[str, Any]] = None):
        """Log an event."""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **(data or {}),
        }
        try:
            with open(_EVENTS_FILE, "a") as f:
                f.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug(f"[Analytics] track failed for event '{event}': {e}")

    def track_connection(self, ip: str = ""):
        self.track("ws_connect", {"ip": ip})

    def track_analysis_start(self, company: str, industry: str, agent_count: int, source: str = "manual"):
        self.track("analysis_start", {
            "company": company, "industry": industry,
            "agent_count": agent_count, "source": source,
        })

    def track_analysis_complete(self, company: str, score: float, verdict: str,
                                 duration_s: float, agent_count: int):
        self.track("analysis_complete", {
            "company": company, "score": score, "verdict": verdict,
            "duration_s": round(duration_s, 1), "agent_count": agent_count,
        })

    def track_pdf_upload(self, filename: str, pages: int, success: bool):
        self.track("pdf_upload", {
            "filename": filename, "pages": pages, "success": success,
        })

    def track_pdf_export(self, company: str):
        self.track("pdf_export", {"company": company})

    def track_agent_chat(self, company: str, persona: str):
        self.track("agent_chat", {"company": company, "persona": persona})

    def summary(self) -> Dict[str, Any]:
        """Generate usage summary from event log."""
        if not os.path.exists(_EVENTS_FILE):
            return {"total_events": 0}

        events = []
        try:
            with open(_EVENTS_FILE) as f:
                for line in f:
                    try:
                        events.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            logger.warning(f"[Analytics] Could not read events file: {e}")
            return {"total_events": -1, "error": f"could not read events file: {e}"}

        analyses = [e for e in events if e.get("event") == "analysis_complete"]
        uploads = [e for e in events if e.get("event") == "pdf_upload"]
        exports = [e for e in events if e.get("event") == "pdf_export"]
        connections = [e for e in events if e.get("event") == "ws_connect"]
        starts = [e for e in events if e.get("event") == "analysis_start"]

        companies_analyzed = list(set(e.get("company", "") for e in analyses if e.get("company")))
        avg_score = sum(e.get("score", 0) for e in analyses) / max(len(analyses), 1)
        avg_duration = sum(e.get("duration_s", 0) for e in analyses) / max(len(analyses), 1)

        verdicts = {}
        for e in analyses:
            v = e.get("verdict", "Unknown")
            verdicts[v] = verdicts.get(v, 0) + 1

        return {
            "total_events": len(events),
            "total_connections": len(connections),
            "total_analyses_started": len(starts),
            "total_analyses_completed": len(analyses),
            "total_pdf_uploads": len(uploads),
            "total_pdf_exports": len(exports),
            "companies_analyzed": companies_analyzed,
            "avg_score": round(avg_score, 1),
            "avg_duration_s": round(avg_duration, 0),
            "verdict_distribution": verdicts,
        }


# Singleton
analytics = Analytics()
