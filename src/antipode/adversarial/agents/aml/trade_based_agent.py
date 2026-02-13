"""
Trade-Based Agent for AML System

Agent specialized in trade-based money laundering patterns.
Generates scenarios using trade transactions to move value.
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field

from ..base.base_agent import BaseAgent, AgentConfig
from ...config.config import TypologyConfig, TypologyType, TYPOLOGY_CONFIGS


class TransactionPlanOutput(BaseModel):
    """Output from transaction planning agent"""
    transactions: List[Dict[str, Any]] = Field(description="List of transactions to generate")


class TradeBasedAgent(BaseAgent):
    """
    Agent specialized in trade-based money laundering patterns.

    Generates scenarios using trade transactions to move value.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name="TradeBasedAgent")
        super().__init__(config)
        self.typology_config = TYPOLOGY_CONFIGS[TypologyType.TRADE_BASED]

    def get_system_prompt(self) -> str:
        return """You are a specialized agent that generates realistic trade-based money laundering scenarios for AML testing.

Your task is to create scenarios that use international trade to move value.

CONTEXT:
- Trade-based ML uses trade transactions to transfer value across borders
- Methods: Over/under invoicing, multiple invoicing, phantom shipments
- Involves: Importers, exporters, banks providing trade finance
- Difficult to detect due to complexity of international trade

OUTPUT: Return a JSON object with:
- trade_parties: Importer, exporter, intermediaries
- goods: What is being traded (real or phantom)
- invoices: Invoice amounts and discrepancies
- true_value: Actual value of goods if real
- inflated_value: Invoiced value for over-invoicing scenarios
- payments: Trade finance transactions
- documentation: Trade documents that support the fraud

Create realistic trade scenarios with plausible goods and prices."""

    def get_output_schema(self) -> type:
        return TransactionPlanOutput
