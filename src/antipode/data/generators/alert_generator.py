"""
Alert rules engine for synthetic data generation.
Generates alerts from signals (not raw transactions).
"""

import numpy as np
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4
from collections import Counter

from ..alerts.rules import ALERT_RULES
from ..models.alert import Alert, AlertRiskLevel, AlertStatus, ALERT_DISTRIBUTION


class AlertRulesEngine:
    """
    Generate alerts from signals (not raw transactions).
    
    Rules operate on the signal layer, not raw data.
    This ensures proper separation of concerns.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, seed: int = 42):
        self.config = config or {}
        np.random.seed(seed)
        
        self.rules = ALERT_RULES
        
        # Target distribution
        self.target_distribution = ALERT_DISTRIBUTION
        
        # False positive generation rate (to reach target distribution)
        self.fp_generation_rate = self.config.get('fp_generation_rate', 0.1)
    
    def generate_alerts(
        self,
        account_signals: List[Dict],
        scenarios: Optional[List[Dict]] = None,
        as_of_date: Optional[date] = None,
    ) -> List[Dict]:
        """
        Generate alerts from signals with target distribution.
        
        Args:
            account_signals: List of signal dictionaries per account
            scenarios: Optional list of ground truth scenarios for labeling
            as_of_date: Date to generate alerts as of
            
        Returns:
            List of alert dictionaries
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        alerts = []
        
        # Build scenario lookup for ground truth
        scenario_by_account = {}
        if scenarios:
            for s in scenarios:
                scenario_by_account[s.get('primary_account', '')] = s
        
        # Generate rule-based alerts
        for signals in account_signals:
            account_id = signals.get('account_id', '')
            
            for rule in self.rules:
                if self._rule_matches(signals, rule):
                    risk_level = self._determine_risk_level(signals, rule)
                    
                    alert = self._create_alert(
                        signals=signals,
                        rule=rule,
                        risk_level=risk_level,
                        as_of_date=as_of_date,
                        scenario=scenario_by_account.get(account_id),
                    )
                    alerts.append(alert)
        
        # Adjust distribution to match targets
        alerts = self._adjust_distribution(alerts, account_signals, as_of_date)
        
        return alerts
    
    def _rule_matches(self, signals: Dict, rule: Dict) -> bool:
        """Check if signals match rule conditions."""
        conditions = rule.get('signal_conditions', [])
        
        for condition in conditions:
            if len(condition) == 3:
                signal_name, operator, threshold = condition
            else:
                continue
            
            signal_value = signals.get(signal_name)
            if signal_value is None:
                return False
            
            if not self._evaluate_condition(signal_value, operator, threshold):
                return False
        
        return True
    
    def _evaluate_condition(self, value: Any, operator: str, threshold: Any) -> bool:
        """Evaluate a single condition."""
        try:
            if operator == '>':
                return value > threshold
            elif operator == '<':
                return value < threshold
            elif operator == '>=':
                return value >= threshold
            elif operator == '<=':
                return value <= threshold
            elif operator == '==':
                return value == threshold
            elif operator == '!=':
                return value != threshold
            elif operator == 'between':
                return threshold[0] <= value <= threshold[1]
            elif operator == 'in':
                return value in threshold
            else:
                return False
        except (TypeError, ValueError):
            return False
    
    def _determine_risk_level(self, signals: Dict, rule: Dict) -> AlertRiskLevel:
        """Determine alert risk level based on escalation conditions."""
        risk_level = rule.get('base_risk', AlertRiskLevel.LOW)
        
        escalation_conditions = rule.get('escalation_conditions', [])
        
        for condition in escalation_conditions:
            if len(condition) == 4:
                signal_name, operator, threshold, escalated_level = condition
            else:
                continue
            
            signal_value = signals.get(signal_name)
            if signal_value is None:
                continue
            
            if self._evaluate_condition(signal_value, operator, threshold):
                # Escalate to higher level
                if self._risk_level_order(escalated_level) > self._risk_level_order(risk_level):
                    risk_level = escalated_level
        
        return risk_level
    
    def _risk_level_order(self, level: AlertRiskLevel) -> int:
        """Get numeric order for risk level comparison."""
        order = {
            AlertRiskLevel.LOW: 1,
            AlertRiskLevel.MEDIUM: 2,
            AlertRiskLevel.HIGH: 3,
            AlertRiskLevel.CRITICAL: 4,
        }
        return order.get(level, 0)
    
    def _create_alert(
        self,
        signals: Dict,
        rule: Dict,
        risk_level: AlertRiskLevel,
        as_of_date: date,
        scenario: Optional[Dict] = None,
    ) -> Dict:
        """Create an alert dictionary."""
        account_id = signals.get('account_id', '')
        customer_id = signals.get('customer_id', '')
        
        # Compute score based on signals and risk level
        score = self._compute_score(signals, rule, risk_level)
        
        # Extract risk factors
        risk_factors = self._extract_risk_factors(signals, rule)
        
        # Get triggering signals
        triggering_signals = self._get_triggering_signals(signals, rule)
        
        # Get contributing transaction IDs based on alert type
        transaction_ids = self._get_contributing_transactions(signals, rule)
        
        alert = Alert(
            alert_id=f"ALERT_{uuid4().hex[:12]}",
            created_ts=datetime.combine(as_of_date, datetime.min.time()),
            rule_id=rule['rule_id'],
            rule_name=rule['rule_name'],
            account_id=account_id,
            customer_id=customer_id,
            risk_level=risk_level,
            score=score,
            risk_factors=risk_factors,
            transaction_ids=transaction_ids,
            triggering_signals=triggering_signals,
            alert_type=rule.get('alert_type', ''),
            description=rule.get('description', ''),
            status=AlertStatus.NEW,
            _true_positive=scenario is not None,
            _scenario_id=scenario.get('scenario_id') if scenario else None,
            _typology=scenario.get('typology') if scenario else None,
        )
        
        return alert.to_dict()
    
    def _compute_score(
        self,
        signals: Dict,
        rule: Dict,
        risk_level: AlertRiskLevel
    ) -> float:
        """Compute alert confidence score (0-100)."""
        # Base score from risk level
        base_scores = {
            AlertRiskLevel.LOW: 25,
            AlertRiskLevel.MEDIUM: 50,
            AlertRiskLevel.HIGH: 75,
            AlertRiskLevel.CRITICAL: 90,
        }
        base = base_scores.get(risk_level, 25)
        
        # Adjust based on signal strength
        adjustments = 0
        conditions = rule.get('signal_conditions', [])
        
        for condition in conditions:
            if len(condition) >= 3:
                signal_name, operator, threshold = condition[:3]
                signal_value = signals.get(signal_name, 0)
                
                if isinstance(signal_value, (int, float)) and isinstance(threshold, (int, float)):
                    if operator == '>' and threshold > 0:
                        ratio = signal_value / threshold
                        adjustments += min(10, (ratio - 1) * 5)
        
        # Add some noise
        noise = np.random.uniform(-5, 5)
        
        return min(100, max(0, base + adjustments + noise))
    
    def _extract_risk_factors(self, signals: Dict, rule: Dict) -> List[str]:
        """Extract human-readable risk factors."""
        factors = []
        
        # Check each condition
        conditions = rule.get('signal_conditions', []) + [
            c[:3] for c in rule.get('escalation_conditions', [])
        ]
        
        factor_descriptions = {
            'structuring_score': 'Transactions near reporting threshold',
            'rapid_movement_score': 'Rapid in-out fund movement',
            'volume_zscore': 'Unusual transaction volume',
            'corridor_risk_score': 'High-risk jurisdiction activity',
            'pep_distance': 'Proximity to PEP',
            'sanctions_distance': 'Proximity to sanctioned entity',
            'adverse_media_flag': 'Adverse media present',
            'declared_vs_actual_volume': 'Volume exceeds declared',
            'cash_intensity': 'High cash activity',
            'kyc_age_days': 'Stale KYC information',
        }
        
        for condition in conditions:
            if len(condition) >= 3:
                signal_name = condition[0]
                if signal_name in factor_descriptions:
                    factors.append(factor_descriptions[signal_name])
        
        return list(set(factors))  # Deduplicate
    
    def _get_triggering_signals(self, signals: Dict, rule: Dict) -> Dict[str, float]:
        """Get the signal values that triggered the alert."""
        triggering = {}
        
        conditions = rule.get('signal_conditions', [])
        for condition in conditions:
            if len(condition) >= 3:
                signal_name = condition[0]
                value = signals.get(signal_name)
                if value is not None:
                    triggering[signal_name] = value
        
        return triggering
    
    def _get_contributing_transactions(self, signals: Dict, rule: Dict) -> List[str]:
        """Get transaction IDs that contributed to this alert.
        
        Maps alert types to the relevant signal's contributing transactions.
        Falls back to volume_30d transactions if specific signal has no transactions.
        """
        contributing_txns = signals.get('_contributing_txns', {})
        alert_type = rule.get('alert_type', '')
        
        # Map alert types to their relevant signal transaction sources
        alert_to_signal_map = {
            'structuring': 'structuring_score',
            'high_risk_corridor': 'corridor_risk_score',
            'volume_anomaly': 'volume_30d',
            'round_amounts': 'round_amount_ratio',
            'rapid_movement': 'velocity_30d',
            'new_counterparties': 'velocity_30d',
        }
        
        # Transaction-based alert types that should always have transaction IDs
        transaction_based_alerts = ['structuring', 'high_risk_corridor', 'volume_anomaly', 'round_amounts', 'rapid_movement']
        
        signal_name = alert_to_signal_map.get(alert_type)
        
        if signal_name and signal_name in contributing_txns:
            txn_ids = contributing_txns[signal_name]
            if txn_ids:
                # Limit to first 100 transactions to avoid huge lists
                return txn_ids[:100] if len(txn_ids) > 100 else txn_ids
        
        # For transaction-based alerts, fall back to volume_30d transactions
        if alert_type in transaction_based_alerts:
            fallback_txns = contributing_txns.get('volume_30d', [])
            if fallback_txns:
                return fallback_txns[:50]
        
        return []
    
    def _adjust_distribution(
        self,
        alerts: List[Dict],
        account_signals: List[Dict],
        as_of_date: date
    ) -> List[Dict]:
        """
        Adjust alert distribution to match realistic targets:
        - ~70% low risk
        - ~20% medium risk  
        - ~8% high risk
        - ~1-2% critical (SAR-able)
        """
        if not alerts:
            return alerts
        
        current_counts = Counter(a.get('risk_level', 'low') for a in alerts)
        total = len(alerts)
        
        # Ensure we have some critical alerts (upgrade highest-risk ones)
        critical_count = current_counts.get('critical', 0)
        target_critical = max(1, int(total * 0.02))  # At least 1-2%
        
        if critical_count < target_critical:
            # Upgrade some high-risk alerts to critical
            high_alerts = [a for a in alerts if a.get('risk_level') == 'high']
            upgrade_count = min(target_critical - critical_count, len(high_alerts))
            
            for i in range(upgrade_count):
                if i < len(high_alerts):
                    high_alerts[i]['risk_level'] = 'critical'
                    high_alerts[i]['score'] = min(100, high_alerts[i].get('score', 75) + 15)
        
        # Recalculate counts
        current_counts = Counter(a.get('risk_level', 'low') for a in alerts)
        
        # Calculate target for low-risk FP alerts
        target_total = int(total / 0.30)  # Scale up to get proper distribution
        target_low = int(target_total * self.target_distribution[AlertRiskLevel.LOW])
        
        current_low = current_counts.get('low', 0)
        
        if current_low < target_low:
            # Generate additional low-risk FP alerts
            fp_needed = min(target_low - current_low, len(account_signals) // 2)
            fp_alerts = self._generate_false_positive_alerts(
                account_signals, fp_needed, as_of_date
            )
            alerts.extend(fp_alerts)
        
        return alerts
    
    def _generate_false_positive_alerts(
        self,
        account_signals: List[Dict],
        count: int,
        as_of_date: date
    ) -> List[Dict]:
        """Generate false positive alerts for realistic distribution."""
        fp_alerts = []
        
        # Select random accounts for FP alerts
        if len(account_signals) < count:
            selected = account_signals
        else:
            indices = np.random.choice(len(account_signals), size=count, replace=False)
            selected = [account_signals[i] for i in indices]
        
        # FP-prone rules (rules that commonly generate false positives)
        fp_rules = [
            {
                'rule_id': 'VOL_ANOM_FP',
                'rule_name': 'Volume Anomaly',
                'alert_type': 'volume_anomaly',
                'description': 'Slight volume increase detected',
            },
            {
                'rule_id': 'CORR_FP',
                'rule_name': 'Corridor Activity',
                'alert_type': 'high_risk_corridor',
                'description': 'Transaction to monitored jurisdiction',
            },
            {
                'rule_id': 'ROUND_FP',
                'rule_name': 'Round Amount Pattern',
                'alert_type': 'round_amounts',
                'description': 'Round number transactions detected',
            },
        ]
        
        for signals in selected:
            rule = np.random.choice(fp_rules)
            
            # Get contributing transactions for FP alerts too
            transaction_ids = self._get_contributing_transactions(signals, rule)
            
            alert = Alert(
                alert_id=f"ALERT_{uuid4().hex[:12]}",
                created_ts=datetime.combine(as_of_date, datetime.min.time()),
                rule_id=rule['rule_id'],
                rule_name=rule['rule_name'],
                account_id=signals.get('account_id', ''),
                customer_id=signals.get('customer_id', ''),
                risk_level=AlertRiskLevel.LOW,
                score=np.random.uniform(15, 35),
                risk_factors=['Minor pattern detected'],
                transaction_ids=transaction_ids,
                triggering_signals={},
                alert_type=rule['alert_type'],
                description=rule['description'],
                status=AlertStatus.NEW,
                _true_positive=False,
                _scenario_id=None,
                _typology=None,
            )
            
            fp_alerts.append(alert.to_dict())
        
        return fp_alerts
    
    def get_alert_statistics(self, alerts: List[Dict]) -> Dict[str, Any]:
        """Get statistics about generated alerts."""
        if not alerts:
            return {'total': 0}
        
        risk_counts = Counter(a.get('risk_level', 'low') for a in alerts)
        rule_counts = Counter(a.get('rule_id', '') for a in alerts)
        type_counts = Counter(a.get('alert_type', '') for a in alerts)
        
        total = len(alerts)
        
        return {
            'total': total,
            'by_risk_level': {
                'low': risk_counts.get('low', 0),
                'medium': risk_counts.get('medium', 0),
                'high': risk_counts.get('high', 0),
                'critical': risk_counts.get('critical', 0),
            },
            'by_risk_level_pct': {
                'low': risk_counts.get('low', 0) / total * 100,
                'medium': risk_counts.get('medium', 0) / total * 100,
                'high': risk_counts.get('high', 0) / total * 100,
                'critical': risk_counts.get('critical', 0) / total * 100,
            },
            'by_rule': dict(rule_counts),
            'by_type': dict(type_counts),
            'true_positives': sum(1 for a in alerts if a.get('_true_positive')),
            'false_positives': sum(1 for a in alerts if not a.get('_true_positive')),
        }
