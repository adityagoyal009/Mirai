"""
Market Radar — scheduled monitoring of external signals.

Maintains a persistent watch list. On each check cycle, queries ChromaDB
for relevant data or flags items for browser-based fetching.
"""

import os
import sys
import json
import time
import uuid
from dataclasses import dataclass, asdict
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


@dataclass
class MarketWatch:
    """A single monitored topic."""
    id: str
    query: str
    interval_seconds: int  # how often to check
    source: str            # "chromadb" or "browser"
    last_checked: float    # epoch timestamp

    def is_due(self) -> bool:
        return time.time() - self.last_checked >= self.interval_seconds


@dataclass
class MarketSignal:
    """A detected signal from a watch."""
    query: str
    findings: str
    timestamp: str
    source: str
    relevance_score: float


class MarketRadar:
    """Scheduled market/data monitoring with persistent watch list."""

    def __init__(self):
        self.watches_path = os.environ.get(
            "MIRAI_WATCHES_PATH",
            os.path.expanduser("~/.mirai/watches.json"),
        )
        self._check_interval = int(os.environ.get("MARKET_RADAR_INTERVAL", "30"))
        self.watches: List[MarketWatch] = self._load_watches()

    def should_check(self, cycle_number: int) -> bool:
        return cycle_number > 0 and cycle_number % self._check_interval == 0

    # ── Watch management ─────────────────────────────────────────

    def add_watch(
        self,
        query: str,
        interval_seconds: int = 3600,
        source: str = "chromadb",
    ) -> str:
        """Add a new topic to monitor. Returns watch ID."""
        watch_id = f"watch_{uuid.uuid4().hex[:12]}"
        watch = MarketWatch(
            id=watch_id,
            query=query,
            interval_seconds=interval_seconds,
            source=source,
            last_checked=0.0,  # check immediately on first pass
        )
        self.watches.append(watch)
        self._save_watches()
        print(f"[RADAR] Added watch: {query} (every {interval_seconds}s via {source})")
        return watch_id

    def remove_watch(self, watch_id: str) -> bool:
        """Remove a watch by ID."""
        before = len(self.watches)
        self.watches = [w for w in self.watches if w.id != watch_id]
        if len(self.watches) < before:
            self._save_watches()
            return True
        return False

    # ── Checking ─────────────────────────────────────────────────

    def check_all(self) -> List[MarketSignal]:
        """Check all due watches and return signals."""
        signals = []
        any_updated = False

        for watch in self.watches:
            if not watch.is_due():
                continue

            signal = self._check_single(watch)
            if signal:
                signals.append(signal)

            watch.last_checked = time.time()
            any_updated = True

        if any_updated:
            self._save_watches()

        if signals:
            print(f"[RADAR] {len(signals)} market signals detected")

        return signals

    def _check_single(self, watch: MarketWatch) -> Optional[MarketSignal]:
        """Check a single watch. Returns a signal if findings exist."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if watch.source == "chromadb":
            return self._check_chromadb(watch, ts)
        elif watch.source == "browser":
            # Flag for the cortex to handle via browser_navigate
            return MarketSignal(
                query=watch.query,
                findings="FETCH_NEEDED",
                timestamp=ts,
                source="browser",
                relevance_score=0.5,
            )
        return None

    def _check_chromadb(self, watch: MarketWatch, ts: str) -> Optional[MarketSignal]:
        """Search ChromaDB for relevant information."""
        try:
            from subconscious.memory import EpisodicMemoryStore

            persist = os.environ.get(
                "CHROMADB_PERSIST_PATH",
                os.path.join(os.path.dirname(__file__), '..', '..', 'subconscious', 'memory', '.chromadb_data'),
            )
            store = EpisodicMemoryStore(persist_path=persist)

            # Search across all known graphs for the watch query
            results = []
            for col in store.client.list_collections():
                col_name = col.name if hasattr(col, 'name') else str(col)
                if col_name.endswith("_episodes"):
                    graph_id = col_name.replace("_episodes", "")
                    hits = store.search(graph_id, watch.query, limit=3)
                    results.extend(hits)

            if results:
                findings = "; ".join(
                    r.get("document", "")[:100] for r in results[:5]
                )
                return MarketSignal(
                    query=watch.query,
                    findings=findings,
                    timestamp=ts,
                    source="chromadb",
                    relevance_score=1.0 - (results[0].get("distance", 1.0) if results else 1.0),
                )
        except Exception as e:
            print(f"[RADAR] ChromaDB check failed for '{watch.query}': {e}")

        return None

    # ── Persistence ──────────────────────────────────────────────

    def _load_watches(self) -> List[MarketWatch]:
        try:
            with open(self.watches_path, "r") as f:
                data = json.load(f)
            return [
                MarketWatch(
                    id=w["id"],
                    query=w["query"],
                    interval_seconds=w["interval_seconds"],
                    source=w["source"],
                    last_checked=w.get("last_checked", 0.0),
                )
                for w in data
            ]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_watches(self):
        os.makedirs(os.path.dirname(self.watches_path), exist_ok=True)
        with open(self.watches_path, "w") as f:
            json.dump([asdict(w) for w in self.watches], f, indent=2)
