"""
Layering Agent for AML System

Agent specialized in layering patterns.
Generates complex chains of transactions through multiple intermediaries
to obscure the origin of funds.
"""

from typing import Optional
from pydantic import BaseModel, Field
from typing import Dict, List, Any

from ..base.base_agent import BaseAgent, AgentConfig
from ...config.config import TypologyConfig, TypologyType, TYPOLOGY_CONFIGS


class TransactionPlanOutput(BaseModel):
    """Output from transaction planning agent"""
    transactions: List[Dict[str, Any]] = Field(description="List of transactions to generate")


class LayeringAgent(BaseAgent):
    """
    Agent specialized in layering patterns.

    Generates complex chains of transactions through multiple intermediaries
    to obscure the origin of funds.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name="LayeringAgent")
        super().__init__(config)
        self.typology_config = TYPOLOGY_CONFIGS[TypologyType.LAYERING]

    def get_system_prompt(self) -> str:
        return """You are a specialized agent that generates realistic layering scenarios for AML testing.

Your task is to create complex transaction chains that obscure the trail of funds.

CONTEXT:
- Layering involves moving money through multiple accounts and entities
- Goals: Create distance from source, mix with legitimate funds, cross jurisdictions
- Methods: Wire transfers, shell companies, trade transactions, crypto

IMPORTANT - Entity Types:
When creating entities, use ONLY these realistic entity_type values:
- "individual" (for people)
- "company" (for corporations)
- "LLC" (for limited liability companies)
- "trust" (for trust structures)
- "partnership" (for partnerships)
- "foundation" (for charitable foundations)

For shell companies: Use entity_type="company" or "LLC" and set is_shell=True
For nominees: Set is_nominee=True
DO NOT use entity_type="shell_company" - that's not realistic!

OUTPUT: Return a JSON object with:
- entities: List of intermediary entities (use realistic entity_type values above, set is_shell=True for shells)
- accounts: List of accounts for each entity
- transaction_chain: Ordered list of transactions from source to destination
- jurisdictions: Countries involved
- stated_purposes: Realistic business purposes for each transaction

Each entity and transaction should have realistic attributes that make detection difficult."""

    def get_output_schema(self) -> type:
        return TransactionPlanOutput
