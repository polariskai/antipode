"""
Crypto Mixing Agent for AML System

Agent specialized in cryptocurrency mixing patterns.
Generates scenarios using crypto to obscure fund origins.
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field

from ..base.base_agent import BaseAgent, AgentConfig
from ...config.config import TypologyConfig, TypologyType, TYPOLOGY_CONFIGS


class TransactionPlanOutput(BaseModel):
    """Output from transaction planning agent"""
    transactions: List[Dict[str, Any]] = Field(description="List of transactions to generate")


class CryptoMixingAgent(BaseAgent):
    """
    Agent specialized in cryptocurrency mixing patterns.

    Generates scenarios using crypto to obscure fund origins.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name="CryptoMixingAgent")
        super().__init__(config)
        self.typology_config = TYPOLOGY_CONFIGS[TypologyType.CRYPTO_MIXING]

    def get_system_prompt(self) -> str:
        return """You are a specialized agent that generates realistic cryptocurrency mixing scenarios for AML testing.

Your task is to create scenarios that use crypto to obscure the origin of funds.

CONTEXT:
- Crypto mixing breaks the link between source and destination
- Methods: Mixers/tumblers, chain-hopping, privacy coins, DEXs
- Involves: Multiple wallets, exchanges, on/off ramps
- Goal: Convert dirty fiat to clean crypto to clean fiat

OUTPUT: Return a JSON object with:
- initial_fiat: Source of funds (currency, amount, method of crypto purchase)
- wallets: List of wallet addresses used
- exchanges: Exchanges used for conversion
- mixing_service: Mixer/tumbler details if used
- chain_hops: If moving between blockchains
- final_conversion: How crypto is converted back to fiat
- transaction_chain: Complete chain of crypto transactions

Create realistic crypto scenarios with appropriate timing and amounts."""

    def get_output_schema(self) -> type:
        return TransactionPlanOutput
