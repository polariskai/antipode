"""
Evasion Specialist Agent for AML System

Agent that modifies scenarios to make them harder to detect.
Applies evasion techniques to generated data to create more challenging test cases.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from ..base.base_agent import BaseAgent, AgentConfig


class EvasionOutput(BaseModel):
    """Output from evasion specialist agent"""
    modifications: List[Dict[str, Any]] = Field(description="Modifications to apply")
    reasoning: str = Field(description="Why these modifications help avoid detection")


class EvasionSpecialistAgent(BaseAgent):
    """
    Agent that modifies scenarios to make them harder to detect.

    Applies evasion techniques to generated data to create more
    challenging test cases.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name="EvasionSpecialist", temperature=0.8)
        super().__init__(config)

    def get_system_prompt(self) -> str:
        return """You are an evasion specialist that modifies money laundering scenarios to avoid detection.

Your task is to analyze a scenario and suggest modifications that would make it harder to detect.

COMMON DETECTION METHODS TO EVADE:
1. Rule-based alerts (thresholds, patterns, velocities)
2. Network analysis (entity relationships, transaction graphs)
3. Behavioral analysis (deviation from normal activity)
4. Geographic risk scoring
5. Entity screening (PEP, sanctions, adverse media)

OUTPUT: Return a JSON object with:
{
  "modifications": [
    {
      "target": "what to modify (entity, transaction, timing, etc.)",
      "original": "current value/state",
      "modified": "new value/state",
      "reasoning": "why this helps avoid detection"
    }
  ],
  "overall_reasoning": "summary of evasion strategy",
  "estimated_detection_reduction": 0.0-1.0 (how much harder to detect)
}

Be creative but realistic. The goal is to generate challenging test cases."""

    def get_output_schema(self) -> type:
        return EvasionOutput
