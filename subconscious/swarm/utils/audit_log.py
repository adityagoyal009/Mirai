"""
Audit Log — captures every LLM call and pipeline step for post-run analysis.

Stores raw prompts, raw responses, parsed outputs, latencies, and model metadata
so you can compare how different models behave and tune prompts.

Usage:
    from ..utils.audit_log import audit

    audit.start_run("Acme Corp", "fintech", agent_count=25)
    audit.log_step("extraction", model="claude-opus-4-6", prompt=p, raw_response=r, parsed=d, latency_s=4.2)
    audit.log_council_vote("Claude Opus 4.6", model="claude-opus-4-6", prompt=p, raw_response=r, scores={...}, latency_s=12.0)
    ...
    audit.end_run(verdict="Likely Hit", score=7.2)
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

_audit_logger = logging.getLogger('mirofish.audit_log')


_AUDIT_DIR = os.path.expanduser("~/.mirai/audits")


class AuditLog:
    """Thread-safe audit logger. One instance per pipeline run."""

    _current: Optional["AuditLog"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._steps: List[Dict] = []
        self._council_votes: List[Dict] = []
        self._research_calls: List[Dict] = []
        self._swarm_agents: List[Dict] = []
        self._report_steps: List[Dict] = []
        self._start_time = time.time()
        self._step_lock = threading.Lock()

    @classmethod
    def start_run(cls, company: str, industry: str, agent_count: int = 0,
                  council_models: List[str] = None, swarm_models: List[str] = None) -> "AuditLog":
        """Start a new audit run. Returns the active AuditLog."""
        instance = cls()
        instance._data = {
            "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "started_at": datetime.now().isoformat(),
            "company": company,
            "industry": industry,
            "agent_count": agent_count,
            "council_models": council_models or [],
            "swarm_models": swarm_models or [],
            "pipeline_config": {
                "depth": "deep",
            },
        }
        with cls._lock:
            cls._current = instance
        return instance

    @classmethod
    def get(cls) -> Optional["AuditLog"]:
        """Get the current active audit log."""
        return cls._current

    def log_step(self, phase: str, *, model: str = "", prompt: str = "",
                 raw_response: str = "", parsed: Any = None,
                 latency_s: float = 0, success: bool = True, error: str = "",
                 metadata: Dict = None):
        """Log a generic pipeline step."""
        entry = {
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "prompt_chars": len(prompt),
            "prompt_preview": prompt[:500],
            "raw_response_chars": len(raw_response),
            "raw_response_preview": raw_response[:1000],
            "parsed": _safe_serialize(parsed),
            "latency_s": round(latency_s, 2),
            "success": success,
            "error": error,
        }
        if metadata:
            entry["metadata"] = metadata
        with self._step_lock:
            self._steps.append(entry)

    def log_research(self, researcher: str, *, model: str, prompt: str,
                     raw_response: str = "", parsed: Any = None,
                     latency_s: float = 0, success: bool = True, error: str = "",
                     facts_count: int = 0, competitors_count: int = 0, sources_count: int = 0):
        """Log a research model call."""
        entry = {
            "researcher": researcher,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "prompt_chars": len(prompt),
            "raw_response_chars": len(raw_response),
            "raw_response_preview": raw_response[:2000],
            "latency_s": round(latency_s, 2),
            "success": success,
            "error": error,
            "facts_count": facts_count,
            "competitors_count": competitors_count,
            "sources_count": sources_count,
            "parsed_keys": list(parsed.keys()) if isinstance(parsed, dict) else [],
        }
        with self._step_lock:
            self._research_calls.append(entry)

    def log_council_vote(self, label: str, *, model: str, prompt: str,
                         raw_response: str = "", scores: Dict = None,
                         reasoning: str = "", confidence: float = 0,
                         latency_s: float = 0, success: bool = True, error: str = ""):
        """Log a single council model's vote with full detail."""
        entry = {
            "label": label,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "prompt_chars": len(prompt),
            "prompt_preview": prompt[:500],
            "raw_response_chars": len(raw_response),
            "raw_response_preview": raw_response[:2000],
            "scores": scores or {},
            "reasoning_preview": reasoning[:500],
            "confidence": confidence,
            "latency_s": round(latency_s, 2),
            "success": success,
            "error": error,
        }
        with self._step_lock:
            self._council_votes.append(entry)

    def log_council_reconciliation(self, *, reconciled_scores: Dict = None,
                                   contested: List = None, chairman_notes: str = "",
                                   model_scores: Dict = None):
        """Log the council reconciliation/chairman step."""
        self._data["council_reconciliation"] = {
            "timestamp": datetime.now().isoformat(),
            "reconciled_scores": reconciled_scores or {},
            "contested_dimensions": contested or [],
            "chairman_notes": chairman_notes[:1000],
            "per_model_scores": model_scores or {},
        }

    def log_swarm_agent(self, agent_id: int, *, persona: str, zone: str,
                        model: str, vote: str, overall: float, scores: Dict = None,
                        reasoning: str = "", confidence: float = 0,
                        latency_s: float = 0, success: bool = True):
        """Log a single swarm agent's vote."""
        entry = {
            "agent_id": agent_id,
            "persona": persona,
            "zone": zone,
            "model": model,
            "vote": vote,
            "overall": overall,
            "scores": scores or {},
            "reasoning_preview": reasoning[:300],
            "confidence": confidence,
            "latency_s": round(latency_s, 2),
            "success": success,
        }
        with self._step_lock:
            self._swarm_agents.append(entry)

    def log_verdict_blend(self, *, council_verdict: str, council_confidence: float,
                          swarm_verdict: str, swarm_confidence: float,
                          blended_score: float, final_verdict: str, final_confidence: float):
        """Log the verdict blending calculation."""
        self._data["verdict_blend"] = {
            "council_verdict": council_verdict,
            "council_confidence": council_confidence,
            "swarm_verdict": swarm_verdict,
            "swarm_confidence": swarm_confidence,
            "blended_score": blended_score,
            "final_verdict": final_verdict,
            "final_confidence": final_confidence,
        }

    def log_report(self, step: str, *, model: str = "", prompt_chars: int = 0,
                   response_chars: int = 0, latency_s: float = 0,
                   success: bool = True, error: str = ""):
        """Log a report generation step."""
        entry = {
            "step": step,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "prompt_chars": prompt_chars,
            "response_chars": response_chars,
            "latency_s": round(latency_s, 2),
            "success": success,
            "error": error,
        }
        with self._step_lock:
            self._report_steps.append(entry)

    def end_run(self, *, verdict: str = "", score: float = 0, confidence: float = 0):
        """Finalize and write the audit log to disk."""
        elapsed = time.time() - self._start_time
        self._data["ended_at"] = datetime.now().isoformat()
        self._data["total_duration_s"] = round(elapsed, 1)
        self._data["final_verdict"] = verdict
        self._data["final_score"] = score
        self._data["final_confidence"] = confidence

        # Assemble full audit
        self._data["steps"] = self._steps
        self._data["research"] = self._research_calls
        self._data["council_votes"] = self._council_votes
        self._data["swarm_agents"] = self._swarm_agents
        self._data["report_generation"] = self._report_steps

        # Summary stats
        self._data["summary"] = {
            "total_llm_calls": len(self._steps) + len(self._research_calls) + len(self._council_votes) + len(self._swarm_agents) + len(self._report_steps),
            "council_models_succeeded": [v["label"] for v in self._council_votes if v["success"]],
            "council_models_failed": [v["label"] for v in self._council_votes if not v["success"]],
            "swarm_agents_succeeded": sum(1 for a in self._swarm_agents if a["success"]),
            "swarm_agents_failed": sum(1 for a in self._swarm_agents if not a["success"]),
            "research_succeeded": sum(1 for r in self._research_calls if r["success"]),
            "research_failed": sum(1 for r in self._research_calls if not r["success"]),
        }

        # Write to disk
        os.makedirs(_AUDIT_DIR, exist_ok=True)
        company = self._data.get("company", "unknown")
        safe = ''.join(c if c.isalnum() or c in '-_ ' else '' for c in company).strip().replace(' ', '-').lower()
        filename = f"{self._data['run_id']}_{safe}.json"
        path = os.path.join(_AUDIT_DIR, filename)

        try:
            with open(path, 'w') as f:
                json.dump(self._data, f, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            _audit_logger.error(
                f"[Audit] Failed to write audit log to {path}: {e}. "
                "All diagnostic data for this run is lost."
            )

        return path


def _safe_serialize(obj: Any) -> Any:
    """Safely serialize an object for JSON storage."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        # Truncate large values
        result = {}
        for k, v in obj.items():
            if isinstance(v, str) and len(v) > 2000:
                result[k] = v[:2000] + "...[truncated]"
            elif isinstance(v, list) and len(v) > 50:
                result[k] = v[:50]
            else:
                result[k] = v
        return result
    if isinstance(obj, list):
        return obj[:50] if len(obj) > 50 else obj
    try:
        return str(obj)[:500]
    except Exception:
        return "<unserializable>"
