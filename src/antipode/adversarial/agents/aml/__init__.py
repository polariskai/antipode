"""
AML Typology Agents

Collection of agents specialized in different AML typologies.
"""

from .structuring_agent import StructuringAgent
from .layering_agent import LayeringAgent
from .integration_agent import IntegrationAgent
from .mule_network_agent import MuleNetworkAgent
from .shell_company_agent import ShellCompanyAgent
from .trade_based_agent import TradeBasedAgent
from .crypto_mixing_agent import CryptoMixingAgent

__all__ = [
    "StructuringAgent",
    "LayeringAgent",
    "IntegrationAgent",
    "MuleNetworkAgent",
    "ShellCompanyAgent",
    "TradeBasedAgent",
    "CryptoMixingAgent",
]

# Agent registry for easy instantiation
AGENT_REGISTRY = {
    "structuring": StructuringAgent,
    "layering": LayeringAgent,
    "integration": IntegrationAgent,
    "mule_network": MuleNetworkAgent,
    "shell_company": ShellCompanyAgent,
    "trade_based": TradeBasedAgent,
    "crypto_mixing": CryptoMixingAgent,
}


def get_agent(typology: str, config=None):
    """Get an agent instance by typology name"""
    if typology not in AGENT_REGISTRY:
        raise ValueError(f"Unknown typology: {typology}")
    return AGENT_REGISTRY[typology](config)


def get_all_typology_agents():
    """Get instances of all typology agents"""
    return {name: cls() for name, cls in AGENT_REGISTRY.items()}
