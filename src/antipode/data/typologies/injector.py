"""
Typology injector for synthetic data generation.
Injects suspicious patterns into transaction data.
"""

import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4

from .definitions import TYPOLOGIES
from ..config.regions import HIGH_RISK_JURISDICTIONS, OFFSHORE_JURISDICTIONS


class TypologyInjector:
    """
    Inject suspicious transaction patterns (typologies) into synthetic data.
    
    The injector creates realistic money laundering patterns while maintaining
    hidden ground truth labels for model training.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, seed: int = 42):
        self.config = config or {}
        np.random.seed(seed)
        
        self.typologies = TYPOLOGIES
        
        # Reporting thresholds by currency
        self.reporting_thresholds = {
            'USD': 10000,
            'EUR': 10000,
            'GBP': 10000,
            'INR': 1000000,
            'CAD': 10000,
        }
    
    def inject_typologies(
        self,
        accounts: List[Dict],
        counterparties: List[Dict],
        start_date: date,
        end_date: date,
        typology_rate: float = 0.05,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Inject typology patterns into accounts.
        
        Args:
            accounts: List of account dictionaries
            counterparties: List of counterparty dictionaries
            start_date: Start of date range
            end_date: End of date range
            typology_rate: Fraction of accounts to inject typologies into
            
        Returns:
            Tuple of (transactions, scenarios)
        """
        all_transactions = []
        all_scenarios = []
        
        # Select accounts for typology injection
        num_suspicious = max(1, int(len(accounts) * typology_rate))
        suspicious_accounts = list(np.random.choice(
            accounts, size=min(num_suspicious, len(accounts)), replace=False
        ))
        
        # Distribute typologies based on prevalence
        typology_names = list(self.typologies.keys())
        prevalences = [self.typologies[t]['prevalence'] for t in typology_names]
        total_prevalence = sum(prevalences)
        probs = [p / total_prevalence for p in prevalences]
        
        for account in suspicious_accounts:
            # Select typology
            typology_name = np.random.choice(typology_names, p=probs)
            
            # Generate transactions for this typology
            txns, scenario = self._inject_typology(
                typology_name=typology_name,
                account=account,
                counterparties=counterparties,
                start_date=start_date,
                end_date=end_date,
            )
            
            all_transactions.extend(txns)
            all_scenarios.append(scenario)
        
        return all_transactions, all_scenarios
    
    def _inject_typology(
        self,
        typology_name: str,
        account: Dict,
        counterparties: List[Dict],
        start_date: date,
        end_date: date,
    ) -> Tuple[List[Dict], Dict]:
        """Inject a specific typology pattern."""
        typology = self.typologies[typology_name]
        
        # Dispatch to specific injector
        injector_map = {
            'structuring': self._inject_structuring,
            'rapid_movement': self._inject_rapid_movement,
            'fan_in': self._inject_fan_in,
            'fan_out': self._inject_fan_out,
            'cycle': self._inject_cycle,
            'mule': self._inject_mule,
            'high_risk_corridor': self._inject_high_risk_corridor,
            'cash_intensive': self._inject_cash_intensive,
        }
        
        injector = injector_map.get(typology_name, self._inject_generic)
        return injector(typology, account, counterparties, start_date, end_date)
    
    def _inject_structuring(
        self,
        typology: Dict,
        account: Dict,
        counterparties: List[Dict],
        start_date: date,
        end_date: date,
    ) -> Tuple[List[Dict], Dict]:
        """Inject structuring pattern (smurfing)."""
        params = typology['params']
        
        currency = account.get('currency', 'USD')
        threshold = self.reporting_thresholds.get(currency, 10000)
        margin = params['margin']
        
        num_txns = np.random.randint(*params['num_transactions'])
        timeframe = np.random.randint(*params['timeframe_days'])
        
        # Pick a random start date within range
        days_range = (end_date - start_date).days - timeframe
        if days_range <= 0:
            days_range = 1
        scenario_start = start_date + timedelta(days=np.random.randint(0, days_range))
        
        scenario_id = f"SCEN_{uuid4().hex[:12]}"
        txns = []
        
        # Total amount to structure
        total_amount = np.random.uniform(threshold * 3, threshold * 10)
        
        for i in range(num_txns):
            # Amount just below threshold
            amount = threshold - np.random.uniform(100, margin)
            
            txn_date = scenario_start + timedelta(
                days=np.random.randint(0, timeframe),
                hours=np.random.randint(9, 17)
            )
            
            txn = {
                'txn_id': f"TXN_{uuid4().hex[:12]}",
                'timestamp': txn_date.isoformat(),
                'amount': round(amount, 2),
                'currency': currency,
                'txn_type': 'cash_deposit',
                'direction': 'credit',
                'channel': np.random.choice(['branch', 'atm'], p=[0.7, 0.3]),
                'from_account_id': None,
                'to_account_id': account.get('account_id'),
                'counterparty_id': None,
                'originator_name_raw': 'CASH DEPOSIT',
                'beneficiary_name_raw': account.get('customer_name', ''),
                'orig_country': account.get('country', 'US'),
                'dest_country': account.get('country', 'US'),
                # Hidden ground truth
                '_is_suspicious': True,
                '_typology': 'structuring',
                '_scenario_id': scenario_id,
            }
            txns.append(txn)
        
        scenario = {
            'scenario_id': scenario_id,
            'typology': 'structuring',
            'primary_account': account.get('account_id'),
            'customer_id': account.get('customer_id'),
            'start_date': scenario_start.isoformat(),
            'end_date': (scenario_start + timedelta(days=timeframe)).isoformat(),
            'transaction_ids': [t['txn_id'] for t in txns],
            'total_amount': sum(t['amount'] for t in txns),
            'risk_level': typology['risk_level'],
        }
        
        return txns, scenario
    
    def _inject_rapid_movement(
        self,
        typology: Dict,
        account: Dict,
        counterparties: List[Dict],
        start_date: date,
        end_date: date,
    ) -> Tuple[List[Dict], Dict]:
        """Inject rapid movement pattern (layering)."""
        params = typology['params']
        
        scenario_id = f"SCEN_{uuid4().hex[:12]}"
        txns = []
        
        # Number of rapid in-out pairs
        num_hops = np.random.randint(*params['hops'])
        
        days_range = (end_date - start_date).days - 7
        if days_range <= 0:
            days_range = 1
        scenario_start = start_date + timedelta(days=np.random.randint(0, days_range))
        
        # Initial amount
        amount = np.random.uniform(20000, 200000)
        currency = account.get('currency', 'USD')
        
        for i in range(num_hops):
            # Incoming transaction
            in_date = scenario_start + timedelta(days=i, hours=np.random.randint(9, 14))
            
            in_cp = np.random.choice(counterparties) if counterparties else {}
            
            in_txn = {
                'txn_id': f"TXN_{uuid4().hex[:12]}",
                'timestamp': in_date.isoformat(),
                'amount': round(amount, 2),
                'currency': currency,
                'txn_type': 'wire',
                'direction': 'credit',
                'channel': 'online',
                'from_account_id': in_cp.get('account_id'),
                'to_account_id': account.get('account_id'),
                'counterparty_id': in_cp.get('id'),
                'originator_name_raw': in_cp.get('name', 'Unknown'),
                'beneficiary_name_raw': account.get('customer_name', ''),
                'orig_country': in_cp.get('country', 'US'),
                'dest_country': account.get('country', 'US'),
                '_is_suspicious': True,
                '_typology': 'rapid_movement',
                '_scenario_id': scenario_id,
            }
            txns.append(in_txn)
            
            # Outgoing transaction (within hours)
            velocity_hours = np.random.randint(*params['velocity_hours'])
            out_date = in_date + timedelta(hours=velocity_hours)
            
            retention = np.random.uniform(*params['amount_retention'])
            out_amount = amount * retention
            
            out_cp = np.random.choice(counterparties) if counterparties else {}
            
            out_txn = {
                'txn_id': f"TXN_{uuid4().hex[:12]}",
                'timestamp': out_date.isoformat(),
                'amount': round(out_amount, 2),
                'currency': currency,
                'txn_type': 'wire',
                'direction': 'debit',
                'channel': 'online',
                'from_account_id': account.get('account_id'),
                'to_account_id': out_cp.get('account_id'),
                'counterparty_id': out_cp.get('id'),
                'originator_name_raw': account.get('customer_name', ''),
                'beneficiary_name_raw': out_cp.get('name', 'Unknown'),
                'orig_country': account.get('country', 'US'),
                'dest_country': out_cp.get('country', 'US'),
                '_is_suspicious': True,
                '_typology': 'rapid_movement',
                '_scenario_id': scenario_id,
            }
            txns.append(out_txn)
            
            # Reduce amount for next hop
            amount = out_amount
        
        scenario = {
            'scenario_id': scenario_id,
            'typology': 'rapid_movement',
            'primary_account': account.get('account_id'),
            'customer_id': account.get('customer_id'),
            'start_date': scenario_start.isoformat(),
            'end_date': (scenario_start + timedelta(days=num_hops + 1)).isoformat(),
            'transaction_ids': [t['txn_id'] for t in txns],
            'total_amount': sum(t['amount'] for t in txns),
            'risk_level': typology['risk_level'],
        }
        
        return txns, scenario
    
    def _inject_fan_in(
        self,
        typology: Dict,
        account: Dict,
        counterparties: List[Dict],
        start_date: date,
        end_date: date,
    ) -> Tuple[List[Dict], Dict]:
        """Inject fan-in pattern (collection)."""
        params = typology['params']
        
        scenario_id = f"SCEN_{uuid4().hex[:12]}"
        txns = []
        
        num_sources = np.random.randint(*params['num_sources'])
        timeframe = np.random.randint(*params['timeframe_days'])
        
        days_range = (end_date - start_date).days - timeframe
        if days_range <= 0:
            days_range = 1
        scenario_start = start_date + timedelta(days=np.random.randint(0, days_range))
        
        base_amount = np.random.uniform(1000, 10000)
        currency = account.get('currency', 'USD')
        
        # Select sources
        sources = list(np.random.choice(
            counterparties, size=min(num_sources, len(counterparties)), replace=False
        )) if counterparties else []
        
        for source in sources:
            # Vary amount slightly
            variance = params['amount_variance']
            amount = base_amount * np.random.uniform(1 - variance, 1 + variance)
            
            txn_date = scenario_start + timedelta(
                days=np.random.randint(0, timeframe),
                hours=np.random.randint(9, 17)
            )
            
            txn = {
                'txn_id': f"TXN_{uuid4().hex[:12]}",
                'timestamp': txn_date.isoformat(),
                'amount': round(amount, 2),
                'currency': currency,
                'txn_type': 'wire',
                'direction': 'credit',
                'channel': 'online',
                'from_account_id': source.get('account_id'),
                'to_account_id': account.get('account_id'),
                'counterparty_id': source.get('id'),
                'originator_name_raw': source.get('name', 'Unknown'),
                'beneficiary_name_raw': account.get('customer_name', ''),
                'orig_country': source.get('country', 'US'),
                'dest_country': account.get('country', 'US'),
                '_is_suspicious': True,
                '_typology': 'fan_in',
                '_scenario_id': scenario_id,
            }
            txns.append(txn)
        
        scenario = {
            'scenario_id': scenario_id,
            'typology': 'fan_in',
            'primary_account': account.get('account_id'),
            'customer_id': account.get('customer_id'),
            'start_date': scenario_start.isoformat(),
            'end_date': (scenario_start + timedelta(days=timeframe)).isoformat(),
            'transaction_ids': [t['txn_id'] for t in txns],
            'total_amount': sum(t['amount'] for t in txns),
            'num_sources': len(sources),
            'risk_level': typology['risk_level'],
        }
        
        return txns, scenario
    
    def _inject_fan_out(
        self,
        typology: Dict,
        account: Dict,
        counterparties: List[Dict],
        start_date: date,
        end_date: date,
    ) -> Tuple[List[Dict], Dict]:
        """Inject fan-out pattern (distribution)."""
        params = typology['params']
        
        scenario_id = f"SCEN_{uuid4().hex[:12]}"
        txns = []
        
        num_destinations = np.random.randint(*params['num_destinations'])
        timeframe = np.random.randint(*params['timeframe_days'])
        
        days_range = (end_date - start_date).days - timeframe
        if days_range <= 0:
            days_range = 1
        scenario_start = start_date + timedelta(days=np.random.randint(0, days_range))
        
        base_amount = np.random.uniform(1000, 10000)
        currency = account.get('currency', 'USD')
        
        # Select destinations
        destinations = list(np.random.choice(
            counterparties, size=min(num_destinations, len(counterparties)), replace=False
        )) if counterparties else []
        
        for dest in destinations:
            variance = params['amount_variance']
            amount = base_amount * np.random.uniform(1 - variance, 1 + variance)
            
            txn_date = scenario_start + timedelta(
                days=np.random.randint(0, timeframe),
                hours=np.random.randint(9, 17)
            )
            
            txn = {
                'txn_id': f"TXN_{uuid4().hex[:12]}",
                'timestamp': txn_date.isoformat(),
                'amount': round(amount, 2),
                'currency': currency,
                'txn_type': 'wire',
                'direction': 'debit',
                'channel': 'online',
                'from_account_id': account.get('account_id'),
                'to_account_id': dest.get('account_id'),
                'counterparty_id': dest.get('id'),
                'originator_name_raw': account.get('customer_name', ''),
                'beneficiary_name_raw': dest.get('name', 'Unknown'),
                'orig_country': account.get('country', 'US'),
                'dest_country': dest.get('country', 'US'),
                '_is_suspicious': True,
                '_typology': 'fan_out',
                '_scenario_id': scenario_id,
            }
            txns.append(txn)
        
        scenario = {
            'scenario_id': scenario_id,
            'typology': 'fan_out',
            'primary_account': account.get('account_id'),
            'customer_id': account.get('customer_id'),
            'start_date': scenario_start.isoformat(),
            'end_date': (scenario_start + timedelta(days=timeframe)).isoformat(),
            'transaction_ids': [t['txn_id'] for t in txns],
            'total_amount': sum(t['amount'] for t in txns),
            'num_destinations': len(destinations),
            'risk_level': typology['risk_level'],
        }
        
        return txns, scenario
    
    def _inject_cycle(
        self,
        typology: Dict,
        account: Dict,
        counterparties: List[Dict],
        start_date: date,
        end_date: date,
    ) -> Tuple[List[Dict], Dict]:
        """Inject cycle pattern (round-tripping)."""
        params = typology['params']
        
        scenario_id = f"SCEN_{uuid4().hex[:12]}"
        txns = []
        
        cycle_length = np.random.randint(*params['cycle_length'])
        timeframe = np.random.randint(*params['timeframe_days'])
        
        days_range = (end_date - start_date).days - timeframe
        if days_range <= 0:
            days_range = 1
        scenario_start = start_date + timedelta(days=np.random.randint(0, days_range))
        
        amount = np.random.uniform(50000, 500000)
        currency = account.get('currency', 'USD')
        
        # Build cycle: account -> cp1 -> cp2 -> ... -> account
        cycle_participants = [account]
        if counterparties and len(counterparties) >= cycle_length - 1:
            cycle_cps = list(np.random.choice(
                counterparties, size=cycle_length - 1, replace=False
            ))
            cycle_participants.extend(cycle_cps)
        
        for i in range(len(cycle_participants)):
            sender = cycle_participants[i]
            receiver = cycle_participants[(i + 1) % len(cycle_participants)]
            
            txn_date = scenario_start + timedelta(
                days=i * (timeframe // cycle_length),
                hours=np.random.randint(9, 17)
            )
            
            # Apply decay
            decay = np.random.uniform(*params['amount_decay'])
            current_amount = amount * (decay ** i)
            
            txn = {
                'txn_id': f"TXN_{uuid4().hex[:12]}",
                'timestamp': txn_date.isoformat(),
                'amount': round(current_amount, 2),
                'currency': currency,
                'txn_type': 'wire',
                'direction': 'debit',
                'channel': 'online',
                'from_account_id': sender.get('account_id'),
                'to_account_id': receiver.get('account_id'),
                'counterparty_id': receiver.get('id'),
                'originator_name_raw': sender.get('name', sender.get('customer_name', '')),
                'beneficiary_name_raw': receiver.get('name', receiver.get('customer_name', '')),
                'orig_country': sender.get('country', 'US'),
                'dest_country': receiver.get('country', 'US'),
                '_is_suspicious': True,
                '_typology': 'cycle',
                '_scenario_id': scenario_id,
            }
            txns.append(txn)
        
        scenario = {
            'scenario_id': scenario_id,
            'typology': 'cycle',
            'primary_account': account.get('account_id'),
            'customer_id': account.get('customer_id'),
            'start_date': scenario_start.isoformat(),
            'end_date': (scenario_start + timedelta(days=timeframe)).isoformat(),
            'transaction_ids': [t['txn_id'] for t in txns],
            'total_amount': sum(t['amount'] for t in txns),
            'cycle_length': len(cycle_participants),
            'risk_level': typology['risk_level'],
        }
        
        return txns, scenario
    
    def _inject_mule(
        self,
        typology: Dict,
        account: Dict,
        counterparties: List[Dict],
        start_date: date,
        end_date: date,
    ) -> Tuple[List[Dict], Dict]:
        """Inject mule account pattern."""
        params = typology['params']
        
        scenario_id = f"SCEN_{uuid4().hex[:12]}"
        txns = []
        
        num_counterparties = np.random.randint(*params['num_counterparties'])
        
        days_range = (end_date - start_date).days - 30
        if days_range <= 0:
            days_range = 1
        scenario_start = start_date + timedelta(days=np.random.randint(0, days_range))
        
        currency = account.get('currency', 'USD')
        
        # Many incoming transactions
        sources = list(np.random.choice(
            counterparties, size=min(num_counterparties // 2, len(counterparties)), replace=True
        )) if counterparties else []
        
        for source in sources:
            amount = np.random.uniform(1000, 20000)
            txn_date = scenario_start + timedelta(
                days=np.random.randint(0, 30),
                hours=np.random.randint(0, 24)
            )
            
            txn = {
                'txn_id': f"TXN_{uuid4().hex[:12]}",
                'timestamp': txn_date.isoformat(),
                'amount': round(amount, 2),
                'currency': currency,
                'txn_type': 'wire',
                'direction': 'credit',
                'channel': 'online',
                'from_account_id': source.get('account_id'),
                'to_account_id': account.get('account_id'),
                'counterparty_id': source.get('id'),
                'originator_name_raw': source.get('name', 'Unknown'),
                'beneficiary_name_raw': account.get('customer_name', ''),
                'orig_country': source.get('country', 'US'),
                'dest_country': account.get('country', 'US'),
                '_is_suspicious': True,
                '_typology': 'mule',
                '_scenario_id': scenario_id,
            }
            txns.append(txn)
        
        # Cash withdrawals
        for _ in range(np.random.randint(5, 15)):
            amount = np.random.uniform(500, 5000)
            txn_date = scenario_start + timedelta(
                days=np.random.randint(0, 30),
                hours=np.random.randint(9, 21)
            )
            
            txn = {
                'txn_id': f"TXN_{uuid4().hex[:12]}",
                'timestamp': txn_date.isoformat(),
                'amount': round(amount, 2),
                'currency': currency,
                'txn_type': 'cash_withdrawal',
                'direction': 'debit',
                'channel': 'atm',
                'from_account_id': account.get('account_id'),
                'to_account_id': None,
                'counterparty_id': None,
                'originator_name_raw': account.get('customer_name', ''),
                'beneficiary_name_raw': 'CASH WITHDRAWAL',
                'orig_country': account.get('country', 'US'),
                'dest_country': account.get('country', 'US'),
                '_is_suspicious': True,
                '_typology': 'mule',
                '_scenario_id': scenario_id,
            }
            txns.append(txn)
        
        scenario = {
            'scenario_id': scenario_id,
            'typology': 'mule',
            'primary_account': account.get('account_id'),
            'customer_id': account.get('customer_id'),
            'start_date': scenario_start.isoformat(),
            'end_date': (scenario_start + timedelta(days=30)).isoformat(),
            'transaction_ids': [t['txn_id'] for t in txns],
            'total_amount': sum(t['amount'] for t in txns),
            'risk_level': typology['risk_level'],
        }
        
        return txns, scenario
    
    def _inject_high_risk_corridor(
        self,
        typology: Dict,
        account: Dict,
        counterparties: List[Dict],
        start_date: date,
        end_date: date,
    ) -> Tuple[List[Dict], Dict]:
        """Inject high-risk corridor pattern."""
        params = typology['params']
        
        scenario_id = f"SCEN_{uuid4().hex[:12]}"
        txns = []
        
        hr_jurisdictions = params['jurisdictions']
        
        days_range = (end_date - start_date).days - 14
        if days_range <= 0:
            days_range = 1
        scenario_start = start_date + timedelta(days=np.random.randint(0, days_range))
        
        currency = account.get('currency', 'USD')
        
        # Generate transactions to high-risk jurisdictions
        num_txns = np.random.randint(3, 10)
        
        for _ in range(num_txns):
            amount = np.random.uniform(10000, 100000)
            dest_country = np.random.choice(hr_jurisdictions)
            
            txn_date = scenario_start + timedelta(
                days=np.random.randint(0, 14),
                hours=np.random.randint(9, 17)
            )
            
            txn = {
                'txn_id': f"TXN_{uuid4().hex[:12]}",
                'timestamp': txn_date.isoformat(),
                'amount': round(amount, 2),
                'currency': currency,
                'txn_type': 'wire',
                'direction': 'debit',
                'channel': 'online',
                'from_account_id': account.get('account_id'),
                'to_account_id': None,
                'counterparty_id': None,
                'originator_name_raw': account.get('customer_name', ''),
                'beneficiary_name_raw': f"Entity in {dest_country}",
                'orig_country': account.get('country', 'US'),
                'dest_country': dest_country,
                '_is_suspicious': True,
                '_typology': 'high_risk_corridor',
                '_scenario_id': scenario_id,
            }
            txns.append(txn)
        
        scenario = {
            'scenario_id': scenario_id,
            'typology': 'high_risk_corridor',
            'primary_account': account.get('account_id'),
            'customer_id': account.get('customer_id'),
            'start_date': scenario_start.isoformat(),
            'end_date': (scenario_start + timedelta(days=14)).isoformat(),
            'transaction_ids': [t['txn_id'] for t in txns],
            'total_amount': sum(t['amount'] for t in txns),
            'jurisdictions': list(set(t['dest_country'] for t in txns)),
            'risk_level': typology['risk_level'],
        }
        
        return txns, scenario
    
    def _inject_cash_intensive(
        self,
        typology: Dict,
        account: Dict,
        counterparties: List[Dict],
        start_date: date,
        end_date: date,
    ) -> Tuple[List[Dict], Dict]:
        """Inject cash-intensive business pattern."""
        params = typology['params']
        
        scenario_id = f"SCEN_{uuid4().hex[:12]}"
        txns = []
        
        deposit_frequency = np.random.randint(*params['deposit_frequency'])
        
        days_range = (end_date - start_date).days - 30
        if days_range <= 0:
            days_range = 1
        scenario_start = start_date + timedelta(days=np.random.randint(0, days_range))
        
        currency = account.get('currency', 'USD')
        threshold = self.reporting_thresholds.get(currency, 10000)
        
        for _ in range(deposit_frequency):
            # Mix of just-below-threshold and smaller amounts
            if np.random.random() < 0.3:
                amount = threshold - np.random.uniform(100, 500)
            else:
                amount = np.random.uniform(500, 5000)
            
            # Round amounts are suspicious
            if np.random.random() < 0.5:
                amount = round(amount / 100) * 100
            
            txn_date = scenario_start + timedelta(
                days=np.random.randint(0, 30),
                hours=np.random.randint(9, 18)
            )
            
            txn = {
                'txn_id': f"TXN_{uuid4().hex[:12]}",
                'timestamp': txn_date.isoformat(),
                'amount': round(amount, 2),
                'currency': currency,
                'txn_type': 'cash_deposit',
                'direction': 'credit',
                'channel': np.random.choice(['branch', 'atm']),
                'from_account_id': None,
                'to_account_id': account.get('account_id'),
                'counterparty_id': None,
                'originator_name_raw': 'CASH DEPOSIT',
                'beneficiary_name_raw': account.get('customer_name', ''),
                'orig_country': account.get('country', 'US'),
                'dest_country': account.get('country', 'US'),
                '_is_suspicious': True,
                '_typology': 'cash_intensive',
                '_scenario_id': scenario_id,
            }
            txns.append(txn)
        
        scenario = {
            'scenario_id': scenario_id,
            'typology': 'cash_intensive',
            'primary_account': account.get('account_id'),
            'customer_id': account.get('customer_id'),
            'start_date': scenario_start.isoformat(),
            'end_date': (scenario_start + timedelta(days=30)).isoformat(),
            'transaction_ids': [t['txn_id'] for t in txns],
            'total_amount': sum(t['amount'] for t in txns),
            'risk_level': typology['risk_level'],
        }
        
        return txns, scenario
    
    def _inject_generic(
        self,
        typology: Dict,
        account: Dict,
        counterparties: List[Dict],
        start_date: date,
        end_date: date,
    ) -> Tuple[List[Dict], Dict]:
        """Generic typology injection for unimplemented patterns."""
        scenario_id = f"SCEN_{uuid4().hex[:12]}"
        
        # Generate a few suspicious transactions
        txns = []
        days_range = (end_date - start_date).days
        if days_range <= 0:
            days_range = 1
        
        for _ in range(np.random.randint(3, 8)):
            txn_date = start_date + timedelta(
                days=np.random.randint(0, days_range),
                hours=np.random.randint(9, 17)
            )
            
            txn = {
                'txn_id': f"TXN_{uuid4().hex[:12]}",
                'timestamp': txn_date.isoformat(),
                'amount': round(np.random.uniform(5000, 50000), 2),
                'currency': account.get('currency', 'USD'),
                'txn_type': 'wire',
                'direction': np.random.choice(['credit', 'debit']),
                'channel': 'online',
                'from_account_id': account.get('account_id'),
                'to_account_id': None,
                '_is_suspicious': True,
                '_typology': 'generic',
                '_scenario_id': scenario_id,
            }
            txns.append(txn)
        
        scenario = {
            'scenario_id': scenario_id,
            'typology': 'generic',
            'primary_account': account.get('account_id'),
            'customer_id': account.get('customer_id'),
            'transaction_ids': [t['txn_id'] for t in txns],
            'total_amount': sum(t['amount'] for t in txns),
            'risk_level': typology.get('risk_level', 'medium'),
        }
        
        return txns, scenario
