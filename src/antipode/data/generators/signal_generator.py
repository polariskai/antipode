"""
Signal generator for synthetic data.
Computes derived signals from raw event data (transactions, news, graph).
"""

import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict

from ..signals.definitions import SIGNAL_DEFINITIONS
from ..config.regions import get_country_risk, is_high_risk_jurisdiction


class SignalGenerator:
    """
    Generate signals from raw event data.
    
    This simulates what analysis models (rule-based or ML) would produce.
    Signals are DERIVED data, not raw events.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, seed: int = 42):
        self.config = config or {}
        np.random.seed(seed)
        
        # Add noise to signals to simulate model imperfection
        self.signal_noise_std = self.config.get('signal_noise_std', 0.05)
        
        # Reporting thresholds by currency
        self.reporting_thresholds = {
            'USD': 10000,
            'EUR': 10000,
            'GBP': 10000,
            'INR': 1000000,  # 10 lakh
            'CAD': 10000,
            'AUD': 10000,
            'SGD': 20000,
            'HKD': 120000,
        }
    
    def generate_signals(
        self,
        accounts: List[Dict],
        transactions: List[Dict],
        news_events: List[Dict],
        graph_data: Optional[Dict] = None,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, List[Dict]]:
        """
        Generate all signals for all accounts as of a given date.
        
        Args:
            accounts: List of account dictionaries
            transactions: List of transaction dictionaries
            news_events: List of news event dictionaries
            graph_data: Optional graph metrics (pre-computed)
            as_of_date: Date to compute signals as of
            
        Returns:
            Dict with account_signals list
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        as_of_datetime = datetime.combine(as_of_date, datetime.max.time())
        
        # Build transaction index by account
        txns_by_account = self._index_transactions_by_account(transactions)
        
        # Build news index by entity
        news_by_entity = self._index_news_by_entity(news_events)
        
        # Build customer to accounts mapping
        customer_accounts = defaultdict(list)
        for account in accounts:
            customer_accounts[account.get('customer_id', '')].append(account)
        
        account_signals = []
        
        for account in accounts:
            account_id = account.get('account_id', '')
            customer_id = account.get('customer_id', '')
            
            # Get transactions for this account
            account_txns = txns_by_account.get(account_id, [])
            
            # Filter to transactions before as_of_date
            account_txns = [
                t for t in account_txns 
                if self._parse_timestamp(t.get('timestamp')) <= as_of_datetime
            ]
            
            # Compute behavioral signals
            behavioral = self._compute_behavioral_signals(account, account_txns, as_of_date)
            
            # Compute network signals
            network = self._compute_network_signals(account, graph_data)
            
            # Compute entity signals
            entity = self._compute_entity_signals(
                account, customer_id, account_txns, news_by_entity
            )
            
            signals = {
                'account_id': account_id,
                'customer_id': customer_id,
                'as_of_date': as_of_date.isoformat(),
                **behavioral,
                **network,
                **entity,
            }
            
            # Add noise to numeric signals
            signals = self._add_signal_noise(signals)
            
            account_signals.append(signals)
        
        return {'account_signals': account_signals}
    
    def _compute_behavioral_signals(
        self,
        account: Dict,
        transactions: List[Dict],
        as_of_date: date
    ) -> Dict[str, Any]:
        """Compute behavioral signals from transaction history.
        
        Also tracks contributing transaction IDs for each signal.
        """
        signals = {}
        contributing_txns = {}  # Maps signal name to list of transaction IDs
        
        # Time windows
        now = datetime.combine(as_of_date, datetime.max.time())
        days_30_ago = now - timedelta(days=30)
        days_90_ago = now - timedelta(days=90)
        
        # Filter transactions by time window
        txns_30d = [t for t in transactions if self._parse_timestamp(t.get('timestamp')) >= days_30_ago]
        txns_90d = [t for t in transactions if self._parse_timestamp(t.get('timestamp')) >= days_90_ago]
        
        # Velocity (transaction count)
        signals['velocity_30d'] = len(txns_30d)
        contributing_txns['velocity_30d'] = [t.get('txn_id') for t in txns_30d if t.get('txn_id')]
        
        # Volume
        signals['volume_30d'] = sum(t.get('amount', 0) for t in txns_30d)
        signals['volume_90d'] = sum(t.get('amount', 0) for t in txns_90d)
        contributing_txns['volume_30d'] = [t.get('txn_id') for t in txns_30d if t.get('txn_id')]
        contributing_txns['volume_90d'] = [t.get('txn_id') for t in txns_90d if t.get('txn_id')]
        
        # Volume z-score (compare current month to historical)
        monthly_volumes = self._compute_monthly_volumes(transactions, as_of_date)
        if len(monthly_volumes) > 2:
            current_month_vol = monthly_volumes[-1] if monthly_volumes else 0
            historical_mean = np.mean(monthly_volumes[:-1])
            historical_std = np.std(monthly_volumes[:-1])
            if historical_std > 0:
                signals['volume_zscore'] = (current_month_vol - historical_mean) / historical_std
            else:
                signals['volume_zscore'] = 0
        else:
            signals['volume_zscore'] = 0
        
        # In/out ratio
        credits = sum(t.get('amount', 0) for t in txns_30d if t.get('direction') == 'credit')
        debits = sum(t.get('amount', 0) for t in txns_30d if t.get('direction') == 'debit')
        signals['in_out_ratio'] = credits / debits if debits > 0 else 0
        
        # Rapid movement score
        signals['rapid_movement_score'] = self._compute_rapid_movement_score(txns_30d)
        
        # Structuring score
        currency = account.get('currency', 'USD')
        threshold = self.reporting_thresholds.get(currency, 10000)
        structuring_result = self._compute_structuring_score(txns_30d, threshold)
        signals['structuring_score'] = structuring_result['score']
        contributing_txns['structuring_score'] = structuring_result['txn_ids']
        
        # Counterparty concentration (HHI)
        signals['counterparty_concentration'] = self._compute_counterparty_hhi(txns_30d)
        
        # New counterparty rate
        signals['new_counterparty_rate'] = self._compute_new_counterparty_rate(transactions, as_of_date)
        
        # Corridor risk score
        corridor_result = self._compute_corridor_risk_score(txns_30d)
        signals['corridor_risk_score'] = corridor_result['score']
        contributing_txns['corridor_risk_score'] = corridor_result['txn_ids']
        
        # Cash intensity
        cash_txns = [t for t in txns_30d if t.get('txn_type') in ['cash_deposit', 'cash_withdrawal']]
        signals['cash_intensity'] = len(cash_txns) / len(txns_30d) if txns_30d else 0
        
        # Round amount ratio
        round_txns = [t for t in txns_30d if self._is_round_amount(t.get('amount', 0))]
        signals['round_amount_ratio'] = len(round_txns) / len(txns_30d) if txns_30d else 0
        contributing_txns['round_amount_ratio'] = [t.get('txn_id') for t in round_txns if t.get('txn_id')]
        
        # Add contributing transactions to signals
        signals['_contributing_txns'] = contributing_txns
        
        return signals
    
    def _compute_network_signals(
        self,
        account: Dict,
        graph_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """Compute network signals from graph data."""
        signals = {}
        
        if graph_data is None:
            # Generate synthetic network signals
            signals['degree_centrality'] = np.random.randint(1, 50)
            signals['betweenness_centrality'] = np.random.uniform(0, 0.1)
            signals['risk_flow_in'] = np.random.uniform(0, 50000)
            signals['risk_flow_out'] = np.random.uniform(0, 50000)
            signals['shared_attribute_score'] = np.random.randint(0, 5)
            signals['pep_distance'] = np.random.choice([1, 2, 3, 4, 5, 99], p=[0.01, 0.02, 0.05, 0.1, 0.2, 0.62])
            signals['sanctions_distance'] = np.random.choice([1, 2, 3, 99], p=[0.005, 0.01, 0.02, 0.965])
            signals['cluster_risk_score'] = np.random.uniform(10, 50)
        else:
            account_id = account.get('account_id', '')
            customer_id = account.get('customer_id', '')
            
            signals['degree_centrality'] = graph_data.get('degree', {}).get(account_id, 0)
            signals['betweenness_centrality'] = graph_data.get('betweenness', {}).get(account_id, 0)
            signals['risk_flow_in'] = graph_data.get('risk_flow_in', {}).get(account_id, 0)
            signals['risk_flow_out'] = graph_data.get('risk_flow_out', {}).get(account_id, 0)
            signals['shared_attribute_score'] = graph_data.get('shared_attrs', {}).get(customer_id, 0)
            signals['pep_distance'] = graph_data.get('pep_distance', {}).get(customer_id, 99)
            signals['sanctions_distance'] = graph_data.get('sanctions_distance', {}).get(customer_id, 99)
            signals['cluster_risk_score'] = graph_data.get('cluster_risk', {}).get(account_id, 0)
        
        return signals
    
    def _compute_entity_signals(
        self,
        account: Dict,
        customer_id: str,
        transactions: List[Dict],
        news_by_entity: Dict[str, List[Dict]]
    ) -> Dict[str, Any]:
        """Compute entity-level signals."""
        signals = {}
        
        # PEP and sanctions flags (from account data)
        signals['pep_flag'] = account.get('is_pep', False)
        signals['sanctions_flag'] = False  # Would come from screening
        
        # Adverse media
        customer_news = news_by_entity.get(customer_id, [])
        adverse_news = [n for n in customer_news if n.get('event_category') == 'adverse_media']
        signals['adverse_media_flag'] = len(adverse_news) > 0
        signals['adverse_media_count'] = len(adverse_news)
        
        if adverse_news:
            severities = [n.get('severity', 'neutral') for n in adverse_news]
            severity_order = {'positive': 0, 'neutral': 1, 'negative': 2, 'critical': 3}
            max_severity = max(severities, key=lambda s: severity_order.get(s, 1))
            signals['adverse_media_severity'] = max_severity
        else:
            signals['adverse_media_severity'] = 'none'
        
        # Jurisdiction risk
        country = account.get('country', 'US')
        signals['jurisdiction_risk'] = get_country_risk(country)
        
        # KYC age
        kyc_date = account.get('kyc_date')
        if kyc_date:
            if isinstance(kyc_date, str):
                kyc_date = date.fromisoformat(kyc_date)
            signals['kyc_age_days'] = (date.today() - kyc_date).days
        else:
            signals['kyc_age_days'] = 999
        
        # Account age
        open_date = account.get('open_date')
        if open_date:
            if isinstance(open_date, str):
                open_date = date.fromisoformat(open_date)
            signals['account_age_days'] = (date.today() - open_date).days
        else:
            signals['account_age_days'] = 0
        
        # Declared vs actual volume
        declared = account.get('declared_monthly_turnover', 0)
        if declared > 0 and transactions:
            # Compute actual monthly average
            monthly_volumes = self._compute_monthly_volumes(transactions, date.today())
            if monthly_volumes:
                actual_avg = np.mean(monthly_volumes)
                signals['declared_vs_actual_volume'] = actual_avg / declared
            else:
                signals['declared_vs_actual_volume'] = 0
        else:
            signals['declared_vs_actual_volume'] = 1.0  # Assume normal if no data
        
        # Dormancy
        if transactions:
            last_txn = max(transactions, key=lambda t: t.get('timestamp', ''))
            last_ts = self._parse_timestamp(last_txn.get('timestamp'))
            signals['dormancy_days'] = (datetime.now() - last_ts).days
        else:
            signals['dormancy_days'] = 999
        
        return signals
    
    def _compute_rapid_movement_score(self, transactions: List[Dict]) -> float:
        """Compute score for rapid in-out movement."""
        if len(transactions) < 2:
            return 0.0
        
        # Sort by timestamp
        sorted_txns = sorted(transactions, key=lambda t: t.get('timestamp', ''))
        
        rapid_pairs = 0
        total_amount = 0
        
        for i, txn in enumerate(sorted_txns):
            if txn.get('direction') == 'credit':
                # Look for matching debit within 48 hours
                credit_ts = self._parse_timestamp(txn.get('timestamp'))
                credit_amount = txn.get('amount', 0)
                
                for j in range(i + 1, len(sorted_txns)):
                    other = sorted_txns[j]
                    if other.get('direction') == 'debit':
                        other_ts = self._parse_timestamp(other.get('timestamp'))
                        other_amount = other.get('amount', 0)
                        
                        hours_diff = (other_ts - credit_ts).total_seconds() / 3600
                        
                        if hours_diff <= 48 and abs(other_amount - credit_amount) / max(credit_amount, 1) < 0.1:
                            rapid_pairs += 1
                            total_amount += credit_amount
                            break
        
        # Normalize score
        total_volume = sum(t.get('amount', 0) for t in transactions)
        if total_volume > 0:
            return min(1.0, total_amount / total_volume)
        return 0.0
    
    def _compute_structuring_score(self, transactions: List[Dict], threshold: float) -> Dict[str, Any]:
        """Count transactions near reporting threshold and return with transaction IDs."""
        margin = threshold * 0.1  # 10% below threshold
        near_threshold = [
            t for t in transactions 
            if threshold - margin < t.get('amount', 0) < threshold
        ]
        return {
            'score': len(near_threshold),
            'txn_ids': [t.get('txn_id') for t in near_threshold if t.get('txn_id')]
        }
    
    def _compute_counterparty_hhi(self, transactions: List[Dict]) -> float:
        """Compute Herfindahl-Hirschman Index for counterparty concentration."""
        if not transactions:
            return 0.0
        
        counterparty_amounts = defaultdict(float)
        total = 0
        
        for txn in transactions:
            cp = txn.get('counterparty_id') or txn.get('beneficiary_name_raw') or 'unknown'
            amount = txn.get('amount', 0)
            counterparty_amounts[cp] += amount
            total += amount
        
        if total == 0:
            return 0.0
        
        hhi = sum((amt / total) ** 2 for amt in counterparty_amounts.values())
        return hhi
    
    def _compute_new_counterparty_rate(self, transactions: List[Dict], as_of_date: date) -> float:
        """Compute rate of new counterparties in last 30 days."""
        if not transactions:
            return 0.0
        
        now = datetime.combine(as_of_date, datetime.max.time())
        days_30_ago = now - timedelta(days=30)
        
        all_counterparties: Set[str] = set()
        new_counterparties: Set[str] = set()
        
        sorted_txns = sorted(transactions, key=lambda t: t.get('timestamp', ''))
        
        for txn in sorted_txns:
            cp = txn.get('counterparty_id') or txn.get('beneficiary_name_raw') or 'unknown'
            txn_ts = self._parse_timestamp(txn.get('timestamp'))
            
            if txn_ts >= days_30_ago:
                if cp not in all_counterparties:
                    new_counterparties.add(cp)
            
            all_counterparties.add(cp)
        
        if not all_counterparties:
            return 0.0
        
        return len(new_counterparties) / len(all_counterparties)
    
    def _compute_corridor_risk_score(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Compute weighted corridor risk score and return with high-risk transaction IDs."""
        if not transactions:
            return {'score': 0.0, 'txn_ids': []}
        
        total_amount = 0
        weighted_risk = 0
        high_risk_txn_ids = []
        
        for txn in transactions:
            amount = txn.get('amount', 0)
            dest_country = txn.get('dest_country', '')
            
            if dest_country:
                risk = get_country_risk(dest_country)
                weighted_risk += amount * risk
                total_amount += amount
                
                # Track high-risk corridor transactions (risk > 50)
                if risk > 50 and txn.get('txn_id'):
                    high_risk_txn_ids.append(txn.get('txn_id'))
        
        if total_amount == 0:
            return {'score': 0.0, 'txn_ids': []}
        
        return {
            'score': weighted_risk / total_amount,
            'txn_ids': high_risk_txn_ids
        }
    
    def _compute_monthly_volumes(self, transactions: List[Dict], as_of_date: date) -> List[float]:
        """Compute monthly volumes for historical comparison."""
        if not transactions:
            return []
        
        monthly_volumes = defaultdict(float)
        
        for txn in transactions:
            ts = self._parse_timestamp(txn.get('timestamp'))
            month_key = (ts.year, ts.month)
            monthly_volumes[month_key] += txn.get('amount', 0)
        
        # Sort by month and return values
        sorted_months = sorted(monthly_volumes.keys())
        return [monthly_volumes[m] for m in sorted_months]
    
    def _is_round_amount(self, amount: float) -> bool:
        """Check if amount is a round number."""
        if amount <= 0:
            return False
        
        # Check if divisible by 100, 500, or 1000
        return (amount % 1000 == 0) or (amount % 500 == 0) or (amount % 100 == 0 and amount >= 1000)
    
    def _index_transactions_by_account(self, transactions: List[Dict]) -> Dict[str, List[Dict]]:
        """Index transactions by account ID."""
        index = defaultdict(list)
        for txn in transactions:
            from_acct = txn.get('from_account_id')
            to_acct = txn.get('to_account_id')
            if from_acct:
                index[from_acct].append(txn)
            if to_acct and to_acct != from_acct:
                index[to_acct].append(txn)
        return index
    
    def _index_news_by_entity(self, news_events: List[Dict]) -> Dict[str, List[Dict]]:
        """Index news events by entity ID."""
        index = defaultdict(list)
        for event in news_events:
            entity_id = event.get('entity_id')
            if entity_id:
                index[entity_id].append(event)
        return index
    
    def _parse_timestamp(self, ts: Any) -> datetime:
        """Parse timestamp to datetime."""
        if ts is None:
            return datetime.min
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, date):
            return datetime.combine(ts, datetime.min.time())
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except ValueError:
                return datetime.min
        return datetime.min
    
    def _add_signal_noise(self, signals: Dict) -> Dict:
        """Add realistic noise to signals (model imperfection)."""
        noisy_signals = signals.copy()
        
        for key, value in signals.items():
            if isinstance(value, (int, float)) and key not in ['account_id', 'customer_id', 'as_of_date']:
                if value != 0:
                    noise = np.random.normal(0, abs(value) * self.signal_noise_std)
                    noisy_signals[key] = value + noise
        
        return noisy_signals
