"""
Relationship Graph for Adversarial AML System

Provides network queries for entity connections and ownership structures.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict, deque
from loguru import logger


@dataclass
class RelationshipEdge:
    """Edge in the relationship graph"""
    from_entity_id: str
    to_entity_id: str
    relationship_type: str
    ownership_percent: Optional[float] = None
    is_hidden: bool = False
    scenario_id: str = ""


class RelationshipGraph:
    """
    Graph for managing entity relationships.

    Features:
    - Network queries (find paths between entities)
    - Ownership structure analysis
    - Hidden relationship detection
    - Connected component analysis
    """

    def __init__(self):
        # Adjacency lists for directed graph
        self._outgoing: Dict[str, List[RelationshipEdge]] = defaultdict(list)
        self._incoming: Dict[str, List[RelationshipEdge]] = defaultdict(list)

        # All relationships
        self._relationships: List[RelationshipEdge] = []

        # Statistics
        self._total_relationships = 0
        self._hidden_relationships = 0

    def add_relationship(self, relationship: Dict[str, Any], scenario_id: str) -> RelationshipEdge:
        """
        Add a relationship between entities.

        Args:
            relationship: Relationship dict from generator
            scenario_id: Scenario this relationship belongs to

        Returns:
            RelationshipEdge
        """
        edge = RelationshipEdge(
            from_entity_id=relationship.get("from_entity_id", ""),
            to_entity_id=relationship.get("to_entity_id", ""),
            relationship_type=relationship.get("relationship_type", "related_to"),
            ownership_percent=relationship.get("ownership_percent"),
            is_hidden=relationship.get("is_hidden", False),
            scenario_id=scenario_id
        )

        # Add to adjacency lists
        self._outgoing[edge.from_entity_id].append(edge)
        self._incoming[edge.to_entity_id].append(edge)
        self._relationships.append(edge)

        # Update stats
        self._total_relationships += 1
        if edge.is_hidden:
            self._hidden_relationships += 1

        logger.debug(
            f"Added relationship: {edge.from_entity_id} --[{edge.relationship_type}]--> {edge.to_entity_id}"
        )

        return edge

    def get_outgoing(self, entity_id: str) -> List[RelationshipEdge]:
        """Get all outgoing relationships for an entity"""
        return self._outgoing.get(entity_id, [])

    def get_incoming(self, entity_id: str) -> List[RelationshipEdge]:
        """Get all incoming relationships for an entity"""
        return self._incoming.get(entity_id, [])

    def get_all_relationships(self, entity_id: str) -> List[RelationshipEdge]:
        """Get all relationships (incoming + outgoing) for an entity"""
        return self.get_outgoing(entity_id) + self.get_incoming(entity_id)

    def find_path(
        self,
        from_entity_id: str,
        to_entity_id: str,
        max_hops: int = 3
    ) -> Optional[List[RelationshipEdge]]:
        """
        Find shortest path between two entities (BFS).

        Args:
            from_entity_id: Starting entity
            to_entity_id: Target entity
            max_hops: Maximum path length

        Returns:
            List of edges forming path, or None if no path found
        """
        if from_entity_id == to_entity_id:
            return []

        # BFS with path tracking
        queue = deque([(from_entity_id, [])])
        visited = {from_entity_id}

        while queue:
            current_id, path = queue.popleft()

            # Check hop limit
            if len(path) >= max_hops:
                continue

            # Explore outgoing edges
            for edge in self.get_outgoing(current_id):
                next_id = edge.to_entity_id

                if next_id == to_entity_id:
                    return path + [edge]

                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [edge]))

        return None  # No path found

    def find_all_paths(
        self,
        from_entity_id: str,
        to_entity_id: str,
        max_hops: int = 3,
        max_paths: int = 10
    ) -> List[List[RelationshipEdge]]:
        """
        Find all paths between two entities (DFS).

        Args:
            from_entity_id: Starting entity
            to_entity_id: Target entity
            max_hops: Maximum path length
            max_paths: Maximum number of paths to return

        Returns:
            List of paths (each path is a list of edges)
        """
        all_paths = []

        def dfs(current_id: str, target_id: str, path: List[RelationshipEdge], visited: Set[str]):
            if len(all_paths) >= max_paths:
                return

            if len(path) >= max_hops:
                return

            if current_id == target_id and path:
                all_paths.append(path[:])
                return

            for edge in self.get_outgoing(current_id):
                next_id = edge.to_entity_id
                if next_id not in visited:
                    visited.add(next_id)
                    path.append(edge)
                    dfs(next_id, target_id, path, visited)
                    path.pop()
                    visited.remove(next_id)

        dfs(from_entity_id, to_entity_id, [], {from_entity_id})
        return all_paths

    def get_connected_entities(self, entity_id: str, max_hops: int = 2) -> Set[str]:
        """
        Get all entities connected to this entity within max_hops.

        Args:
            entity_id: Starting entity
            max_hops: Maximum distance

        Returns:
            Set of connected entity IDs
        """
        connected = set()
        queue = deque([(entity_id, 0)])
        visited = {entity_id}

        while queue:
            current_id, hops = queue.popleft()

            if hops >= max_hops:
                continue

            # Explore both outgoing and incoming edges
            for edge in self.get_outgoing(current_id) + self.get_incoming(current_id):
                next_id = edge.to_entity_id if edge.from_entity_id == current_id else edge.from_entity_id

                if next_id not in visited:
                    visited.add(next_id)
                    connected.add(next_id)
                    queue.append((next_id, hops + 1))

        return connected

    def get_ownership_chain(self, entity_id: str) -> List[Tuple[str, float]]:
        """
        Get ownership chain for an entity.

        Returns:
            List of (owner_entity_id, ownership_percent) tuples
        """
        ownership_chain = []

        current_id = entity_id
        visited = {entity_id}

        while True:
            # Find incoming "owns" relationships
            owners = [
                edge for edge in self.get_incoming(current_id)
                if edge.relationship_type == "owns"
            ]

            if not owners:
                break

            # Take the largest owner
            owners.sort(key=lambda e: e.ownership_percent or 0, reverse=True)
            owner_edge = owners[0]

            if owner_edge.from_entity_id in visited:
                # Circular ownership detected
                break

            ownership_chain.append((owner_edge.from_entity_id, owner_edge.ownership_percent or 0))
            visited.add(owner_edge.from_entity_id)
            current_id = owner_edge.from_entity_id

        return ownership_chain

    def get_hidden_relationships(self) -> List[RelationshipEdge]:
        """Get all hidden relationships"""
        return [edge for edge in self._relationships if edge.is_hidden]

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        # Count relationship types
        type_counts = defaultdict(int)
        for edge in self._relationships:
            type_counts[edge.relationship_type] += 1

        return {
            "total_relationships": self._total_relationships,
            "hidden_relationships": self._hidden_relationships,
            "hidden_rate": self._hidden_relationships / max(1, self._total_relationships),
            "entities_with_relationships": len(self._outgoing) + len(self._incoming),
            "relationship_types": dict(type_counts),
        }

    def clear(self):
        """Clear all relationships (for testing)"""
        self._outgoing.clear()
        self._incoming.clear()
        self._relationships.clear()
        self._total_relationships = 0
        self._hidden_relationships = 0
        logger.info("Relationship graph cleared")
