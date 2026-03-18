"""Graph paging utilities — delegates to EpisodicMemoryStore.

Replaces the original Zep Cloud pagination with local ChromaDB reads.
The function signatures are kept compatible so callers need minimal changes.
"""

from __future__ import annotations

from typing import Any, List

from .logger import get_logger

logger = get_logger('mirofish.zep_paging')


def fetch_all_nodes(
    store,
    graph_id: str,
    **_kwargs: Any,
) -> List[Any]:
    """Fetch all nodes from a graph via EpisodicMemoryStore."""
    nodes = store.get_all_nodes(graph_id)
    logger.info(f"Fetched {len(nodes)} nodes from graph {graph_id}")
    return nodes


def fetch_all_edges(
    store,
    graph_id: str,
    **_kwargs: Any,
) -> List[Any]:
    """Fetch all edges from a graph via EpisodicMemoryStore."""
    edges = store.get_all_edges(graph_id)
    logger.info(f"Fetched {len(edges)} edges from graph {graph_id}")
    return edges
