"""
Adversarial Agents

Reorganized agent module with agents organized by domain.

For backward compatibility, all agents are re-exported here.
"""

# AML Typology Agents
from .aml import (
    StructuringAgent,
    LayeringAgent,
    IntegrationAgent,
    MuleNetworkAgent,
    ShellCompanyAgent,
    TradeBasedAgent,
    CryptoMixingAgent,
    AGENT_REGISTRY as AML_AGENT_REGISTRY,
    get_agent,
    get_all_typology_agents,
)

# Orchestration Agents
from .orchestration import (
    ScenarioPlannerAgent,
    EvasionSpecialistAgent,
    ValidatorAgent,
)

# Base Agent Framework
from .base.base_agent import BaseAgent, VotingAgent, AgentPool, RedFlagDetector, AgentConfig

# Benign Agents
# Note: benign_agents.py still needs to be split if needed

__all__ = [
    # Base
    "BaseAgent",
    "VotingAgent",
    "AgentPool",
    "RedFlagDetector",
    "AgentConfig",
    # AML Typology
    "StructuringAgent",
    "LayeringAgent",
    "IntegrationAgent",
    "MuleNetworkAgent",
    "ShellCompanyAgent",
    "TradeBasedAgent",
    "CryptoMixingAgent",
    # Orchestration
    "ScenarioPlannerAgent",
    "EvasionSpecialistAgent",
    "ValidatorAgent",
    # Registry functions
    "AML_AGENT_REGISTRY",
    "get_agent",
    "get_all_typology_agents",
]

# Combined agent registry for backward compatibility
AGENT_REGISTRY = {
    **AML_AGENT_REGISTRY,
    "scenario_planner": ScenarioPlannerAgent,
    "evasion_specialist": EvasionSpecialistAgent,
    "validator": ValidatorAgent,
}
