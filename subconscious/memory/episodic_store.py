"""
EpisodicMemoryStore — ChromaDB-backed episodic memory for Mirai.

Provides persistent semantic search, node/edge graph storage, and episode
management. Replaces the Zep Cloud dependency with a fully local solution.
"""

import os
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

import chromadb

logger = logging.getLogger("mirai.memory")

# Default persistence path (relative to this file)
_DEFAULT_PERSIST_PATH = os.path.join(os.path.dirname(__file__), ".chromadb_data")


@dataclass
class MemoryNode:
    """A node in the knowledge graph."""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryEdge:
    """An edge (relationship) in the knowledge graph."""
    uuid: str
    name: str
    fact: str
    source_node_uuid: str
    target_node_uuid: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EpisodicMemoryStore:
    """
    Persistent episodic memory backed by ChromaDB.

    Each graph has three collections:
      - {graph_id}_episodes  — raw text episodes (for semantic search)
      - {graph_id}_nodes     — entity nodes
      - {graph_id}_edges     — relationship edges

    Uses ChromaDB's built-in sentence-transformer embeddings for semantic search.
    """

    def __init__(self, persist_path: Optional[str] = None):
        self.persist_path = persist_path or _DEFAULT_PERSIST_PATH
        os.makedirs(self.persist_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_path)
        logger.info(f"EpisodicMemoryStore initialized at {self.persist_path}")

    # ── Graph lifecycle ──────────────────────────────────────────

    def create_graph(self, graph_name: str) -> str:
        """Create a new graph and return its ID."""
        graph_id = f"mirofish_{uuid.uuid4().hex[:16]}"
        # Create the three collections
        self.client.get_or_create_collection(
            name=f"{graph_id}_episodes",
            metadata={"graph_name": graph_name, "type": "episodes"},
        )
        self.client.get_or_create_collection(
            name=f"{graph_id}_nodes",
            metadata={"graph_name": graph_name, "type": "nodes"},
        )
        self.client.get_or_create_collection(
            name=f"{graph_id}_edges",
            metadata={"graph_name": graph_name, "type": "edges"},
        )
        logger.info(f"Created graph '{graph_name}' with id={graph_id}")
        return graph_id

    def delete_graph(self, graph_id: str):
        """Delete a graph and all its collections."""
        for suffix in ("_episodes", "_nodes", "_edges"):
            try:
                self.client.delete_collection(f"{graph_id}{suffix}")
            except Exception:
                pass
        logger.info(f"Deleted graph {graph_id}")

    # ── Episodes (raw text for semantic search) ──────────────────

    def add_episodes(
        self,
        graph_id: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add text episodes to the graph. Returns the list of IDs."""
        collection = self.client.get_or_create_collection(f"{graph_id}_episodes")
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        if metadatas is None:
            metadatas = [{"type": "episode"} for _ in documents]
        # Ensure metadata values are ChromaDB-safe (str, int, float, bool)
        safe_metadatas = [self._sanitize_metadata(m) for m in metadatas]
        collection.add(documents=documents, metadatas=safe_metadatas, ids=ids)
        return ids

    def search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
        collection_suffix: str = "_episodes",
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across a graph collection.
        Returns list of {id, document, metadata, distance}.
        """
        col_name = f"{graph_id}{collection_suffix}"
        try:
            collection = self.client.get_collection(col_name)
        except Exception:
            return []

        count = collection.count()
        if count == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(limit, count),
        )

        items = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            ids = results["ids"][0]
            distances = results["distances"][0] if results.get("distances") else [0] * len(docs)
            metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            for i, doc in enumerate(docs):
                items.append({
                    "id": ids[i],
                    "document": doc,
                    "metadata": metadatas[i],
                    "distance": distances[i],
                })
        return items

    # ── Nodes ────────────────────────────────────────────────────

    def add_nodes(self, graph_id: str, nodes: List[MemoryNode]) -> List[str]:
        """Add entity nodes to the graph."""
        if not nodes:
            return []
        collection = self.client.get_or_create_collection(f"{graph_id}_nodes")
        ids = [n.uuid for n in nodes]
        documents = [f"{n.name}: {n.summary}" for n in nodes]
        metadatas = [
            self._sanitize_metadata({
                "name": n.name,
                "labels": json.dumps(n.labels),
                "summary": n.summary,
                "attributes": json.dumps(n.attributes),
                "created_at": n.created_at or "",
            })
            for n in nodes
        ]
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        return ids

    def get_all_nodes(self, graph_id: str) -> List[MemoryNode]:
        """Retrieve all nodes from a graph."""
        try:
            collection = self.client.get_collection(f"{graph_id}_nodes")
        except Exception:
            return []

        data = collection.get()
        if not data or not data.get("ids"):
            return []

        nodes = []
        for i, node_id in enumerate(data["ids"]):
            meta = data["metadatas"][i] if data.get("metadatas") else {}
            nodes.append(MemoryNode(
                uuid=node_id,
                name=meta.get("name", ""),
                labels=json.loads(meta.get("labels", "[]")),
                summary=meta.get("summary", ""),
                attributes=json.loads(meta.get("attributes", "{}")),
                created_at=meta.get("created_at"),
            ))
        return nodes

    def get_node(self, graph_id: str, node_uuid: str) -> Optional[MemoryNode]:
        """Retrieve a single node by UUID."""
        try:
            collection = self.client.get_collection(f"{graph_id}_nodes")
        except Exception:
            return None

        data = collection.get(ids=[node_uuid])
        if not data or not data.get("ids"):
            return None

        meta = data["metadatas"][0] if data.get("metadatas") else {}
        return MemoryNode(
            uuid=node_uuid,
            name=meta.get("name", ""),
            labels=json.loads(meta.get("labels", "[]")),
            summary=meta.get("summary", ""),
            attributes=json.loads(meta.get("attributes", "{}")),
            created_at=meta.get("created_at"),
        )

    def get_node_count(self, graph_id: str) -> int:
        """Get the number of nodes in a graph."""
        try:
            collection = self.client.get_collection(f"{graph_id}_nodes")
            return collection.count()
        except Exception:
            return 0

    # ── Edges ────────────────────────────────────────────────────

    def add_edges(self, graph_id: str, edges: List[MemoryEdge]) -> List[str]:
        """Add relationship edges to the graph."""
        if not edges:
            return []
        collection = self.client.get_or_create_collection(f"{graph_id}_edges")
        ids = [e.uuid for e in edges]
        documents = [f"{e.name}: {e.fact}" for e in edges]
        metadatas = [
            self._sanitize_metadata({
                "name": e.name,
                "fact": e.fact,
                "source_node_uuid": e.source_node_uuid,
                "target_node_uuid": e.target_node_uuid,
                "attributes": json.dumps(e.attributes),
                "created_at": e.created_at or "",
                "valid_at": e.valid_at or "",
                "invalid_at": e.invalid_at or "",
                "expired_at": e.expired_at or "",
            })
            for e in edges
        ]
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        return ids

    def get_all_edges(self, graph_id: str) -> List[MemoryEdge]:
        """Retrieve all edges from a graph."""
        try:
            collection = self.client.get_collection(f"{graph_id}_edges")
        except Exception:
            return []

        data = collection.get()
        if not data or not data.get("ids"):
            return []

        edges = []
        for i, edge_id in enumerate(data["ids"]):
            meta = data["metadatas"][i] if data.get("metadatas") else {}
            edges.append(MemoryEdge(
                uuid=edge_id,
                name=meta.get("name", ""),
                fact=meta.get("fact", ""),
                source_node_uuid=meta.get("source_node_uuid", ""),
                target_node_uuid=meta.get("target_node_uuid", ""),
                attributes=json.loads(meta.get("attributes", "{}")),
                created_at=meta.get("created_at") or None,
                valid_at=meta.get("valid_at") or None,
                invalid_at=meta.get("invalid_at") or None,
                expired_at=meta.get("expired_at") or None,
            ))
        return edges

    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[MemoryEdge]:
        """Get all edges connected to a specific node."""
        all_edges = self.get_all_edges(graph_id)
        return [
            e for e in all_edges
            if e.source_node_uuid == node_uuid or e.target_node_uuid == node_uuid
        ]

    def get_edge_count(self, graph_id: str) -> int:
        """Get the number of edges in a graph."""
        try:
            collection = self.client.get_collection(f"{graph_id}_edges")
            return collection.count()
        except Exception:
            return 0

    # ── Episode count ────────────────────────────────────────────

    def get_episode_count(self, graph_id: str) -> int:
        """Get the number of episodes in a graph."""
        try:
            collection = self.client.get_collection(f"{graph_id}_episodes")
            return collection.count()
        except Exception:
            return 0

    # ── Utilities ────────────────────────────────────────────────

    @staticmethod
    def _sanitize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure metadata values are ChromaDB-safe types."""
        safe = {}
        for k, v in meta.items():
            if v is None:
                safe[k] = ""
            elif isinstance(v, (str, int, float, bool)):
                safe[k] = v
            else:
                safe[k] = json.dumps(v)
        return safe
