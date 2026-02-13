"""
Antipode Adversarial Synthetic Data Generation

Reorganized structure for better maintainability and PRD alignment.

New structure:
- agents/: All agent implementations organized by domain
- orchestrator/: Workflow orchestration
- memory/: Shared memory system (TODO)
- sophistication/: Detection difficulty framework (TODO)
- config/: Configuration management

For backward compatibility, legacy exports are maintained.
"""

# Legacy exports (deprecated - use new structure)
import warnings

__version__ = "2.0.0"

# New structured imports (preferred)
from .agents.base.base_agent import BaseAgent, VotingAgent, AgentPool
from .orchestrator.orchestrator import AdversarialOrchestrator, GeneratedScenario
from .orchestrator.mixed_orchestrator import MixedScenarioOrchestrator
from .config.config import OrchestratorConfig, AgentConfig

__all__ = [
    "BaseAgent",
    "VotingAgent",
    "AgentPool",
    "AdversarialOrchestrator",
    "GeneratedScenario",
    "MixedScenarioOrchestrator",
    "OrchestratorConfig",
    "AgentConfig",
]
