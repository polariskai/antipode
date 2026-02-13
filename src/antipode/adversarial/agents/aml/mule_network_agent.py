"""
Mule Network Agent for AML System

Agent specialized in money mule network patterns.
Generates scenarios involving networks of money mules moving funds.
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field

from ..base.base_agent import BaseAgent, AgentConfig
from ...config.config import TypologyConfig, TypologyType, TYPOLOGY_CONFIGS


class TransactionPlanOutput(BaseModel):
    """Output from transaction planning agent"""
    transactions: List[Dict[str, Any]] = Field(description="List of transactions to generate")


class MuleNetworkAgent(BaseAgent):
    """
    Agent specialized in money mule network patterns.

    Generates scenarios involving networks of money mules moving funds.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name="MuleNetworkAgent")
        super().__init__(config)
        self.typology_config = TYPOLOGY_CONFIGS[TypologyType.MULE_NETWORK]

    def get_system_prompt(self) -> str:
        return """You are a specialized agent that generates realistic money mule network scenarios for AML testing.

Your task is to create networks of accounts that move funds in fan-in/fan-out patterns.

CONTEXT:
- Money mules are individuals who move money on behalf of others
- Patterns: Fan-in (many sources to one), Fan-out (one source to many), Cycle
- Mules often have new accounts with sudden high activity
- Networks try to avoid detection through diversity and timing

OUTPUT: Return a JSON object with:
- mules: List of mule profiles (demographics, account age, normal activity)
- hub_accounts: Central accounts that aggregate/distribute
- transaction_pattern: Description of the flow pattern
- transactions: List of transactions with timing and amounts
- recruitment_indicators: How mules were likely recruited

Create realistic mule profiles that would blend in with normal customers."""

    def get_output_schema(self) -> type:
        return TransactionPlanOutput
