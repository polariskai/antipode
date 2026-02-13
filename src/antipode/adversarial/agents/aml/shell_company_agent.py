"""
Shell Company Agent for AML System

Agent specialized in shell company patterns.
Generates scenarios involving shell companies to disguise ownership and move funds.
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field

from ..base.base_agent import BaseAgent, AgentConfig
from ...config.config import TypologyConfig, TypologyType, TYPOLOGY_CONFIGS


class EntityPlanOutput(BaseModel):
    """Output from entity planning agent"""
    entities: List[Dict[str, Any]] = Field(description="List of entities to create")


class ShellCompanyAgent(BaseAgent):
    """
    Agent specialized in shell company patterns.

    Generates scenarios involving shell companies to disguise
    ownership and move funds.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name="ShellCompanyAgent")
        super().__init__(config)
        self.typology_config = TYPOLOGY_CONFIGS[TypologyType.SHELL_COMPANY]

    def get_system_prompt(self) -> str:
        return """You are a specialized agent that generates realistic shell company scenarios for AML testing.

Your task is to create corporate structures that obscure beneficial ownership and move funds.

CONTEXT:
- Shell companies have no significant operations or assets
- Used to: Hide ownership, move funds across borders, create fake invoices
- Often registered in privacy-friendly jurisdictions
- May use nominee directors and shareholders

IMPORTANT - Entity Types (CRITICAL FOR REALISM):
When creating shell companies, use ONLY these realistic entity_type values:
- "company" (for corporations)
- "LLC" (for limited liability companies - common for shells)
- "trust" (for trust structures)
- "partnership" (for partnerships)
- "foundation" (for charitable foundations)

For shell companies: Use entity_type="LLC" or "company" and set is_shell=True
For nominees: Set is_nominee=True
DO NOT use entity_type="shell_company" - that would be an obvious red flag!
In the real world, shell companies look like normal companies - that's the whole point!

OUTPUT: Return a JSON object with:
- entities: List of shell companies (use entity_type="LLC" or "company" with is_shell=True)
- ownership_structure: How companies are connected (layered ownership)
- beneficial_owners: The true owners being hidden
- nominee_directors: Front people used (set is_nominee=True)
- jurisdictions: Where companies are registered
- fake_business_activity: Simulated business to justify transactions
- transaction_flow: How money moves through the structure

Create realistic company profiles that would pass basic due diligence."""

    def get_output_schema(self) -> type:
        return EntityPlanOutput
