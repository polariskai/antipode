"""
Entity Registry for Adversarial AML System

Provides O(1) entity lookups, entity reuse, and deduplication.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class EntityRecord:
    """Record of an entity in the registry"""
    entity_id: str
    entity_type: str
    entity_subtype: Optional[str]
    name: str
    country: str
    created_at: str
    scenarios_used: List[str] = field(default_factory=list)
    account_count: int = 0
    transaction_count: int = 0
    last_used: Optional[str] = None
    ground_truth: Dict[str, Any] = field(default_factory=dict)


class EntityRegistry:
    """
    Registry for managing entities across scenarios.

    Features:
    - O(1) lookups by entity ID
    - Entity reuse across scenarios
    - Deduplication by name/country
    - Usage statistics tracking
    """

    def __init__(self):
        # Primary index: entity_id -> EntityRecord
        self._entities: Dict[str, EntityRecord] = {}

        # Secondary indices for fast lookups
        self._by_name: Dict[str, List[str]] = {}  # name -> [entity_ids]
        self._by_country: Dict[str, List[str]] = {}  # country -> [entity_ids]
        self._by_type: Dict[str, List[str]] = {}  # type -> [entity_ids]

        # Statistics
        self._total_entities = 0
        self._total_reuses = 0

    def register(self, entity: Dict[str, Any], scenario_id: str) -> EntityRecord:
        """
        Register a new entity or return existing if duplicate.

        Args:
            entity: Entity dict from generator
            scenario_id: Scenario this entity belongs to

        Returns:
            EntityRecord (new or existing)
        """
        entity_id = entity["entity_id"]

        # Check if entity already exists
        if entity_id in self._entities:
            record = self._entities[entity_id]
            # Update usage
            if scenario_id not in record.scenarios_used:
                record.scenarios_used.append(scenario_id)
                record.last_used = datetime.now().isoformat()
                self._total_reuses += 1
                logger.debug(f"Reusing entity {entity_id} in scenario {scenario_id}")
            return record

        # Create new record
        record = EntityRecord(
            entity_id=entity_id,
            entity_type=entity.get("entity_type", "individual"),
            entity_subtype=entity.get("entity_subtype"),
            name=entity.get("name", ""),
            country=entity.get("country", ""),
            created_at=entity.get("created_at", datetime.now().isoformat()),
            scenarios_used=[scenario_id],
            last_used=datetime.now().isoformat(),
            ground_truth=entity.get("_ground_truth", {})
        )

        # Add to primary index
        self._entities[entity_id] = record

        # Update secondary indices
        self._by_name.setdefault(record.name, []).append(entity_id)
        self._by_country.setdefault(record.country, []).append(entity_id)
        self._by_type.setdefault(record.entity_type, []).append(entity_id)

        self._total_entities += 1
        logger.debug(f"Registered new entity {entity_id} ({record.name}, {record.country})")

        return record

    def get(self, entity_id: str) -> Optional[EntityRecord]:
        """Get entity by ID (O(1) lookup)"""
        return self._entities.get(entity_id)

    def find_by_name(self, name: str) -> List[EntityRecord]:
        """Find entities by name (case-sensitive)"""
        entity_ids = self._by_name.get(name, [])
        return [self._entities[eid] for eid in entity_ids]

    def find_by_country(self, country: str) -> List[EntityRecord]:
        """Find entities by country"""
        entity_ids = self._by_country.get(country, [])
        return [self._entities[eid] for eid in entity_ids]

    def find_by_type(self, entity_type: str) -> List[EntityRecord]:
        """Find entities by type"""
        entity_ids = self._by_type.get(entity_type, [])
        return [self._entities[eid] for eid in entity_ids]

    def find_similar(self, name: str, country: str, limit: int = 5) -> List[EntityRecord]:
        """
        Find entities similar to given name/country.

        Simple similarity: exact country match + name prefix match
        """
        # Start with entities in same country
        candidates = self.find_by_country(country)

        # Filter by name similarity (simple prefix match for now)
        name_lower = name.lower()
        matches = [
            e for e in candidates
            if e.name.lower().startswith(name_lower[:3]) or name_lower.startswith(e.name.lower()[:3])
        ]

        return matches[:limit]

    def update_stats(self, entity_id: str, account_delta: int = 0, transaction_delta: int = 0):
        """Update entity statistics"""
        if entity_id in self._entities:
            record = self._entities[entity_id]
            record.account_count += account_delta
            record.transaction_count += transaction_delta

    def get_reusable_entities(
        self,
        entity_type: Optional[str] = None,
        country: Optional[str] = None,
        min_age_days: int = 0,
        max_scenarios: int = 10
    ) -> List[EntityRecord]:
        """
        Get entities that can be reused in new scenarios.

        Args:
            entity_type: Filter by type
            country: Filter by country
            min_age_days: Minimum entity age in days
            max_scenarios: Max scenarios entity has been used in

        Returns:
            List of reusable entities
        """
        candidates = list(self._entities.values())

        # Apply filters
        if entity_type:
            candidates = [e for e in candidates if e.entity_type == entity_type]

        if country:
            candidates = [e for e in candidates if e.country == country]

        # Filter by scenario count
        candidates = [e for e in candidates if len(e.scenarios_used) < max_scenarios]

        # TODO: Filter by age if needed

        return candidates

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        return {
            "total_entities": self._total_entities,
            "total_reuses": self._total_reuses,
            "reuse_rate": self._total_reuses / max(1, self._total_entities),
            "by_type": {
                entity_type: len(ids)
                for entity_type, ids in self._by_type.items()
            },
            "by_country": {
                country: len(ids)
                for country, ids in sorted(self._by_country.items(), key=lambda x: -len(x[1]))[:10]
            },
            "multi_scenario_entities": len([
                e for e in self._entities.values()
                if len(e.scenarios_used) > 1
            ])
        }

    def clear(self):
        """Clear all entities (for testing)"""
        self._entities.clear()
        self._by_name.clear()
        self._by_country.clear()
        self._by_type.clear()
        self._total_entities = 0
        self._total_reuses = 0
        logger.info("Entity registry cleared")
