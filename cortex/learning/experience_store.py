"""
Experience Store — stores (situation, action, outcome) tuples in ChromaDB.

Every cortex cycle logs what happened so Mirai can recall similar past
experiences before deciding its next action.
"""

import os
import sys
import uuid
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from subconscious.memory import EpisodicMemoryStore

_GRAPH_ID = "mirai_experiences"
_store: Optional[EpisodicMemoryStore] = None


def _get_store() -> EpisodicMemoryStore:
    global _store
    if _store is None:
        persist = os.environ.get(
            "CHROMADB_PERSIST_PATH",
            os.path.join(os.path.dirname(__file__), '..', '..', 'subconscious', 'memory', '.chromadb_data'),
        )
        _store = EpisodicMemoryStore(persist_path=persist)
        # Ensure the experiences graph exists
        try:
            _store.client.get_collection(f"{_GRAPH_ID}_episodes")
        except Exception:
            _store.create_graph("Mirai Experiences")
            # Rename — create_graph returns a random id. We need the fixed one.
            # Simpler: just ensure the collection exists directly.
            pass
        _store.client.get_or_create_collection(
            name=f"{_GRAPH_ID}_episodes",
            metadata={"type": "experiences"},
        )
    return _store


@dataclass
class Experience:
    """A single recorded experience."""
    id: str
    situation: str
    action: str
    action_type: str
    outcome: str
    success: bool
    score: float
    lesson: str = ""
    timestamp: str = ""
    cycle_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_metadata(cls, meta: Dict[str, Any], doc: str = "") -> "Experience":
        return cls(
            id=meta.get("id", ""),
            situation=meta.get("situation", ""),
            action=meta.get("action", ""),
            action_type=meta.get("action_type", ""),
            outcome=meta.get("outcome", doc),
            success=meta.get("success", "true") == "true",
            score=float(meta.get("score", 0.0)),
            lesson=meta.get("lesson", ""),
            timestamp=meta.get("timestamp", ""),
            cycle_number=int(meta.get("cycle_number", 0)),
        )


class ExperienceStore:
    """Persistent experience memory backed by ChromaDB."""

    def __init__(self):
        self._store = _get_store()

    def store_experience(
        self,
        situation: str,
        action: str,
        action_type: str,
        outcome: str,
        success: bool,
        score: float = 0.0,
        lesson: str = "",
        cycle_number: int = 0,
    ) -> str:
        """Store a new experience. Returns the experience ID."""
        exp_id = f"exp_{uuid.uuid4().hex[:16]}"
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Document text for semantic search
        doc = (
            f"Situation: {situation}\n"
            f"Action ({action_type}): {action}\n"
            f"Outcome: {outcome}\n"
            f"Success: {success}"
        )

        meta = {
            "id": exp_id,
            "situation": situation[:500],
            "action": action[:500],
            "action_type": action_type,
            "outcome": outcome[:500],
            "success": str(success).lower(),  # ChromaDB needs str
            "score": float(score),
            "lesson": lesson[:300],
            "timestamp": ts,
            "cycle_number": int(cycle_number),
        }

        col = self._store.client.get_or_create_collection(f"{_GRAPH_ID}_episodes")
        col.add(
            documents=[doc],
            metadatas=[meta],
            ids=[exp_id],
        )
        return exp_id

    def recall_similar(self, situation: str, limit: int = 5) -> List[Experience]:
        """Semantic search for experiences similar to a given situation."""
        col = self._store.client.get_or_create_collection(f"{_GRAPH_ID}_episodes")
        if col.count() == 0:
            return []

        results = col.query(
            query_texts=[situation],
            n_results=min(limit, col.count()),
        )

        experiences = []
        if results and results.get("ids"):
            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else [""] * len(ids)
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
            for i, eid in enumerate(ids):
                exp = Experience.from_metadata(metas[i], docs[i])
                exp.id = eid
                experiences.append(exp)
        return experiences

    def get_recent(self, n: int = 20) -> List[Experience]:
        """Get the most recent N experiences (by cycle_number descending)."""
        col = self._store.client.get_or_create_collection(f"{_GRAPH_ID}_episodes")
        if col.count() == 0:
            return []

        data = col.get(limit=min(n * 3, col.count()))  # overfetch to sort
        if not data or not data.get("ids"):
            return []

        experiences = []
        for i, eid in enumerate(data["ids"]):
            meta = data["metadatas"][i] if data.get("metadatas") else {}
            doc = data["documents"][i] if data.get("documents") else ""
            exp = Experience.from_metadata(meta, doc)
            exp.id = eid
            experiences.append(exp)

        # Sort by cycle_number descending, take top N
        experiences.sort(key=lambda e: e.cycle_number, reverse=True)
        return experiences[:n]

    def get_failure_patterns(self, limit: int = 20) -> List[Experience]:
        """Get recent failed experiences."""
        col = self._store.client.get_or_create_collection(f"{_GRAPH_ID}_episodes")
        if col.count() == 0:
            return []

        try:
            data = col.get(where={"success": "false"}, limit=limit)
        except Exception:
            # Fallback if where filter fails
            data = col.get(limit=limit * 2)

        if not data or not data.get("ids"):
            return []

        experiences = []
        for i, eid in enumerate(data["ids"]):
            meta = data["metadatas"][i] if data.get("metadatas") else {}
            doc = data["documents"][i] if data.get("documents") else ""
            exp = Experience.from_metadata(meta, doc)
            exp.id = eid
            if not exp.success:
                experiences.append(exp)

        experiences.sort(key=lambda e: e.cycle_number, reverse=True)
        return experiences[:limit]

    def get_count(self) -> int:
        """Total number of stored experiences."""
        col = self._store.client.get_or_create_collection(f"{_GRAPH_ID}_episodes")
        return col.count()
