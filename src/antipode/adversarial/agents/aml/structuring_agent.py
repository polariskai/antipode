"""
Structuring Agent for AML System

Agent specialized in structuring/smurfing patterns.
Generates scenarios where large amounts are broken into smaller
transactions to avoid reporting thresholds.
"""

from typing import Optional
from pydantic import BaseModel, Field
from typing import Dict, List, Any

from ..base.base_agent import BaseAgent, AgentConfig
from ...config.config import TypologyConfig, TypologyType, TYPOLOGY_CONFIGS


class TransactionPlanOutput(BaseModel):
    """Output from transaction planning agent"""
    transactions: List[Dict[str, Any]] = Field(description="List of transactions to generate")


class StructuringAgent(BaseAgent):
    """
    Agent specialized in structuring/smurfing patterns.

    Generates scenarios where large amounts are broken into smaller
    transactions to avoid reporting thresholds.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name="StructuringAgent")
        super().__init__(config)
        self.typology_config = TYPOLOGY_CONFIGS[TypologyType.STRUCTURING]

    def get_system_prompt(self) -> str:
        return """You are a specialized agent that generates realistic structuring/smurfing scenarios for AML testing.

Your task is to create a plan for breaking large amounts into smaller transactions below reporting thresholds.

CONTEXT:
- Structuring involves splitting large transactions into smaller ones to avoid Currency Transaction Reports (CTRs)
- In the US, the threshold is $10,000 for cash transactions
- Sophisticated structurers vary amounts, timing, locations, and methods

OUTPUT: Return a JSON object with the transaction plan. Each transaction should include:
- amount: Below threshold, with realistic variation
- timing: Spread across time to avoid pattern detection
- method: Cash, check, ACH, etc.
- location: Different branches/banks if applicable
- purpose: Realistic stated purpose

Be creative but realistic. The goal is to generate data that tests AML detection systems."""

    def get_output_schema(self) -> type:
        return TransactionPlanOutput
