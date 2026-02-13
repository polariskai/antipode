"""
Validator Agent for AML System

Agent that validates generated scenarios for realism and consistency.
Ensures generated data is plausible and internally consistent.
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from ..base.base_agent import BaseAgent, AgentConfig


class ValidationOutput(BaseModel):
    """Output from validator agent"""
    is_valid: bool = Field(description="Whether the scenario is valid")
    is_realistic: bool = Field(description="Whether the scenario is realistic")
    detection_difficulty: float = Field(description="Estimated detection difficulty 0-1")
    issues: List[str] = Field(description="List of issues found")
    suggestions: List[str] = Field(description="Suggestions for improvement")


class ValidatorAgent(BaseAgent):
    """
    Agent that validates generated scenarios for realism and consistency.

    Ensures generated data is plausible and internally consistent.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name="Validator", temperature=0.2)
        super().__init__(config)

    def get_system_prompt(self) -> str:
        return """You are a validator that checks money laundering scenarios for realism and consistency.

Your task is to analyze a scenario and identify any issues that would make it unrealistic or inconsistent.

CHECK FOR:
1. Temporal consistency (transactions in logical order, realistic timing)
2. Amount consistency (funds balance, fees make sense)
3. Entity consistency (entities have realistic attributes, relationships make sense)
4. Geographic consistency (jurisdictions make sense for the typology)
5. Behavioral realism (activity matches entity profile)

OUTPUT: Return a JSON object with:
{
  "is_valid": true/false,
  "is_realistic": true/false,
  "detection_difficulty": 0.0-1.0,
  "issues": ["list of problems found"],
  "suggestions": ["how to fix the issues"],
  "confidence": 0.0-1.0 (confidence in assessment)
}

Be thorough but practical. Minor issues can be noted but shouldn't fail validation."""

    def get_output_schema(self) -> type:
        return ValidationOutput
