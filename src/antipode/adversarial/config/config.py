"""
Configuration for the Adversarial AML Agent System
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import os

# Load global config to get default model
try:
    from ...config import config as global_config
    DEFAULT_MODEL = global_config.groq.model if hasattr(global_config, 'groq') else "qwen/qwen3-32b"
except Exception:
    # Fallback if global config not available
    DEFAULT_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")


class TypologyType(Enum):
    """Money laundering typology types"""
    STRUCTURING = "structuring"
    LAYERING = "layering"
    INTEGRATION = "integration"
    MULE_NETWORK = "mule_network"
    SHELL_COMPANY = "shell_company"
    TRADE_BASED = "trade_based"
    CRYPTO_MIXING = "crypto_mixing"
    ROUND_TRIPPING = "round_tripping"
    LOAN_BACK = "loan_back"
    REAL_ESTATE = "real_estate"
    CASH_INTENSIVE = "cash_intensive"
    CORRESPONDENT_BANKING = "correspondent_banking"


class RiskLevel(Enum):
    """Risk levels for generated scenarios"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentConfig:
    """Configuration for individual micro-agents"""
    name: str
    model: str = field(default_factory=lambda: DEFAULT_MODEL)
    temperature: float = 0.7
    max_tokens: int = 4000  # Increased from 1000 to handle complex JSON generation
    max_retries: int = 3
    timeout_seconds: int = 30
    red_flag_max_tokens: int = 4000  # Increased from 2000 to match new max_tokens
    voting_k: int = 2  # First-to-ahead-by-k voting margin
    api_key: Optional[str] = None  # API key for fallback (not used with Groq)


@dataclass
class TypologyConfig:
    """Configuration for a money laundering typology"""
    typology_type: TypologyType
    description: str
    risk_level: RiskLevel
    min_transactions: int
    max_transactions: int
    min_entities: int
    max_entities: int
    typical_amount_range: tuple  # (min, max) in USD
    detection_difficulty: float  # 0.0 (easy) to 1.0 (hard)
    indicators: List[str] = field(default_factory=list)
    evasion_techniques: List[str] = field(default_factory=list)


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator"""
    model: str = field(default_factory=lambda: DEFAULT_MODEL)
    max_concurrent_agents: int = 5
    voting_k: int = 2  # Voting margin for orchestrator decisions (reduced from 3 to 2 for better consensus)
    max_scenario_complexity: int = 10  # Max number of typologies to combine
    ground_truth_output_dir: str = "data/adversarial_ground_truth"


# Default typology configurations
TYPOLOGY_CONFIGS: Dict[TypologyType, TypologyConfig] = {
    TypologyType.STRUCTURING: TypologyConfig(
        typology_type=TypologyType.STRUCTURING,
        description="Breaking large amounts into smaller transactions below reporting thresholds",
        risk_level=RiskLevel.MEDIUM,
        min_transactions=5,
        max_transactions=50,
        min_entities=1,
        max_entities=3,
        typical_amount_range=(1000, 9900),
        detection_difficulty=0.3,
        indicators=[
            "Multiple transactions just below $10,000",
            "Same-day deposits across multiple branches",
            "Round dollar amounts",
            "Sequential transaction IDs",
        ],
        evasion_techniques=[
            "Vary amounts slightly",
            "Use different branches",
            "Space transactions over time",
            "Use multiple account holders",
        ],
    ),
    TypologyType.LAYERING: TypologyConfig(
        typology_type=TypologyType.LAYERING,
        description="Creating complex layers of transactions to obscure the money trail",
        risk_level=RiskLevel.HIGH,
        min_transactions=10,
        max_transactions=100,
        min_entities=5,
        max_entities=20,
        typical_amount_range=(10000, 500000),
        detection_difficulty=0.7,
        indicators=[
            "Rapid movement of funds",
            "Multiple intermediary accounts",
            "Cross-border transactions",
            "Shell company involvement",
        ],
        evasion_techniques=[
            "Use legitimate-looking business transactions",
            "Mix with normal business activity",
            "Use multiple jurisdictions",
            "Employ professional intermediaries",
        ],
    ),
    TypologyType.INTEGRATION: TypologyConfig(
        typology_type=TypologyType.INTEGRATION,
        description="Reintroducing laundered money into the legitimate economy",
        risk_level=RiskLevel.HIGH,
        min_transactions=3,
        max_transactions=20,
        min_entities=2,
        max_entities=10,
        typical_amount_range=(50000, 5000000),
        detection_difficulty=0.8,
        indicators=[
            "Large asset purchases",
            "Investment in legitimate businesses",
            "Real estate transactions",
            "Luxury goods purchases",
        ],
        evasion_techniques=[
            "Use third-party purchasers",
            "Create paper trail through loans",
            "Mix funds with legitimate income",
            "Use offshore accounts",
        ],
    ),
    TypologyType.MULE_NETWORK: TypologyConfig(
        typology_type=TypologyType.MULE_NETWORK,
        description="Using money mules to move funds through multiple accounts",
        risk_level=RiskLevel.HIGH,
        min_transactions=20,
        max_transactions=200,
        min_entities=10,
        max_entities=50,
        typical_amount_range=(500, 50000),
        detection_difficulty=0.6,
        indicators=[
            "New accounts with sudden high activity",
            "Fan-in/fan-out patterns",
            "Similar transaction patterns across accounts",
            "Accounts linked by shared attributes",
        ],
        evasion_techniques=[
            "Recruit diverse mules",
            "Vary transaction amounts",
            "Use different channels",
            "Rotate mule accounts frequently",
        ],
    ),
    TypologyType.SHELL_COMPANY: TypologyConfig(
        typology_type=TypologyType.SHELL_COMPANY,
        description="Using shell companies to disguise ownership and move funds",
        risk_level=RiskLevel.CRITICAL,
        min_transactions=5,
        max_transactions=50,
        min_entities=3,
        max_entities=15,
        typical_amount_range=(100000, 10000000),
        detection_difficulty=0.9,
        indicators=[
            "Companies with no clear business purpose",
            "Nominee directors/shareholders",
            "High-risk jurisdiction registration",
            "Complex ownership structures",
        ],
        evasion_techniques=[
            "Use legitimate-sounding business names",
            "Create paper trail of contracts",
            "Use professional service providers",
            "Layer company ownership across jurisdictions",
        ],
    ),
    TypologyType.TRADE_BASED: TypologyConfig(
        typology_type=TypologyType.TRADE_BASED,
        description="Using trade transactions to move value across borders",
        risk_level=RiskLevel.CRITICAL,
        min_transactions=3,
        max_transactions=30,
        min_entities=4,
        max_entities=12,
        typical_amount_range=(50000, 5000000),
        detection_difficulty=0.85,
        indicators=[
            "Over/under-invoicing",
            "Multiple invoicing for same goods",
            "Phantom shipments",
            "Unusual trade partners",
        ],
        evasion_techniques=[
            "Use legitimate trade documents",
            "Mix with normal trade activity",
            "Use free trade zones",
            "Employ complex supply chains",
        ],
    ),
    TypologyType.CRYPTO_MIXING: TypologyConfig(
        typology_type=TypologyType.CRYPTO_MIXING,
        description="Using cryptocurrency mixing services to obscure fund origins",
        risk_level=RiskLevel.HIGH,
        min_transactions=5,
        max_transactions=100,
        min_entities=3,
        max_entities=20,
        typical_amount_range=(5000, 1000000),
        detection_difficulty=0.75,
        indicators=[
            "Transactions through mixing services",
            "Rapid crypto-to-fiat conversions",
            "Multiple wallet addresses",
            "High-risk exchange usage",
        ],
        evasion_techniques=[
            "Use privacy coins",
            "Chain-hop across blockchains",
            "Use decentralized exchanges",
            "Split transactions across time",
        ],
    ),
}


# Micro-agent definitions for each typology
MICRO_AGENT_SPECS = {
    "entity_creator": AgentConfig(
        name="EntityCreator",
        model="gpt-4o-mini",
        temperature=0.8,
    ),
    "account_creator": AgentConfig(
        name="AccountCreator",
        model="gpt-4o-mini",
        temperature=0.7,
    ),
    "transaction_generator": AgentConfig(
        name="TransactionGenerator",
        model="gpt-4o-mini",
        temperature=0.6,
    ),
    "relationship_builder": AgentConfig(
        name="RelationshipBuilder",
        model="gpt-4o-mini",
        temperature=0.7,
    ),
    "scenario_planner": AgentConfig(
        name="ScenarioPlanner",
        model="gpt-4o",
        temperature=0.9,
    ),
    "evasion_specialist": AgentConfig(
        name="EvasionSpecialist",
        model="gpt-4o",
        temperature=0.8,
    ),
    "validator": AgentConfig(
        name="Validator",
        model="gpt-4o-mini",
        temperature=0.2,
    ),
}
