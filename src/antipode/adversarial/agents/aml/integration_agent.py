"""
Integration Agent for AML System

Agent specialized in integration patterns.
Generates scenarios for reintroducing laundered funds into the legitimate economy.
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field

from ..base.base_agent import BaseAgent, AgentConfig
from ...config.config import TypologyConfig, TypologyType, TYPOLOGY_CONFIGS


class TransactionPlanOutput(BaseModel):
    """Output from transaction planning agent"""
    transactions: List[Dict[str, Any]] = Field(description="List of transactions to generate")


class IntegrationAgent(BaseAgent):
    """
    Agent specialized in integration patterns.

    Generates scenarios for reintroducing laundered funds into the
    legitimate economy.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name="IntegrationAgent")
        super().__init__(config)
        self.typology_config = TYPOLOGY_CONFIGS[TypologyType.INTEGRATION]

    def get_system_prompt(self) -> str:
        return """You are a specialized agent that generates realistic integration scenarios for AML testing.

Your task is to create scenarios for reintroducing laundered money into the legitimate economy.

CONTEXT:
- Integration is the final stage of money laundering
- Methods: Real estate purchases, business investments, luxury goods, loans
- Goal: Create legitimate-appearing income/wealth

OUTPUT: Return a JSON object with:
- target_assets: What will be purchased/invested in
- entities: Entities involved in the integration
- transaction_flow: How money moves from laundered state to legitimate assets
- paper_trail: Documentation that legitimizes the funds
- total_value: Value being integrated

Focus on realistic scenarios that would be difficult to distinguish from legitimate wealth."""

    def get_output_schema(self) -> type:
        return TransactionPlanOutput
