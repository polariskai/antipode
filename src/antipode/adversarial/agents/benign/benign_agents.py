"""
Benign Transaction Agents for Realistic AML Testing

These agents generate legitimate, normal business transactions that represent
the >98% of benign activity in a real banking environment.

Key Categories:
1. Regular BAU (Business As Usual) - Normal daily transactions
2. False Positive Triggers - Legitimate transactions that look suspicious
3. Edge Cases - Transactions near thresholds but legitimate
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4
import random
import numpy as np
from pydantic import BaseModel, Field

from ..base.base_agent import BaseAgent, AgentConfig
from ...config.config import RiskLevel


class BenignPatternType:
    """Types of benign transaction patterns"""
    SALARY = "salary"
    RENT_MORTGAGE = "rent_mortgage"
    UTILITIES = "utilities"
    RETAIL = "retail"
    GROCERY = "grocery"
    SUBSCRIPTION = "subscription"
    INVESTMENT = "investment"
    LOAN_PAYMENT = "loan_payment"
    BUSINESS_PAYROLL = "business_payroll"
    BUSINESS_VENDOR = "business_vendor"
    BUSINESS_REVENUE = "business_revenue"
    INTERNATIONAL_FAMILY = "international_family"
    TAX_PAYMENT = "tax_payment"
    INSURANCE = "insurance"
    HEALTHCARE = "healthcare"


class FalsePositiveTrigger:
    """Types of false positive triggers - legitimate but looks suspicious"""
    LARGE_CASH_BUSINESS = "large_cash_business"  # Cash-intensive legitimate business
    ROUND_AMOUNT_PAYROLL = "round_amount_payroll"  # Round amounts for salaries
    JUST_BELOW_THRESHOLD = "just_below_threshold"  # Near-threshold legitimate tx
    HIGH_VOLUME_SEASONAL = "high_volume_seasonal"  # Seasonal business spikes
    INTERNATIONAL_TRADE = "international_trade"  # Legitimate cross-border trade
    REAL_ESTATE_CLOSING = "real_estate_closing"  # Large legitimate RE transactions
    CRYPTO_INVESTMENT = "crypto_investment"  # Legitimate crypto trading
    INHERITANCE = "inheritance"  # Large inheritance transfers
    BUSINESS_ACQUISITION = "business_acquisition"  # M&A related transfers
    RAPID_MOVEMENT_TREASURY = "rapid_movement_treasury"  # Corporate treasury ops


@dataclass
class BenignPatternConfig:
    """Configuration for a benign transaction pattern"""
    pattern_type: str
    description: str
    typical_amount_range: tuple  # (min, max)
    frequency: str  # daily, weekly, monthly, quarterly, annual, irregular
    typical_counterparties: List[str]
    channels: List[str]
    purposes: List[str]
    volume_per_month: tuple  # (min, max) transactions per month


# Standard benign patterns based on real banking data
BENIGN_PATTERNS: Dict[str, BenignPatternConfig] = {
    BenignPatternType.SALARY: BenignPatternConfig(
        pattern_type=BenignPatternType.SALARY,
        description="Regular salary deposits",
        typical_amount_range=(2000, 15000),
        frequency="monthly",
        typical_counterparties=["employer"],
        channels=["ach", "wire"],
        purposes=["salary", "payroll", "wages"],
        volume_per_month=(1, 2),
    ),
    BenignPatternType.RENT_MORTGAGE: BenignPatternConfig(
        pattern_type=BenignPatternType.RENT_MORTGAGE,
        description="Monthly rent or mortgage payments",
        typical_amount_range=(1000, 5000),
        frequency="monthly",
        typical_counterparties=["landlord", "mortgage_company"],
        channels=["ach", "check"],
        purposes=["rent", "mortgage", "housing"],
        volume_per_month=(1, 1),
    ),
    BenignPatternType.UTILITIES: BenignPatternConfig(
        pattern_type=BenignPatternType.UTILITIES,
        description="Utility bill payments",
        typical_amount_range=(50, 500),
        frequency="monthly",
        typical_counterparties=["utility_company"],
        channels=["ach", "online"],
        purposes=["utilities", "electric", "gas", "water"],
        volume_per_month=(3, 6),
    ),
    BenignPatternType.RETAIL: BenignPatternConfig(
        pattern_type=BenignPatternType.RETAIL,
        description="Retail purchases",
        typical_amount_range=(10, 500),
        frequency="irregular",
        typical_counterparties=["merchant"],
        channels=["card", "online"],
        purposes=["purchase", "shopping"],
        volume_per_month=(10, 50),
    ),
    BenignPatternType.GROCERY: BenignPatternConfig(
        pattern_type=BenignPatternType.GROCERY,
        description="Grocery shopping",
        typical_amount_range=(50, 300),
        frequency="weekly",
        typical_counterparties=["grocery_store"],
        channels=["card"],
        purposes=["groceries", "food"],
        volume_per_month=(4, 12),
    ),
    BenignPatternType.BUSINESS_PAYROLL: BenignPatternConfig(
        pattern_type=BenignPatternType.BUSINESS_PAYROLL,
        description="Business payroll disbursements",
        typical_amount_range=(50000, 500000),
        frequency="biweekly",
        typical_counterparties=["employees"],
        channels=["ach", "wire"],
        purposes=["payroll", "wages", "salaries"],
        volume_per_month=(2, 4),
    ),
    BenignPatternType.BUSINESS_VENDOR: BenignPatternConfig(
        pattern_type=BenignPatternType.BUSINESS_VENDOR,
        description="Business vendor payments",
        typical_amount_range=(1000, 100000),
        frequency="irregular",
        typical_counterparties=["vendor", "supplier"],
        channels=["ach", "wire", "check"],
        purposes=["invoice", "supplies", "services"],
        volume_per_month=(5, 30),
    ),
    BenignPatternType.BUSINESS_REVENUE: BenignPatternConfig(
        pattern_type=BenignPatternType.BUSINESS_REVENUE,
        description="Business revenue deposits",
        typical_amount_range=(500, 50000),
        frequency="irregular",
        typical_counterparties=["customer", "client"],
        channels=["ach", "wire", "check", "card"],
        purposes=["payment", "invoice", "sales"],
        volume_per_month=(10, 100),
    ),
    BenignPatternType.INTERNATIONAL_FAMILY: BenignPatternConfig(
        pattern_type=BenignPatternType.INTERNATIONAL_FAMILY,
        description="International family remittances",
        typical_amount_range=(200, 2000),
        frequency="monthly",
        typical_counterparties=["family_member"],
        channels=["wire", "remittance"],
        purposes=["family support", "gift", "remittance"],
        volume_per_month=(1, 4),
    ),
    BenignPatternType.INVESTMENT: BenignPatternConfig(
        pattern_type=BenignPatternType.INVESTMENT,
        description="Investment transactions",
        typical_amount_range=(100, 10000),
        frequency="monthly",
        typical_counterparties=["brokerage", "investment_fund"],
        channels=["ach", "wire"],
        purposes=["investment", "401k", "IRA", "stocks"],
        volume_per_month=(1, 5),
    ),
}

# False positive pattern configurations
FALSE_POSITIVE_PATTERNS: Dict[str, Dict[str, Any]] = {
    FalsePositiveTrigger.LARGE_CASH_BUSINESS: {
        "description": "Legitimate cash-intensive business (restaurant, retail)",
        "entity_type": "business",
        "industry": ["restaurant", "retail", "convenience_store", "laundromat"],
        "typical_cash_deposits": (5000, 25000),
        "frequency": "daily",
        "why_flagged": "High cash volume mimics structuring",
        "legitimate_reason": "Normal cash-based business operations",
    },
    FalsePositiveTrigger.ROUND_AMOUNT_PAYROLL: {
        "description": "Round salary amounts that trigger structuring alerts",
        "entity_type": "business",
        "typical_amounts": [5000, 7500, 10000, 15000],
        "frequency": "biweekly",
        "why_flagged": "Round amounts, multiple recipients",
        "legitimate_reason": "Standard payroll with round salaries",
    },
    FalsePositiveTrigger.JUST_BELOW_THRESHOLD: {
        "description": "Legitimate transactions just below reporting threshold",
        "typical_amounts": (9000, 9999),
        "frequency": "occasional",
        "why_flagged": "Appears to be avoiding CTR threshold",
        "legitimate_reason": "Coincidental amount, not intentional avoidance",
    },
    FalsePositiveTrigger.HIGH_VOLUME_SEASONAL: {
        "description": "Seasonal business with high-volume periods",
        "entity_type": "business",
        "industry": ["retail", "tourism", "agriculture", "tax_prep"],
        "volume_multiplier": (3, 10),
        "seasons": ["holiday", "summer", "tax_season"],
        "why_flagged": "Sudden volume spike",
        "legitimate_reason": "Normal seasonal business pattern",
    },
    FalsePositiveTrigger.INTERNATIONAL_TRADE: {
        "description": "Legitimate international trade transactions",
        "entity_type": "business",
        "typical_amounts": (50000, 500000),
        "countries": ["CN", "DE", "JP", "MX", "CA"],
        "why_flagged": "Large cross-border, high-risk countries",
        "legitimate_reason": "Established trade relationships with documentation",
    },
    FalsePositiveTrigger.REAL_ESTATE_CLOSING: {
        "description": "Real estate purchase closing",
        "entity_type": "individual",
        "typical_amounts": (100000, 2000000),
        "frequency": "rare",
        "why_flagged": "Large wire, possibly to title company",
        "legitimate_reason": "Documented home purchase",
    },
    FalsePositiveTrigger.INHERITANCE: {
        "description": "Inheritance or estate distribution",
        "entity_type": "individual",
        "typical_amounts": (50000, 1000000),
        "frequency": "one-time",
        "why_flagged": "Large incoming with no prior history",
        "legitimate_reason": "Documented inheritance from estate",
    },
    FalsePositiveTrigger.RAPID_MOVEMENT_TREASURY: {
        "description": "Corporate treasury operations",
        "entity_type": "business",
        "typical_amounts": (100000, 10000000),
        "frequency": "daily",
        "why_flagged": "Rapid fund movement between accounts",
        "legitimate_reason": "Normal cash management and liquidity ops",
    },
}


class BenignTransactionOutput(BaseModel):
    """Output schema for benign transaction generation"""
    transactions: List[Dict[str, Any]] = Field(description="Generated benign transactions")
    pattern_type: str = Field(description="Type of benign pattern")
    entity_context: Dict[str, Any] = Field(description="Context about the entity")


class BenignPatternAgent(BaseAgent):
    """
    Agent that generates benign, normal transaction patterns.
    
    Creates realistic BAU (Business As Usual) transactions that represent
    the majority of banking activity.
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name="BenignPatternAgent", temperature=0.7)
        super().__init__(config)
    
    def get_system_prompt(self) -> str:
        return """You are an agent that generates realistic, benign banking transaction patterns.

Your task is to create normal, everyday transactions that represent legitimate banking activity.

PATTERN TYPES:
- salary: Regular paycheck deposits
- rent_mortgage: Monthly housing payments
- utilities: Bill payments
- retail: Shopping transactions
- grocery: Food purchases
- business_payroll: Company payroll
- business_vendor: B2B payments
- business_revenue: Customer payments received
- international_family: Family remittances

OUTPUT: Return a JSON object with realistic transaction details:
{
  "transactions": [
    {
      "amount": number,
      "purpose": "string",
      "counterparty_type": "string",
      "channel": "string",
      "day_of_month": number,
      "variation_reason": "why this specific amount"
    }
  ],
  "pattern_type": "string",
  "entity_context": {
    "occupation": "string",
    "income_level": "string",
    "typical_behavior": "string"
  }
}

Make transactions realistic with natural variation in amounts and timing."""
    
    def get_output_schema(self) -> type:
        return BenignTransactionOutput
    
    def generate_pattern(
        self,
        pattern_type: str,
        entity_id: str,
        account_id: str,
        num_months: int = 12,
        scenario_id: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate benign transactions for a specific pattern type.
        
        This is a deterministic generator that doesn't require LLM calls,
        making it efficient for bulk generation.
        """
        if pattern_type not in BENIGN_PATTERNS:
            pattern_type = BenignPatternType.RETAIL  # Default
        
        config = BENIGN_PATTERNS[pattern_type]
        transactions = []
        
        base_date = datetime.now() - timedelta(days=num_months * 30)
        
        for month in range(num_months):
            month_date = base_date + timedelta(days=month * 30)
            
            # Determine number of transactions this month
            num_txns = random.randint(*config.volume_per_month)
            
            for _ in range(num_txns):
                # Generate amount with natural variation
                base_amount = random.uniform(*config.typical_amount_range)
                # Add slight variation (±5%)
                amount = base_amount * random.uniform(0.95, 1.05)
                
                # Determine day of month based on frequency
                if config.frequency == "monthly":
                    day = random.choice([1, 15, random.randint(1, 28)])
                elif config.frequency == "biweekly":
                    day = random.choice([1, 15])
                elif config.frequency == "weekly":
                    day = random.randint(1, 28)
                else:
                    day = random.randint(1, 28)
                
                txn_date = month_date.replace(day=min(day, 28))
                
                txn = {
                    "txn_id": f"TXN_{uuid4().hex[:12]}",
                    "from_account_id": account_id,
                    "to_account_id": f"EXT_{uuid4().hex[:8]}",
                    "amount": round(amount, 2),
                    "currency": "USD",
                    "txn_type": random.choice(config.channels),
                    "purpose": random.choice(config.purposes),
                    "timestamp": txn_date.isoformat(),
                    "counterparty_type": random.choice(config.typical_counterparties),
                    "_ground_truth": {
                        "is_suspicious": False,
                        "is_false_positive": False,
                        "pattern_type": pattern_type,
                        "scenario_id": scenario_id,
                        "label": "true_negative",
                    }
                }
                transactions.append(txn)
        
        return transactions


class FalsePositiveAgent(BaseAgent):
    """
    Agent that generates false positive scenarios.
    
    Creates transactions that look suspicious but are actually legitimate,
    which is critical for testing AML system precision (reducing false alarms).
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(name="FalsePositiveAgent", temperature=0.8)
        super().__init__(config)
    
    def get_system_prompt(self) -> str:
        return """You are an agent that generates FALSE POSITIVE scenarios for AML testing.

These are LEGITIMATE transactions that LOOK suspicious but are NOT actually money laundering.

FALSE POSITIVE TRIGGERS:
1. large_cash_business: Restaurant deposits $8,000 cash daily - normal for cash business
2. round_amount_payroll: Company pays $10,000 salaries - normal payroll
3. just_below_threshold: Customer deposits $9,500 for car purchase - coincidental
4. high_volume_seasonal: Retailer 5x volume in December - holiday season
5. international_trade: Manufacturer wires $200K to China - regular supplier payment
6. real_estate_closing: Wire $500K for home purchase - documented transaction
7. inheritance: Receive $300K from deceased relative's estate
8. rapid_movement_treasury: Corporate moves $1M between accounts - cash management

OUTPUT: Return JSON with:
{
  "trigger_type": "string",
  "entity": {
    "name": "string",
    "type": "individual/business",
    "industry": "string if business",
    "legitimate_reason": "why this activity is normal"
  },
  "transactions": [...],
  "documentation": ["list of supporting documents that prove legitimacy"],
  "why_flagged": "what makes this look suspicious",
  "why_legitimate": "why this is actually normal"
}

Create realistic scenarios that would challenge AML detection systems."""
    
    def get_output_schema(self) -> type:
        return BenignTransactionOutput
    
    def generate_false_positive(
        self,
        trigger_type: str,
        entity_id: str,
        account_id: str,
        scenario_id: str = None,
    ) -> Dict[str, Any]:
        """
        Generate a false positive scenario.
        """
        if trigger_type not in FALSE_POSITIVE_PATTERNS:
            trigger_type = FalsePositiveTrigger.JUST_BELOW_THRESHOLD
        
        config = FALSE_POSITIVE_PATTERNS[trigger_type]
        transactions = []
        
        if trigger_type == FalsePositiveTrigger.LARGE_CASH_BUSINESS:
            # Generate daily cash deposits for a cash-intensive business
            for day in range(30):
                amount = random.uniform(*config["typical_cash_deposits"])
                # Natural variation - weekends lower
                if day % 7 in [5, 6]:
                    amount *= 0.6
                
                txn = {
                    "txn_id": f"TXN_{uuid4().hex[:12]}",
                    "from_account_id": f"CASH_{uuid4().hex[:8]}",
                    "to_account_id": account_id,
                    "amount": round(amount, 2),
                    "currency": "USD",
                    "txn_type": "cash",
                    "purpose": "business deposit",
                    "timestamp": (datetime.now() - timedelta(days=30-day)).isoformat(),
                    "_ground_truth": {
                        "is_suspicious": False,
                        "is_false_positive": True,
                        "trigger_type": trigger_type,
                        "scenario_id": scenario_id,
                        "label": "false_positive",
                        "why_flagged": config["why_flagged"],
                        "legitimate_reason": config["legitimate_reason"],
                    }
                }
                transactions.append(txn)
                
        elif trigger_type == FalsePositiveTrigger.JUST_BELOW_THRESHOLD:
            # Generate transactions just below $10K threshold
            for _ in range(random.randint(3, 8)):
                amount = random.uniform(*config["typical_amounts"])
                
                txn = {
                    "txn_id": f"TXN_{uuid4().hex[:12]}",
                    "from_account_id": f"EXT_{uuid4().hex[:8]}",
                    "to_account_id": account_id,
                    "amount": round(amount, 2),
                    "currency": "USD",
                    "txn_type": random.choice(["cash", "check"]),
                    "purpose": random.choice(["deposit", "payment received"]),
                    "timestamp": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
                    "_ground_truth": {
                        "is_suspicious": False,
                        "is_false_positive": True,
                        "trigger_type": trigger_type,
                        "scenario_id": scenario_id,
                        "label": "false_positive",
                        "why_flagged": config["why_flagged"],
                        "legitimate_reason": config["legitimate_reason"],
                    }
                }
                transactions.append(txn)
                
        elif trigger_type == FalsePositiveTrigger.REAL_ESTATE_CLOSING:
            # Large wire for home purchase
            amount = random.uniform(*config["typical_amounts"])
            
            txn = {
                "txn_id": f"TXN_{uuid4().hex[:12]}",
                "from_account_id": account_id,
                "to_account_id": f"TITLE_{uuid4().hex[:8]}",
                "amount": round(amount, 2),
                "currency": "USD",
                "txn_type": "wire",
                "purpose": "real estate closing",
                "timestamp": datetime.now().isoformat(),
                "_ground_truth": {
                    "is_suspicious": False,
                    "is_false_positive": True,
                    "trigger_type": trigger_type,
                    "scenario_id": scenario_id,
                    "label": "false_positive",
                    "why_flagged": config["why_flagged"],
                    "legitimate_reason": config["legitimate_reason"],
                    "documentation": ["purchase agreement", "title insurance", "mortgage approval"],
                }
            }
            transactions.append(txn)
            
        elif trigger_type == FalsePositiveTrigger.HIGH_VOLUME_SEASONAL:
            # Seasonal spike in business volume
            normal_volume = random.randint(10, 30)
            spike_multiplier = random.uniform(*config["volume_multiplier"])
            spike_volume = int(normal_volume * spike_multiplier)
            
            # Normal months
            for month in range(9):
                for _ in range(normal_volume):
                    txn = {
                        "txn_id": f"TXN_{uuid4().hex[:12]}",
                        "from_account_id": f"CUST_{uuid4().hex[:8]}",
                        "to_account_id": account_id,
                        "amount": round(random.uniform(50, 500), 2),
                        "currency": "USD",
                        "txn_type": "card",
                        "purpose": "sale",
                        "timestamp": (datetime.now() - timedelta(days=270-month*30+random.randint(0,29))).isoformat(),
                        "_ground_truth": {
                            "is_suspicious": False,
                            "is_false_positive": False,
                            "pattern_type": "seasonal_business",
                            "scenario_id": scenario_id,
                            "label": "true_negative",
                        }
                    }
                    transactions.append(txn)
            
            # Spike months (last 3)
            for month in range(3):
                for _ in range(spike_volume):
                    txn = {
                        "txn_id": f"TXN_{uuid4().hex[:12]}",
                        "from_account_id": f"CUST_{uuid4().hex[:8]}",
                        "to_account_id": account_id,
                        "amount": round(random.uniform(50, 500), 2),
                        "currency": "USD",
                        "txn_type": "card",
                        "purpose": "sale",
                        "timestamp": (datetime.now() - timedelta(days=90-month*30+random.randint(0,29))).isoformat(),
                        "_ground_truth": {
                            "is_suspicious": False,
                            "is_false_positive": True,
                            "trigger_type": trigger_type,
                            "scenario_id": scenario_id,
                            "label": "false_positive",
                            "why_flagged": config["why_flagged"],
                            "legitimate_reason": config["legitimate_reason"],
                        }
                    }
                    transactions.append(txn)
        
        else:
            # Generic false positive generation
            typical_amounts = config.get("typical_amounts", (1000, 10000))
            if isinstance(typical_amounts, list):
                amount = random.choice(typical_amounts)
            else:
                amount = random.uniform(*typical_amounts)
            
            txn = {
                "txn_id": f"TXN_{uuid4().hex[:12]}",
                "from_account_id": account_id,
                "to_account_id": f"EXT_{uuid4().hex[:8]}",
                "amount": round(amount, 2),
                "currency": "USD",
                "txn_type": "wire",
                "purpose": "payment",
                "timestamp": datetime.now().isoformat(),
                "_ground_truth": {
                    "is_suspicious": False,
                    "is_false_positive": True,
                    "trigger_type": trigger_type,
                    "scenario_id": scenario_id,
                    "label": "false_positive",
                    "why_flagged": config["why_flagged"],
                    "legitimate_reason": config["legitimate_reason"],
                }
            }
            transactions.append(txn)
        
        return {
            "entity_id": entity_id,
            "account_id": account_id,
            "trigger_type": trigger_type,
            "transactions": transactions,
            "config": config,
        }


# Agent registry
BENIGN_AGENT_REGISTRY = {
    "benign_pattern": BenignPatternAgent,
    "false_positive": FalsePositiveAgent,
}


def get_benign_agent(agent_type: str, config: Optional[AgentConfig] = None) -> BaseAgent:
    """Get a benign agent instance"""
    if agent_type not in BENIGN_AGENT_REGISTRY:
        raise ValueError(f"Unknown benign agent type: {agent_type}")
    return BENIGN_AGENT_REGISTRY[agent_type](config)
