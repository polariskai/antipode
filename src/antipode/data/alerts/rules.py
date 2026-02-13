"""
Alert rule definitions for synthetic data generation.
Rules operate on signals, not raw transactions.
"""

from typing import Dict, List, Any
from ..models.alert import AlertRiskLevel


ALERT_RULES: List[Dict[str, Any]] = [
    {
        'rule_id': 'STRUCT_001',
        'rule_name': 'Structuring Pattern',
        'description': 'Transactions structured to avoid reporting thresholds',
        'signal_conditions': [
            ('structuring_score', '>', 3),
        ],
        'base_risk': AlertRiskLevel.MEDIUM,
        'escalation_conditions': [
            ('volume_30d', '>', 50000, AlertRiskLevel.HIGH),
            ('adverse_media_flag', '==', True, AlertRiskLevel.CRITICAL),
            ('structuring_score', '>', 7, AlertRiskLevel.HIGH),
        ],
        'alert_type': 'structuring',
    },
    {
        'rule_id': 'RAPID_001',
        'rule_name': 'Rapid Movement',
        'description': 'Funds received and moved out quickly (layering)',
        'signal_conditions': [
            ('rapid_movement_score', '>', 0.5),
        ],
        'base_risk': AlertRiskLevel.MEDIUM,
        'escalation_conditions': [
            ('corridor_risk_score', '>', 50, AlertRiskLevel.HIGH),
            ('pep_distance', '<', 3, AlertRiskLevel.CRITICAL),
            ('rapid_movement_score', '>', 0.8, AlertRiskLevel.HIGH),
        ],
        'alert_type': 'rapid_movement',
    },
    {
        'rule_id': 'VOL_ANOM_001',
        'rule_name': 'Volume Anomaly',
        'description': 'Unusual transaction volume compared to history',
        'signal_conditions': [
            ('volume_zscore', '>', 2.5),
        ],
        'base_risk': AlertRiskLevel.LOW,
        'escalation_conditions': [
            ('volume_zscore', '>', 4, AlertRiskLevel.MEDIUM),
            ('declared_vs_actual_volume', '>', 3, AlertRiskLevel.HIGH),
            ('volume_zscore', '>', 5, AlertRiskLevel.HIGH),
        ],
        'alert_type': 'volume_anomaly',
    },
    {
        'rule_id': 'CORR_001',
        'rule_name': 'High-Risk Corridor',
        'description': 'Transactions to/from high-risk jurisdictions',
        'signal_conditions': [
            ('corridor_risk_score', '>', 40),
        ],
        'base_risk': AlertRiskLevel.LOW,
        'escalation_conditions': [
            ('corridor_risk_score', '>', 60, AlertRiskLevel.MEDIUM),
            ('corridor_risk_score', '>', 80, AlertRiskLevel.HIGH),
            ('sanctions_distance', '<', 2, AlertRiskLevel.CRITICAL),
        ],
        'alert_type': 'high_risk_corridor',
    },
    {
        'rule_id': 'NET_001',
        'rule_name': 'Network Risk',
        'description': 'Connected to high-risk entities in network',
        'signal_conditions': [
            ('risk_flow_in', '>', 10000),
        ],
        'base_risk': AlertRiskLevel.MEDIUM,
        'escalation_conditions': [
            ('pep_distance', '<', 2, AlertRiskLevel.HIGH),
            ('pep_distance', '==', 1, AlertRiskLevel.CRITICAL),
            ('sanctions_distance', '<', 2, AlertRiskLevel.CRITICAL),
        ],
        'alert_type': 'network_risk',
    },
    {
        'rule_id': 'MEDIA_001',
        'rule_name': 'Adverse Media',
        'description': 'Entity has adverse media hits',
        'signal_conditions': [
            ('adverse_media_flag', '==', True),
        ],
        'base_risk': AlertRiskLevel.MEDIUM,
        'escalation_conditions': [
            ('adverse_media_severity', '==', 'critical', AlertRiskLevel.HIGH),
            ('adverse_media_count', '>', 3, AlertRiskLevel.HIGH),
        ],
        'alert_type': 'adverse_media',
    },
    {
        'rule_id': 'KYC_001',
        'rule_name': 'KYC Refresh Due',
        'description': 'KYC information is stale',
        'signal_conditions': [
            ('kyc_age_days', '>', 365),
        ],
        'base_risk': AlertRiskLevel.LOW,
        'escalation_conditions': [
            ('kyc_age_days', '>', 730, AlertRiskLevel.MEDIUM),
            ('pep_flag', '==', True, AlertRiskLevel.HIGH),
        ],
        'alert_type': 'kyc_refresh',
    },
    {
        'rule_id': 'DECL_001',
        'rule_name': 'Declared vs Actual Mismatch',
        'description': 'Actual volume significantly exceeds declared',
        'signal_conditions': [
            ('declared_vs_actual_volume', '>', 2.0),
        ],
        'base_risk': AlertRiskLevel.LOW,
        'escalation_conditions': [
            ('declared_vs_actual_volume', '>', 3.0, AlertRiskLevel.MEDIUM),
            ('declared_vs_actual_volume', '>', 5.0, AlertRiskLevel.HIGH),
        ],
        'alert_type': 'declared_mismatch',
    },
    {
        'rule_id': 'CASH_001',
        'rule_name': 'High Cash Activity',
        'description': 'Unusual proportion of cash transactions',
        'signal_conditions': [
            ('cash_intensity', '>', 0.3),
        ],
        'base_risk': AlertRiskLevel.LOW,
        'escalation_conditions': [
            ('cash_intensity', '>', 0.5, AlertRiskLevel.MEDIUM),
            ('structuring_score', '>', 3, AlertRiskLevel.HIGH),
        ],
        'alert_type': 'high_cash',
    },
    {
        'rule_id': 'DORM_001',
        'rule_name': 'Dormant Account Reactivation',
        'description': 'Previously dormant account suddenly active',
        'signal_conditions': [
            ('dormancy_days', '>', 180),
            ('velocity_30d', '>', 5),
        ],
        'base_risk': AlertRiskLevel.MEDIUM,
        'escalation_conditions': [
            ('volume_zscore', '>', 3, AlertRiskLevel.HIGH),
        ],
        'alert_type': 'dormant_reactivation',
    },
    {
        'rule_id': 'ROUND_001',
        'rule_name': 'Round Amount Pattern',
        'description': 'High proportion of round-number transactions',
        'signal_conditions': [
            ('round_amount_ratio', '>', 0.5),
            ('velocity_30d', '>', 10),
        ],
        'base_risk': AlertRiskLevel.LOW,
        'escalation_conditions': [
            ('round_amount_ratio', '>', 0.7, AlertRiskLevel.MEDIUM),
            ('structuring_score', '>', 2, AlertRiskLevel.MEDIUM),
        ],
        'alert_type': 'round_amounts',
    },
    {
        'rule_id': 'NEWCP_001',
        'rule_name': 'New Counterparty Surge',
        'description': 'Sudden increase in new counterparties',
        'signal_conditions': [
            ('new_counterparty_rate', '>', 0.5),
            ('velocity_30d', '>', 10),
        ],
        'base_risk': AlertRiskLevel.LOW,
        'escalation_conditions': [
            ('new_counterparty_rate', '>', 0.7, AlertRiskLevel.MEDIUM),
            ('corridor_risk_score', '>', 40, AlertRiskLevel.MEDIUM),
        ],
        'alert_type': 'new_counterparties',
    },
]


def get_rule_by_id(rule_id: str) -> Dict[str, Any]:
    """Get a rule by its ID."""
    for rule in ALERT_RULES:
        if rule['rule_id'] == rule_id:
            return rule
    return {}


def get_rules_by_type(alert_type: str) -> List[Dict[str, Any]]:
    """Get all rules of a specific type."""
    return [r for r in ALERT_RULES if r.get('alert_type') == alert_type]
