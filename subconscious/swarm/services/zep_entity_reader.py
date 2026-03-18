"""
Entity Reading and Filtering Service
Reads nodes from ChromaDB graph, filters those matching predefined entity types
(Original Zep dependency replaced with local EpisodicMemoryStore)
"""

import time
from typing import Dict, Any, List, Optional, Set, Callable, TypeVar
from dataclasses import dataclass, field

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.zep_entity_reader')

# Lazy import
_memory_store = None


def _get_memory_store():
    global _memory_store
    if _memory_store is None:
        from subconscious.memory import EpisodicMemoryStore
        _memory_store = EpisodicMemoryStore(persist_path=Config.CHROMADB_PERSIST_PATH)
    return _memory_store


T = TypeVar('T')


@dataclass
class EntityNode:
    """Entity Node Data Structure"""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }

    def get_entity_type(self) -> Optional[str]:
        """Get entity type (excluding default Entity label)"""
        for label in self.labels:
            if label not in ["Entity", "Node"]:
                return label
        return None


@dataclass
class FilteredEntities:
    """Filtered Entity Collection"""
    entities: List[EntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_types": list(self.entity_types),
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }


class ZepEntityReader:
    """
    Entity Reading and Filtering Service (ChromaDB-backed)

    Main features:
    1. Read all nodes from ChromaDB graph
    2. Filter nodes matching predefined entity types
    3. Get related edges and associated node info for each entity
    """

    def __init__(self, store=None):
        self.store = store or _get_memory_store()

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        """Get all nodes of the graph"""
        logger.info(f"Get graph {graph_id}  all nodes...")
        nodes = self.store.get_all_nodes(graph_id)
        nodes_data = [
            {
                "uuid": n.uuid,
                "name": n.name,
                "labels": n.labels,
                "summary": n.summary,
                "attributes": n.attributes,
            }
            for n in nodes
        ]
        logger.info(f"Retrieved  {len(nodes_data)}  nodes")
        return nodes_data

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        """Get graph all edges"""
        logger.info(f"Get graph {graph_id}  all edges...")
        edges = self.store.get_all_edges(graph_id)
        edges_data = [
            {
                "uuid": e.uuid,
                "name": e.name,
                "fact": e.fact,
                "source_node_uuid": e.source_node_uuid,
                "target_node_uuid": e.target_node_uuid,
                "attributes": e.attributes,
            }
            for e in edges
        ]
        logger.info(f"Retrieved  {len(edges_data)}  edges")
        return edges_data

    def get_node_edges(self, node_uuid: str, graph_id: str = "") -> List[Dict[str, Any]]:
        """Get all related edges of a specified node"""
        try:
            edges = self.store.get_node_edges(graph_id, node_uuid) if graph_id else []
            return [
                {
                    "uuid": e.uuid,
                    "name": e.name,
                    "fact": e.fact,
                    "source_node_uuid": e.source_node_uuid,
                    "target_node_uuid": e.target_node_uuid,
                    "attributes": e.attributes,
                }
                for e in edges
            ]
        except Exception as e:
            logger.warning(f"Get node  {node_uuid}  edges failed: {str(e)}")
            return []

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True
    ) -> FilteredEntities:
        """
        Filter nodes matching predefined entity types

        Filtering logic:
        - If a node's Labels contain only "Entity", skip it
        - If a node's Labels contain labels other than "Entity" and "Node", keep it
        """
        logger.info(f"Starting to filter graph  {graph_id}  entities...")

        all_nodes = self.get_all_nodes(graph_id)
        total_count = len(all_nodes)

        all_edges = self.get_all_edges(graph_id) if enrich_with_edges else []

        node_map = {n["uuid"]: n for n in all_nodes}

        filtered_entities = []
        entity_types_found = set()

        for node in all_nodes:
            labels = node.get("labels", [])
            custom_labels = [l for l in labels if l not in ["Entity", "Node"]]

            if not custom_labels:
                continue

            if defined_entity_types:
                matching_labels = [l for l in custom_labels if l in defined_entity_types]
                if not matching_labels:
                    continue
                entity_type = matching_labels[0]
            else:
                entity_type = custom_labels[0]

            entity_types_found.add(entity_type)

            entity = EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=labels,
                summary=node["summary"],
                attributes=node["attributes"],
            )

            if enrich_with_edges:
                related_edges = []
                related_node_uuids = set()

                for edge in all_edges:
                    if edge["source_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "outgoing",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "target_node_uuid": edge["target_node_uuid"],
                        })
                        related_node_uuids.add(edge["target_node_uuid"])
                    elif edge["target_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "incoming",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "source_node_uuid": edge["source_node_uuid"],
                        })
                        related_node_uuids.add(edge["source_node_uuid"])

                entity.related_edges = related_edges

                related_nodes = []
                for related_uuid in related_node_uuids:
                    if related_uuid in node_map:
                        related_node = node_map[related_uuid]
                        related_nodes.append({
                            "uuid": related_node["uuid"],
                            "name": related_node["name"],
                            "labels": related_node["labels"],
                            "summary": related_node.get("summary", ""),
                        })

                entity.related_nodes = related_nodes

            filtered_entities.append(entity)

        logger.info(f"Filtering complete: total nodes  {total_count}, , matching  {len(filtered_entities)}, "
                   f", entity types: {entity_types_found}")

        return FilteredEntities(
            entities=filtered_entities,
            entity_types=entity_types_found,
            total_count=total_count,
            filtered_count=len(filtered_entities),
        )

    def get_entity_with_context(
        self,
        graph_id: str,
        entity_uuid: str
    ) -> Optional[EntityNode]:
        """Get a single entity with its full context"""
        try:
            node = self.store.get_node(graph_id, entity_uuid)
            if not node:
                return None

            edges = self.store.get_node_edges(graph_id, entity_uuid)
            all_nodes = self.get_all_nodes(graph_id)
            node_map = {n["uuid"]: n for n in all_nodes}

            related_edges = []
            related_node_uuids = set()

            for edge in edges:
                if edge.source_node_uuid == entity_uuid:
                    related_edges.append({
                        "direction": "outgoing",
                        "edge_name": edge.name,
                        "fact": edge.fact,
                        "target_node_uuid": edge.target_node_uuid,
                    })
                    related_node_uuids.add(edge.target_node_uuid)
                else:
                    related_edges.append({
                        "direction": "incoming",
                        "edge_name": edge.name,
                        "fact": edge.fact,
                        "source_node_uuid": edge.source_node_uuid,
                    })
                    related_node_uuids.add(edge.source_node_uuid)

            related_nodes = []
            for related_uuid in related_node_uuids:
                if related_uuid in node_map:
                    rn = node_map[related_uuid]
                    related_nodes.append({
                        "uuid": rn["uuid"],
                        "name": rn["name"],
                        "labels": rn["labels"],
                        "summary": rn.get("summary", ""),
                    })

            return EntityNode(
                uuid=node.uuid,
                name=node.name,
                labels=node.labels,
                summary=node.summary,
                attributes=node.attributes,
                related_edges=related_edges,
                related_nodes=related_nodes,
            )

        except Exception as e:
            logger.error(f"Get entity  {entity_uuid}  failed: {str(e)}")
            return None

    def get_entities_by_type(
        self,
        graph_id: str,
        entity_type: str,
        enrich_with_edges: bool = True
    ) -> List[EntityNode]:
        """Get all entities of a specified type"""
        result = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges
        )
        return result.entities
