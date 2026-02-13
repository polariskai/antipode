"""
Memory Manager for Adversarial AML System

Coordinates all memory components and provides unified interface.
"""

from typing import Dict, List, Optional, Any
from loguru import logger

from .entity_registry import EntityRegistry
from .transaction_ledger import TransactionLedger
from .relationship_graph import RelationshipGraph
from .scenario_tracker import ScenarioTracker


class MemoryManager:
    """
    Central manager for all memory components.

    Provides unified interface for:
    - Entity management
    - Transaction tracking
    - Relationship queries
    - Scenario coordination
    """

    def __init__(self):
        self.entities = EntityRegistry()
        self.transactions = TransactionLedger()
        self.relationships = RelationshipGraph()
        self.scenarios = ScenarioTracker()

        logger.info("Memory Manager initialized")

    def start_scenario(
        self,
        scenario_id: str,
        typology: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Start tracking a new scenario"""
        self.scenarios.start_scenario(scenario_id, typology, metadata)
        logger.info(f"Started scenario {scenario_id}")

    def register_entity(
        self,
        entity: Dict[str, Any],
        scenario_id: str
    ) -> Dict[str, Any]:
        """
        Register an entity and associate with scenario.

        Returns:
            Entity record (may be existing entity if reused)
        """
        # Register in entity registry
        record = self.entities.register(entity, scenario_id)

        # Track in scenario
        self.scenarios.add_entity(scenario_id, record.entity_id)

        return {
            "entity_id": record.entity_id,
            "entity_type": record.entity_type,
            "entity_subtype": record.entity_subtype,
            "name": record.name,
            "country": record.country,
            "created_at": record.created_at,
            "reused": len(record.scenarios_used) > 1,
            "scenarios_used": record.scenarios_used
        }

    def register_account(
        self,
        account: Dict[str, Any],
        scenario_id: str
    ):
        """Register an account and associate with scenario"""
        account_id = account.get("account_id", "")
        entity_id = account.get("entity_id", "")

        # Track in scenario
        self.scenarios.add_account(scenario_id, account_id)

        # Update entity stats
        self.entities.update_stats(entity_id, account_delta=1)

        logger.debug(f"Registered account {account_id} for entity {entity_id}")

    def record_transaction(
        self,
        transaction: Dict[str, Any],
        scenario_id: str
    ):
        """Record a transaction and update all relevant indices"""
        # Record in ledger
        record = self.transactions.record(transaction, scenario_id)

        # Track in scenario
        self.scenarios.add_transaction(
            scenario_id,
            record.txn_id,
            record.amount
        )

        # Update entity stats (TODO: need to map accounts to entities)
        # For now, just log
        logger.debug(f"Recorded transaction {record.txn_id}: ${record.amount:.2f}")

    def add_relationship(
        self,
        relationship: Dict[str, Any],
        scenario_id: str
    ):
        """Add a relationship to the graph"""
        self.relationships.add_relationship(relationship, scenario_id)

    def complete_scenario(self, scenario_id: str, success: bool = True):
        """Mark scenario as completed"""
        self.scenarios.complete_scenario(scenario_id, success)
        logger.info(f"Completed scenario {scenario_id}")

    def find_reusable_entities(
        self,
        entity_type: Optional[str] = None,
        country: Optional[str] = None,
        max_scenarios: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find entities that can be reused in new scenarios.

        Args:
            entity_type: Filter by type
            country: Filter by country
            max_scenarios: Max scenarios entity has been used in

        Returns:
            List of entity dicts
        """
        records = self.entities.get_reusable_entities(
            entity_type=entity_type,
            country=country,
            max_scenarios=max_scenarios
        )

        return [
            {
                "entity_id": r.entity_id,
                "entity_type": r.entity_type,
                "entity_subtype": r.entity_subtype,
                "name": r.name,
                "country": r.country,
                "created_at": r.created_at,
                "scenarios_used": len(r.scenarios_used),
                "account_count": r.account_count,
                "transaction_count": r.transaction_count
            }
            for r in records
        ]

    def get_entity_network(self, entity_id: str, max_hops: int = 2) -> Dict[str, Any]:
        """
        Get network of entities connected to this entity.

        Returns:
            Dict with entities and relationships
        """
        # Get connected entities
        connected_ids = self.relationships.get_connected_entities(entity_id, max_hops)

        # Get entity details
        entities = {}
        for eid in connected_ids:
            record = self.entities.get(eid)
            if record:
                entities[eid] = {
                    "entity_id": record.entity_id,
                    "name": record.name,
                    "country": record.country,
                    "entity_type": record.entity_type
                }

        # Get relationships
        relationships = []
        for eid in [entity_id] + list(connected_ids):
            for edge in self.relationships.get_outgoing(eid):
                if edge.to_entity_id in connected_ids or edge.to_entity_id == entity_id:
                    relationships.append({
                        "from": edge.from_entity_id,
                        "to": edge.to_entity_id,
                        "type": edge.relationship_type,
                        "ownership_percent": edge.ownership_percent
                    })

        return {
            "center_entity_id": entity_id,
            "connected_entities": entities,
            "relationships": relationships
        }

    def detect_patterns(self, scenario_id: str) -> Dict[str, Any]:
        """
        Detect suspicious patterns in a scenario.

        Returns:
            Dict with detected patterns
        """
        scenario = self.scenarios.get_scenario(scenario_id)
        if not scenario:
            return {}

        patterns = {
            "round_amounts": [],
            "structuring": [],
            "high_velocity": []
        }

        # Check for round amounts
        for txn_id in scenario.transaction_ids:
            txn = self.transactions.get(txn_id)
            if txn and txn.amount % 1000 == 0:
                patterns["round_amounts"].append({
                    "txn_id": txn_id,
                    "amount": txn.amount
                })

        # Check for structuring on each account
        for account_id in scenario.account_ids:
            if self.transactions.detect_structuring_pattern(account_id):
                patterns["structuring"].append({
                    "account_id": account_id
                })

        # Check velocity
        for account_id in scenario.account_ids:
            velocity = self.transactions.get_account_velocity(account_id)
            if velocity["velocity_per_day"] > 5:  # More than 5 txns/day
                patterns["high_velocity"].append({
                    "account_id": account_id,
                    "velocity_per_day": velocity["velocity_per_day"]
                })

        return patterns

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get statistics from all memory components"""
        return {
            "entities": self.entities.get_stats(),
            "transactions": self.transactions.get_stats(),
            "relationships": self.relationships.get_stats(),
            "scenarios": self.scenarios.get_stats()
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get simplified statistics for reporting.

        Returns:
            Dict with key metrics: total_entities, total_reuses, reuse_rate
        """
        entity_stats = self.entities.get_stats()
        return {
            "total_entities": entity_stats["total_entities"],
            "total_reuses": entity_stats["total_reuses"],
            "reuse_rate": entity_stats["reuse_rate"]
        }

    def clear_all(self):
        """Clear all memory (for testing)"""
        self.entities.clear()
        self.transactions.clear()
        self.relationships.clear()
        self.scenarios.clear()
        logger.info("All memory cleared")
