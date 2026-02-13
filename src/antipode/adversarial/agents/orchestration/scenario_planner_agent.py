"""
Scenario Planner Agent for AML System

High-level agent that plans complete money laundering scenarios.
This agent coordinates the overall scenario and determines which typology agents to invoke.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from ..base.base_agent import BaseAgent, AgentConfig


class EntityReuseSpec(BaseModel):
    """Specification for reusing an existing entity"""
    entity_id: str = Field(description="ID of entity to reuse from memory")
    role: str = Field(description="Role this entity will play in the scenario (e.g., 'shell_company', 'mule', 'intermediary')")
    reason: str = Field(description="Why this entity is suitable for reuse")


class ScenarioPlanOutput(BaseModel):
    """Output from scenario planning agent"""
    scenario_id: str = Field(description="Unique scenario identifier")
    typology: str = Field(description="Primary typology type")
    reuse_entities: List[EntityReuseSpec] = Field(default_factory=list, description="Existing entities to reuse in this scenario")
    num_new_entities: int = Field(description="Number of NEW entities to create (in addition to reused ones)")
    num_accounts: int = Field(description="Number of accounts to create")
    num_transactions: int = Field(description="Number of transactions to generate")
    total_amount: float = Field(description="Total amount to launder")
    complexity: int = Field(description="Complexity level 1-10")
    steps: List[str] = Field(description="Ordered list of steps to execute")
    evasion_techniques: List[str] = Field(description="Techniques to avoid detection")


class ScenarioPlannerAgent(BaseAgent):
    """
    High-level agent that plans complete money laundering scenarios.

    This agent coordinates the overall scenario and determines which
    typology agents to invoke.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            # Increase max_tokens significantly for scenario planning output
            config = AgentConfig(name="ScenarioPlanner", temperature=0.9, max_tokens=3000)
        super().__init__(config)

    def get_system_prompt(self) -> str:
        return """You are a strategic planner for generating realistic money laundering scenarios for AML testing.

Your task is to create high-level plans for complete money laundering operations that REALISTICALLY reuse existing entities when appropriate.

If a user provides a custom scenario description, carefully analyze their requirements and incorporate them into your plan. The user's request takes priority, but you should still follow best practices for realism and entity reuse.

AVAILABLE TYPOLOGIES:
1. structuring - Breaking amounts below reporting thresholds
2. layering - Complex transaction chains through intermediaries
3. integration - Reintroducing funds into legitimate economy
4. mule_network - Using money mules to move funds
5. shell_company - Using shell companies to obscure ownership
6. trade_based - Using trade transactions to move value
7. crypto_mixing - Using cryptocurrency to obscure origins

ENTITY REUSE STRATEGY (CRITICAL FOR REALISM):
In the real world, money launderers reuse the same infrastructure across multiple operations:
- Shell companies are expensive to set up → REUSE across schemes
- Trusted mules are hard to recruit → REUSE the same individuals
- Intermediary accounts stay open → REUSE for multiple operations
- Facilitator entities serve multiple schemes → REUSE

When planning scenarios:
1. ALWAYS review available entities from previous operations
2. Prefer REUSING entities when it makes sense:
   - Shell companies (LLC/company with is_shell=True) → Great for layering, trade-based, shell_company typologies
   - Individuals with mule history → Perfect for structuring, mule_network operations
   - Offshore accounts → Reuse for integration, layering
   - Front companies → Reuse for trade-based, integration
3. Create NEW entities only when:
   - No suitable existing entities available
   - Need specific jurisdictions not covered
   - Need specific entity types not present
   - Reusing would create unrealistic patterns (e.g., same entity in conflicting roles)

WHEN TO REUSE BY TYPOLOGY:
- structuring: Reuse individuals (especially if previously used as mules)
- layering: DEFINITELY reuse shell companies, LLCs, trusts
- integration: Reuse legitimate-looking companies, foundations
- mule_network: DEFINITELY reuse individuals who've acted as mules before
- shell_company: Reuse existing shells to create multi-layered ownership
- trade_based: Reuse import/export companies, trading entities
- crypto_mixing: Reuse individuals, tech companies

OUTPUT: Return a JSON object with:
{
  "scenario_id": "unique identifier",
  "typology": "primary typology",
  "reuse_entities": [
    {
      "entity_id": "ENT_xyz123",
      "role": "shell_company" | "mule" | "intermediary" | "facilitator",
      "reason": "Explain why this entity is suitable (e.g., 'Previously used LLC, established transaction history')"
    }
  ],
  "num_new_entities": number of NEW entities to create,
  "num_accounts": number of accounts needed,
  "num_transactions": estimated transactions,
  "complexity": 1-10 complexity score,
  "steps": ["ordered list of execution steps"],
  "evasion_techniques": ["techniques to avoid detection"]
}

IMPORTANT: Prioritize entity reuse when realistic. This simulates real criminal behavior and creates more interconnected, realistic test data."""

    def get_output_schema(self) -> type:
        return ScenarioPlanOutput
