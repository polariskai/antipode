"""
Typology definitions for AML synthetic data generation.
Based on common money laundering patterns and FATF typologies.
"""

from typing import Dict, Any, List


TYPOLOGIES: Dict[str, Dict[str, Any]] = {
    "structuring": {
        "description": "Breaking large amounts into smaller transactions to avoid reporting thresholds",
        "indicators": ["amounts_just_below_threshold", "multiple_branches", "short_timeframe"],
        "params": {
            "threshold": 10000,
            "margin": 500,              # amounts between threshold-margin and threshold
            "num_transactions": (5, 15),
            "timeframe_days": (1, 5),
        },
        "risk_level": "high",
        "prevalence": 0.02,  # 2% of suspicious activity
    },
    "rapid_movement": {
        "description": "Funds received and moved out quickly (layering)",
        "indicators": ["in_out_velocity", "different_counterparties", "cross_border"],
        "params": {
            "velocity_hours": (1, 48),  # time between in and out
            "amount_retention": (0.90, 0.99),  # % moved out
            "hops": (2, 5),
        },
        "risk_level": "high",
        "prevalence": 0.03,
    },
    "fan_in": {
        "description": "Multiple sources sending to single account (collection)",
        "indicators": ["many_originators", "consolidation", "similar_amounts"],
        "params": {
            "num_sources": (5, 20),
            "timeframe_days": (1, 7),
            "amount_variance": 0.1,
        },
        "risk_level": "medium",
        "prevalence": 0.02,
    },
    "fan_out": {
        "description": "Single source distributing to multiple accounts (distribution)",
        "indicators": ["many_beneficiaries", "similar_amounts", "short_timeframe"],
        "params": {
            "num_destinations": (5, 20),
            "timeframe_days": (1, 7),
            "amount_variance": 0.1,
        },
        "risk_level": "medium",
        "prevalence": 0.02,
    },
    "cycle": {
        "description": "Circular flow of funds (round-tripping)",
        "indicators": ["circular_path", "similar_amounts", "layered_entities"],
        "params": {
            "cycle_length": (3, 6),     # number of hops
            "amount_decay": (0.95, 0.99),
            "timeframe_days": (3, 14),
        },
        "risk_level": "critical",
        "prevalence": 0.01,
    },
    "mule": {
        "description": "Account used as pass-through for illicit funds",
        "indicators": ["new_account", "high_volume_sudden", "many_counterparties"],
        "params": {
            "account_age_days": (30, 90),
            "volume_spike_multiplier": (5, 20),
            "num_counterparties": (10, 50),
        },
        "risk_level": "critical",
        "prevalence": 0.01,
    },
    "high_risk_corridor": {
        "description": "Transactions to/from high-risk jurisdictions",
        "indicators": ["hr_jurisdiction", "unusual_for_customer", "large_amounts"],
        "params": {
            "jurisdictions": ["IR", "KP", "SY", "CU", "VE", "MM", "AF"],
            "amount_multiplier": (2, 10),
        },
        "risk_level": "high",
        "prevalence": 0.02,
    },
    "trade_based": {
        "description": "Over/under invoicing in trade transactions",
        "indicators": ["price_anomaly", "unusual_goods", "mismatched_documents"],
        "params": {
            "price_deviation": (0.3, 0.7),  # 30-70% over/under market
            "goods_categories": ["electronics", "textiles", "commodities"],
        },
        "risk_level": "high",
        "prevalence": 0.01,
    },
    "shell_company": {
        "description": "Transactions through shell companies with no real business",
        "indicators": ["no_employees", "registered_agent", "offshore_jurisdiction"],
        "params": {
            "jurisdictions": ["KY", "VG", "BM", "PA"],
            "transaction_types": ["wire", "investment"],
        },
        "risk_level": "critical",
        "prevalence": 0.01,
    },
    "cash_intensive": {
        "description": "Unusual cash deposits inconsistent with business type",
        "indicators": ["high_cash_ratio", "round_amounts", "multiple_locations"],
        "params": {
            "cash_ratio": (0.5, 0.9),
            "deposit_frequency": (10, 30),  # per month
        },
        "risk_level": "medium",
        "prevalence": 0.02,
    },
    "insider_trading": {
        "description": "Trading based on material non-public information",
        "indicators": ["pre_announcement_trades", "connected_persons", "unusual_size"],
        "params": {
            "days_before_announcement": (1, 5),
            "profit_multiplier": (1.5, 5),
        },
        "risk_level": "critical",
        "prevalence": 0.005,
    },
}


def get_typology(name: str) -> Dict[str, Any]:
    """Get typology definition by name."""
    return TYPOLOGIES.get(name, {})


def get_all_typology_names() -> List[str]:
    """Get list of all typology names."""
    return list(TYPOLOGIES.keys())


def get_typologies_by_risk(risk_level: str) -> List[str]:
    """Get typologies filtered by risk level."""
    return [
        name for name, config in TYPOLOGIES.items()
        if config.get('risk_level') == risk_level
    ]
