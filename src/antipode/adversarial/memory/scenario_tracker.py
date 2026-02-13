"""
Scenario Tracker for Adversarial AML System

Tracks active scenarios and prevents temporal/logical conflicts.
"""

from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class ScenarioRecord:
    """Record of a scenario"""
    scenario_id: str
    typology: str
    status: str  # "active", "completed", "failed"
    created_at: str
    completed_at: Optional[str] = None
    entity_ids: Set[str] = field(default_factory=set)
    account_ids: Set[str] = field(default_factory=set)
    transaction_ids: Set[str] = field(default_factory=set)
    total_amount: float = 0.0
    num_transactions: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScenarioTracker:
    """
    Tracker for managing scenarios across generations.

    Features:
    - Track active vs completed scenarios
    - Prevent entity conflicts (same entity in multiple active scenarios)
    - Temporal consistency checking
    - Scenario dependency tracking
    """

    def __init__(self):
        # Scenarios by ID
        self._scenarios: Dict[str, ScenarioRecord] = {}

        # Active scenarios
        self._active_scenarios: Set[str] = set()

        # Reverse indices
        self._entity_to_scenarios: Dict[str, Set[str]] = {}  # entity_id -> {scenario_ids}
        self._account_to_scenarios: Dict[str, Set[str]] = {}  # account_id -> {scenario_ids}

        # Statistics
        self._total_scenarios = 0
        self._completed_scenarios = 0
        self._failed_scenarios = 0

    def start_scenario(
        self,
        scenario_id: str,
        typology: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ScenarioRecord:
        """
        Start tracking a new scenario.

        Args:
            scenario_id: Unique scenario identifier
            typology: AML typology type
            metadata: Additional scenario metadata

        Returns:
            ScenarioRecord
        """
        if scenario_id in self._scenarios:
            logger.warning(f"Scenario {scenario_id} already exists")
            return self._scenarios[scenario_id]

        record = ScenarioRecord(
            scenario_id=scenario_id,
            typology=typology,
            status="active",
            created_at=datetime.now().isoformat(),
            metadata=metadata or {}
        )

        self._scenarios[scenario_id] = record
        self._active_scenarios.add(scenario_id)
        self._total_scenarios += 1

        logger.info(f"Started tracking scenario {scenario_id} ({typology})")

        return record

    def add_entity(self, scenario_id: str, entity_id: str):
        """Associate an entity with a scenario"""
        if scenario_id in self._scenarios:
            self._scenarios[scenario_id].entity_ids.add(entity_id)

            # Update reverse index
            if entity_id not in self._entity_to_scenarios:
                self._entity_to_scenarios[entity_id] = set()
            self._entity_to_scenarios[entity_id].add(scenario_id)

    def add_account(self, scenario_id: str, account_id: str):
        """Associate an account with a scenario"""
        if scenario_id in self._scenarios:
            self._scenarios[scenario_id].account_ids.add(account_id)

            # Update reverse index
            if account_id not in self._account_to_scenarios:
                self._account_to_scenarios[account_id] = set()
            self._account_to_scenarios[account_id].add(scenario_id)

    def add_transaction(self, scenario_id: str, txn_id: str, amount: float):
        """Add a transaction to scenario tracking"""
        if scenario_id in self._scenarios:
            record = self._scenarios[scenario_id]
            record.transaction_ids.add(txn_id)
            record.total_amount += amount
            record.num_transactions += 1

    def complete_scenario(self, scenario_id: str, success: bool = True):
        """Mark scenario as completed"""
        if scenario_id in self._scenarios:
            record = self._scenarios[scenario_id]
            record.status = "completed" if success else "failed"
            record.completed_at = datetime.now().isoformat()

            # Remove from active
            self._active_scenarios.discard(scenario_id)

            if success:
                self._completed_scenarios += 1
            else:
                self._failed_scenarios += 1

            logger.info(f"Completed scenario {scenario_id} ({'success' if success else 'failed'})")

    def get_scenario(self, scenario_id: str) -> Optional[ScenarioRecord]:
        """Get scenario by ID"""
        return self._scenarios.get(scenario_id)

    def get_active_scenarios(self) -> List[ScenarioRecord]:
        """Get all active scenarios"""
        return [
            self._scenarios[sid]
            for sid in self._active_scenarios
            if sid in self._scenarios
        ]

    def get_scenarios_for_entity(self, entity_id: str) -> List[ScenarioRecord]:
        """Get all scenarios involving an entity"""
        scenario_ids = self._entity_to_scenarios.get(entity_id, set())
        return [self._scenarios[sid] for sid in scenario_ids if sid in self._scenarios]

    def get_scenarios_for_account(self, account_id: str) -> List[ScenarioRecord]:
        """Get all scenarios involving an account"""
        scenario_ids = self._account_to_scenarios.get(account_id, set())
        return [self._scenarios[sid] for sid in scenario_ids if sid in self._scenarios]

    def check_entity_conflict(self, entity_id: str) -> bool:
        """
        Check if entity is involved in active scenarios.

        Returns:
            True if entity is in use (conflict)
        """
        scenarios = self.get_scenarios_for_entity(entity_id)
        active = [s for s in scenarios if s.status == "active"]
        return len(active) > 0

    def check_account_conflict(self, account_id: str) -> bool:
        """
        Check if account is involved in active scenarios.

        Returns:
            True if account is in use (conflict)
        """
        scenarios = self.get_scenarios_for_account(account_id)
        active = [s for s in scenarios if s.status == "active"]
        return len(active) > 0

    def get_available_entities(
        self,
        all_entity_ids: List[str]
    ) -> List[str]:
        """
        Get entities not involved in active scenarios.

        Args:
            all_entity_ids: List of all entity IDs to check

        Returns:
            List of available entity IDs
        """
        return [
            eid for eid in all_entity_ids
            if not self.check_entity_conflict(eid)
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics"""
        return {
            "total_scenarios": self._total_scenarios,
            "completed_scenarios": self._completed_scenarios,
            "failed_scenarios": self._failed_scenarios,
            "active_scenarios": len(self._active_scenarios),
            "completion_rate": self._completed_scenarios / max(1, self._total_scenarios),
            "failure_rate": self._failed_scenarios / max(1, self._total_scenarios),
        }

    def clear(self):
        """Clear all scenarios (for testing)"""
        self._scenarios.clear()
        self._active_scenarios.clear()
        self._entity_to_scenarios.clear()
        self._account_to_scenarios.clear()
        self._total_scenarios = 0
        self._completed_scenarios = 0
        self._failed_scenarios = 0
        logger.info("Scenario tracker cleared")
