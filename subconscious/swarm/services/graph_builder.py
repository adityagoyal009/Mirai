"""
Graph Building Service
API 2: Build local knowledge graph using ChromaDB (replaces Zep Cloud)
"""

import os
import uuid
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from ..config import Config
from ..models.task import TaskManager, TaskStatus
from .text_processor import TextProcessor

# Lazy import to avoid circular dependency
_memory_store = None


def _get_memory_store():
    """Get or create the shared EpisodicMemoryStore instance."""
    global _memory_store
    if _memory_store is None:
        from subconscious.memory import EpisodicMemoryStore
        _memory_store = EpisodicMemoryStore(persist_path=Config.CHROMADB_PERSIST_PATH)
    return _memory_store


@dataclass
class GraphInfo:
    """Graph Info"""
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


class GraphBuilderService:
    """
    Graph Building Service
    Build local knowledge graph using ChromaDB
    """

    def __init__(self, store=None):
        self.store = store or _get_memory_store()
        self.task_manager = TaskManager()

    def build_graph_async(
        self,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str = "MiroFish Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 3
    ) -> str:
        """
        Build graph asynchronously

        Args:
            text: Input text
            ontology: Ontology definition (output from API 1)
            graph_name: Graph name
            chunk_size: Text chunk size
            chunk_overlap: Chunk overlap size
            batch_size: Number of chunks per batch

        Returns:
            Task ID
        """
        # # Create task
        task_id = self.task_manager.create_task(
            task_type="graph_build",
            metadata={
                "graph_name": graph_name,
                "chunk_size": chunk_size,
                "text_length": len(text),
            }
        )

        # # Execute build in background thread
        thread = threading.Thread(
            target=self._build_graph_worker,
            args=(task_id, text, ontology, graph_name, chunk_size, chunk_overlap, batch_size)
        )
        thread.daemon = True
        thread.start()

        return task_id

    def _build_graph_worker(
        self,
        task_id: str,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str,
        chunk_size: int,
        chunk_overlap: int,
        batch_size: int
    ):
        """Graph building worker thread"""
        try:
            self.task_manager.update_task(
                task_id,
                status=TaskStatus.PROCESSING,
                progress=5,
                message="Starting graph build..."
            )

            # 1. Create graph
            graph_id = self.create_graph(graph_name)
            self.task_manager.update_task(
                task_id,
                progress=10,
                message=f"Graph created: {graph_id}"
            )

            # 2. Set ontology (stored as metadata)
            self.set_ontology(graph_id, ontology)
            self.task_manager.update_task(
                task_id,
                progress=15,
                message="Ontology set"
            )

            # 3. Text chunking
            chunks = TextProcessor.split_text(text, chunk_size, chunk_overlap)
            total_chunks = len(chunks)
            self.task_manager.update_task(
                task_id,
                progress=20,
                message=f"Text split into {total_chunks}  chunks"
            )

            # 4. Add text to graph in batches
            episode_uuids = self.add_text_batches(
                graph_id, chunks, batch_size,
                lambda msg, prog: self.task_manager.update_task(
                    task_id,
                    progress=20 + int(prog * 0.4),  # 20-60%
                    message=msg
                )
            )

            # 5. Processing complete (local ChromaDB is immediate)
            self.task_manager.update_task(
                task_id,
                progress=60,
                message="Processing data..."
            )

            self._wait_for_episodes(
                episode_uuids,
                lambda msg, prog: self.task_manager.update_task(
                    task_id,
                    progress=60 + int(prog * 0.3),  # 60-90%
                    message=msg
                )
            )

            # 6. Get graph info
            self.task_manager.update_task(
                task_id,
                progress=90,
                message="Getting graph info..."
            )

            graph_info = self._get_graph_info(graph_id)

            # Complete
            self.task_manager.complete_task(task_id, {
                "graph_id": graph_id,
                "graph_info": graph_info.to_dict(),
                "chunks_processed": total_chunks,
            })

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.task_manager.fail_task(task_id, error_msg)

    def create_graph(self, name: str) -> str:
        """Create graph (public method)"""
        return self.store.create_graph(name)

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """Set graph ontology (stored as metadata)"""
        # Store ontology as a special episode for future reference
        if ontology:
            import json
            self.store.add_episodes(
                graph_id,
                documents=[json.dumps(ontology, ensure_ascii=False)],
                metadatas=[{"type": "ontology"}],
            )

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """Add text to graph in batches, return list of all episode UUIDs"""
        all_uuids = []
        total_chunks = len(chunks)

        for i in range(0, total_chunks, batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size

            if progress_callback:
                progress = (i + len(batch_chunks)) / total_chunks
                progress_callback(
                    f"Sending batch  {batch_num}/{total_batches} data ({len(batch_chunks)}  chunks)...",
                    progress
                )

            try:
                batch_uuids = self.store.add_episodes(
                    graph_id,
                    documents=batch_chunks,
                    metadatas=[{"type": "text"} for _ in batch_chunks],
                )
                all_uuids.extend(batch_uuids)

                # Small delay to avoid overwhelming I/O
                time.sleep(0.1)

            except Exception as e:
                if progress_callback:
                    progress_callback(f"Batch  {batch_num} send failed: {str(e)}", 0)
                raise

        return all_uuids

    def _wait_for_episodes(
        self,
        episode_uuids: List[str],
        progress_callback: Optional[Callable] = None,
        timeout: int = 600
    ):
        """ChromaDB is synchronous — episodes are ready immediately."""
        if progress_callback:
            progress_callback("Processing complete", 1.0)

    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        """Get graph info"""
        node_count = self.store.get_episode_count(graph_id)
        edge_count = self.store.get_edge_count(graph_id)

        return GraphInfo(
            graph_id=graph_id,
            node_count=node_count,
            edge_count=edge_count,
            entity_types=["document"]
        )

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """Get complete graph data (with detailed info)"""
        # Get episodes as pseudo-nodes for display
        try:
            col = self.store.client.get_collection(f"{graph_id}_episodes")
            docs = col.get()
        except Exception:
            docs = {"ids": [], "documents": [], "metadatas": []}

        nodes_data = []
        if docs and docs.get('documents'):
            for i, doc in enumerate(docs['documents']):
                doc_id = docs['ids'][i]
                nodes_data.append({
                    "uuid": doc_id,
                    "name": f"Document {doc_id[:8]}",
                    "labels": ["document"],
                    "summary": doc[:100],
                    "attributes": {"text": doc},
                    "created_at": None,
                })

        # Also include real graph nodes
        real_nodes = self.store.get_all_nodes(graph_id)
        for node in real_nodes:
            nodes_data.append(node.to_dict())

        # Get edges
        real_edges = self.store.get_all_edges(graph_id)
        edges_data = [e.to_dict() for e in real_edges]

        return {
            "graph_id": graph_id,
            "nodes": nodes_data,
            "edges": edges_data,
            "node_count": len(nodes_data),
            "edge_count": len(edges_data),
        }

    def delete_graph(self, graph_id: str):
        """Delete graph"""
        self.store.delete_graph(graph_id)
