"""
Customer segment definitions for synthetic data generation.
Defines behavioral profiles for different customer types.
"""

from typing import Dict, Any


CUSTOMER_SEGMENTS: Dict[str, Dict[str, Any]] = {
    "retail": {
        "description": "Individual retail customers",
        "monthly_volume_range": (500, 15000),
        "txn_frequency": {"salary": 1, "rent": 1, "utilities": 4, "shopping": 15, "transfer": 3},
        "channels": {"online": 0.6, "mobile": 0.3, "branch": 0.08, "atm": 0.02},
        "corridors": {"domestic": 0.95, "cross_border": 0.05},
        "avg_txn_size": (50, 500),
        "risk_weight": 1.0,
    },
    "hnw": {
        "description": "High net worth individuals",
        "monthly_volume_range": (50000, 500000),
        "txn_frequency": {"investment": 5, "wire": 3, "luxury": 2, "transfer": 8, "fx": 2},
        "channels": {"online": 0.4, "private_banking": 0.4, "branch": 0.15, "mobile": 0.05},
        "corridors": {"domestic": 0.6, "cross_border": 0.4},
        "avg_txn_size": (5000, 100000),
        "risk_weight": 1.5,
    },
    "smb": {
        "description": "Small and medium businesses",
        "monthly_volume_range": (10000, 200000),
        "txn_frequency": {"payroll": 2, "supplier": 20, "customer": 30, "tax": 1, "loan": 1},
        "channels": {"online": 0.5, "API": 0.3, "branch": 0.15, "mobile": 0.05},
        "corridors": {"domestic": 0.85, "cross_border": 0.15},
        "avg_txn_size": (500, 10000),
        "risk_weight": 1.2,
    },
    "corporate": {
        "description": "Large corporate clients",
        "monthly_volume_range": (1000000, 100000000),
        "txn_frequency": {"payroll": 4, "supplier": 50, "treasury": 10, "fx": 5, "intercompany": 20},
        "channels": {"API": 0.6, "online": 0.3, "branch": 0.1},
        "corridors": {"domestic": 0.5, "cross_border": 0.5},
        "avg_txn_size": (10000, 5000000),
        "risk_weight": 1.3,
    },
    "correspondent": {
        "description": "Correspondent banking relationships",
        "monthly_volume_range": (10000000, 1000000000),
        "txn_frequency": {"nostro": 100, "vostro": 100, "fx": 50, "settlement": 200},
        "channels": {"SWIFT": 0.7, "API": 0.25, "manual": 0.05},
        "corridors": {"domestic": 0.2, "cross_border": 0.8},
        "avg_txn_size": (100000, 50000000),
        "risk_weight": 2.0,
    },
    "pep": {
        "description": "Politically exposed persons",
        "monthly_volume_range": (5000, 100000),
        "txn_frequency": {"salary": 1, "investment": 3, "transfer": 5, "cash": 2},
        "channels": {"online": 0.4, "branch": 0.4, "mobile": 0.2},
        "corridors": {"domestic": 0.7, "cross_border": 0.3},
        "avg_txn_size": (1000, 50000),
        "risk_weight": 3.0,
    },
    "ngo": {
        "description": "Non-governmental organizations",
        "monthly_volume_range": (5000, 500000),
        "txn_frequency": {"donation_in": 20, "grant_out": 5, "payroll": 2, "operational": 15},
        "channels": {"online": 0.5, "wire": 0.3, "branch": 0.2},
        "corridors": {"domestic": 0.4, "cross_border": 0.6},
        "avg_txn_size": (100, 50000),
        "risk_weight": 1.8,
    },
    "msb": {
        "description": "Money service businesses",
        "monthly_volume_range": (100000, 10000000),
        "txn_frequency": {"remittance_in": 500, "remittance_out": 500, "settlement": 20},
        "channels": {"API": 0.8, "branch": 0.15, "mobile": 0.05},
        "corridors": {"domestic": 0.3, "cross_border": 0.7},
        "avg_txn_size": (200, 5000),
        "risk_weight": 2.5,
    },
}


def get_segment_config(segment: str) -> Dict[str, Any]:
    """Get configuration for a customer segment."""
    return CUSTOMER_SEGMENTS.get(segment, CUSTOMER_SEGMENTS["retail"])


def get_all_segments() -> list:
    """Get list of all segment names."""
    return list(CUSTOMER_SEGMENTS.keys())
