"""
Signal definitions for synthetic data generation.
Signals are DERIVED features computed from raw event data by analysis models.
"""

from typing import Dict, Any


SIGNAL_DEFINITIONS: Dict[str, Dict[str, Dict[str, Any]]] = {
    # Behavioral signals (computed from transaction history)
    "behavioral": {
        "velocity_30d": {
            "description": "Transaction count in last 30 days",
            "computation": "count(txns where ts > now - 30d)",
            "type": "numeric",
            "threshold_low": 5,
            "threshold_high": 100,
        },
        "volume_30d": {
            "description": "Total volume in last 30 days",
            "computation": "sum(amount where ts > now - 30d)",
            "type": "numeric",
            "threshold_low": 1000,
            "threshold_high": 100000,
        },
        "volume_zscore": {
            "description": "Current month volume vs historical mean (z-score)",
            "computation": "(current_month_vol - mean_monthly_vol) / std_monthly_vol",
            "type": "numeric",
            "threshold_alert": 2.5,
            "threshold_high": 4.0,
        },
        "peer_deviation": {
            "description": "Deviation from peer group behavior",
            "computation": "customer_metric / peer_group_median",
            "type": "numeric",
            "threshold_alert": 2.0,
        },
        "in_out_ratio": {
            "description": "Ratio of incoming to outgoing funds",
            "computation": "sum(credits) / sum(debits)",
            "type": "numeric",
            "normal_range": (0.8, 1.2),
            "suspicious_range": (0.95, 1.05),  # Too balanced = layering
        },
        "rapid_movement_score": {
            "description": "Score for funds moving in and out quickly",
            "computation": "weighted_sum(txns where out_ts - in_ts < 48h)",
            "type": "numeric",
            "threshold_alert": 0.5,
            "threshold_high": 0.8,
        },
        "structuring_score": {
            "description": "Score for transactions near reporting threshold",
            "computation": "count(txns where threshold - 1000 < amount < threshold)",
            "type": "numeric",
            "threshold_alert": 3,
            "threshold_high": 5,
        },
        "counterparty_concentration": {
            "description": "HHI of counterparty distribution (0-1)",
            "computation": "sum(counterparty_share^2)",
            "type": "numeric",
            "threshold_low": 0.1,  # Diverse
            "threshold_high": 0.5,  # Concentrated
        },
        "new_counterparty_rate": {
            "description": "Rate of new counterparties in recent period",
            "computation": "count(new_counterparties_30d) / count(all_counterparties)",
            "type": "numeric",
            "threshold_alert": 0.5,
        },
        "corridor_risk_score": {
            "description": "Weighted score based on destination countries (0-100)",
            "computation": "sum(amount * country_risk_weight) / sum(amount)",
            "type": "numeric",
            "threshold_low": 20,
            "threshold_medium": 40,
            "threshold_high": 60,
        },
        "cash_intensity": {
            "description": "Proportion of transactions involving cash",
            "computation": "count(cash_txns) / count(all_txns)",
            "type": "numeric",
            "threshold_alert": 0.3,
        },
        "round_amount_ratio": {
            "description": "Proportion of round-number transactions",
            "computation": "count(round_amounts) / count(all_txns)",
            "type": "numeric",
            "threshold_alert": 0.5,
        },
    },
    
    # Network signals (computed from graph)
    "network": {
        "degree_centrality": {
            "description": "Number of direct connections",
            "computation": "count(edges)",
            "type": "numeric",
        },
        "betweenness_centrality": {
            "description": "How often node lies on shortest paths",
            "computation": "betweenness_centrality(node)",
            "type": "numeric",
        },
        "risk_flow_in": {
            "description": "Incoming flow from high-risk nodes",
            "computation": "sum(incoming_amount where source_risk > threshold)",
            "type": "numeric",
            "threshold_alert": 10000,
        },
        "risk_flow_out": {
            "description": "Outgoing flow to high-risk nodes",
            "computation": "sum(outgoing_amount where dest_risk > threshold)",
            "type": "numeric",
            "threshold_alert": 10000,
        },
        "shared_attribute_score": {
            "description": "Score for shared addresses/phones/devices",
            "computation": "weighted_count(shared_attributes)",
            "type": "numeric",
            "threshold_alert": 2,
        },
        "pep_distance": {
            "description": "Shortest path distance to known PEP",
            "computation": "min(path_length to PEP nodes)",
            "type": "numeric",
            "threshold_close": 2,
            "threshold_medium": 4,
        },
        "sanctions_distance": {
            "description": "Shortest path distance to sanctioned entity",
            "computation": "min(path_length to sanctioned nodes)",
            "type": "numeric",
            "threshold_close": 2,
        },
        "cluster_risk_score": {
            "description": "Average risk of connected cluster",
            "computation": "mean(risk_score of cluster members)",
            "type": "numeric",
        },
    },
    
    # Entity signals (from KYC/screening)
    "entity": {
        "pep_flag": {
            "description": "Is entity a PEP or PEP-related",
            "computation": "screening_result",
            "type": "boolean",
        },
        "sanctions_flag": {
            "description": "Entity on sanctions list",
            "computation": "screening_result",
            "type": "boolean",
        },
        "adverse_media_flag": {
            "description": "Entity has adverse media hits",
            "computation": "count(adverse_news) > 0",
            "type": "boolean",
        },
        "adverse_media_count": {
            "description": "Number of adverse media hits",
            "computation": "count(adverse_news)",
            "type": "numeric",
        },
        "adverse_media_severity": {
            "description": "Max severity of adverse media",
            "computation": "max(news_severity)",
            "type": "categorical",
            "values": ["none", "low", "medium", "high", "critical"],
        },
        "jurisdiction_risk": {
            "description": "Risk level of entity jurisdiction (0-100)",
            "computation": "lookup(jurisdiction_risk_table)",
            "type": "numeric",
        },
        "kyc_age_days": {
            "description": "Days since last KYC refresh",
            "computation": "now - last_kyc_date",
            "type": "numeric",
            "threshold_stale": 365,
            "threshold_very_stale": 730,
        },
        "declared_vs_actual_volume": {
            "description": "Ratio of actual to declared volume",
            "computation": "actual_monthly_vol / declared_monthly_vol",
            "type": "numeric",
            "threshold_low": 0.5,  # Under-utilizing
            "threshold_high": 2.0,  # Exceeding declared
            "threshold_alert": 3.0,  # Significantly exceeding
        },
        "account_age_days": {
            "description": "Days since account opened",
            "computation": "now - open_date",
            "type": "numeric",
            "threshold_new": 90,
        },
        "dormancy_days": {
            "description": "Days since last transaction",
            "computation": "now - last_txn_date",
            "type": "numeric",
            "threshold_dormant": 180,
        },
    },
}


def get_signal_threshold(category: str, signal_name: str, threshold_type: str) -> float:
    """Get a specific threshold for a signal."""
    signal = SIGNAL_DEFINITIONS.get(category, {}).get(signal_name, {})
    return signal.get(threshold_type, 0)


def get_all_signal_names() -> list:
    """Get list of all signal names."""
    names = []
    for category, signals in SIGNAL_DEFINITIONS.items():
        for signal_name in signals.keys():
            names.append(f"{category}.{signal_name}")
    return names
