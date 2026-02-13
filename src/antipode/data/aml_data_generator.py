"""
AML Synthetic Data Generator

Integrated generator that produces realistic synthetic data for AML/Transaction Surveillance
with proper separation of concerns:
- Raw Events: Entities, Accounts, Transactions, News
- Signals: Derived features from analysis models
- Alerts: Generated from signal-based rules
- Cases: Investigation outcomes

Based on the implementation plan in docs/SYNTHETIC_DATA_IMPLEMENTATION_PLAN.md
"""

import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from uuid import uuid4
import json

from .config.regions import REGIONS, get_all_countries, get_country_risk, INDIA_CONFIG
from .config.segments import CUSTOMER_SEGMENTS, get_segment_config
from .models.account import Account, AccountType, AccountStatus
from .models.transaction import Transaction, TransactionType, TransactionDirection, TransactionChannel
from .models.news_event import NewsEvent, EVENT_CATEGORIES
from .models.news_generator import NewsEventGenerator
from .models.alert import Alert, AlertRiskLevel, ALERT_DISTRIBUTION
from .signals.generator import SignalGenerator
from .alerts.rules_engine import AlertRulesEngine
from .typologies.injector import TypologyInjector


class AMLDataGenerator:
    """
    Generate synthetic AML/Transaction Surveillance data.
    
    Produces:
    - Entities (customers, companies)
    - Accounts (with KYC-declared fields, NOT derived signals)
    - Transactions (raw events)
    - News/Corporate Events
    - Signals (derived from raw data)
    - Alerts (generated from signals)
    - Scenarios (ground truth for typologies)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, seed: int = 42):
        self.config = config or {}
        self.seed = seed
        np.random.seed(seed)
        
        # Initialize Faker for different locales
        self.fakers = self._init_fakers(seed)
        self.faker = self.fakers.get('en_US', Faker())
        
        # Initialize sub-generators
        self.news_generator = NewsEventGenerator(config, seed)
        self.signal_generator = SignalGenerator(config, seed)
        self.alert_engine = AlertRulesEngine(config, seed)
        self.typology_injector = TypologyInjector(config, seed)
        
        # Country weights from regions
        self.country_weights = self._build_country_weights()
    
    def _init_fakers(self, seed: int) -> Dict[str, Faker]:
        """Initialize Faker instances for different locales."""
        locales = [
            'en_US', 'en_GB', 'de_DE', 'fr_FR', 'en_CA', 'en_AU',
            'ja_JP', 'zh_CN', 'en_IN', 'pt_BR', 'es_MX', 'ar_AE',
            'nl_NL', 'de_CH',
        ]
        fakers = {}
        for locale in locales:
            try:
                fakers[locale] = Faker(locale)
                fakers[locale].seed_instance(seed)
            except Exception:
                pass
        return fakers
    
    def _build_country_weights(self) -> Dict[str, float]:
        """Build country weight distribution from regions."""
        weights = {}
        for region_data in REGIONS.values():
            for country, config in region_data['countries'].items():
                weights[country] = config['weight']
        
        # Normalize
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}
    
    def generate_full_dataset(
        self,
        num_customers: int = 1000,
        num_companies: int = 200,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        typology_rate: float = 0.05,
        adverse_media_rate: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Generate a complete synthetic dataset.
        
        Args:
            num_customers: Number of individual customers
            num_companies: Number of company entities
            start_date: Start of transaction date range
            end_date: End of transaction date range
            typology_rate: Fraction of accounts with suspicious patterns
            adverse_media_rate: Fraction of entities with adverse news
            
        Returns:
            Dictionary containing all generated data
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=365)
        if end_date is None:
            end_date = date.today()
        
        print(f"Generating synthetic AML data...")
        print(f"  Customers: {num_customers}")
        print(f"  Companies: {num_companies}")
        print(f"  Date range: {start_date} to {end_date}")
        
        # 1. Generate entities
        print("  [1/8] Generating entities...")
        customers = self.generate_customers(num_customers)
        companies = self.generate_companies(num_companies)
        all_entities = customers + companies
        
        # 2. Generate accounts
        print("  [2/8] Generating accounts...")
        accounts = self.generate_accounts(customers + companies)
        
        # 3. Generate counterparties (external entities)
        print("  [3/8] Generating counterparties...")
        counterparties = self.generate_counterparties(num_customers // 2)
        
        # 4. Generate baseline transactions
        print("  [4/8] Generating baseline transactions...")
        baseline_txns = self.generate_baseline_transactions(
            accounts, counterparties, start_date, end_date
        )
        
        # 5. Inject typologies (suspicious patterns)
        print("  [5/8] Injecting typologies...")
        suspicious_txns, scenarios = self.typology_injector.inject_typologies(
            accounts, counterparties, start_date, end_date, typology_rate
        )
        
        # Combine all transactions
        all_transactions = baseline_txns + suspicious_txns
        all_transactions.sort(key=lambda t: t.get('timestamp', ''))
        
        # 6. Generate news events
        print("  [6/8] Generating news events...")
        news_events = self.news_generator.generate_news_events(
            companies, customers, start_date, end_date, adverse_media_rate
        )
        
        # 7. Generate signals
        print("  [7/8] Computing signals...")
        signals_result = self.signal_generator.generate_signals(
            accounts, all_transactions, news_events, None, end_date
        )
        account_signals = signals_result['account_signals']
        
        # 8. Generate alerts
        print("  [8/8] Generating alerts...")
        alerts = self.alert_engine.generate_alerts(
            account_signals, scenarios, end_date
        )
        
        # Compute statistics
        alert_stats = self.alert_engine.get_alert_statistics(alerts)
        
        print(f"\nGeneration complete!")
        print(f"  Total transactions: {len(all_transactions)}")
        print(f"  Suspicious transactions: {len(suspicious_txns)}")
        print(f"  Scenarios: {len(scenarios)}")
        print(f"  News events: {len(news_events)}")
        print(f"  Alerts: {len(alerts)}")
        print(f"  Alert distribution: {alert_stats.get('by_risk_level_pct', {})}")
        
        return {
            'customers': customers,
            'companies': companies,
            'accounts': accounts,
            'counterparties': counterparties,
            'transactions': all_transactions,
            'news_events': news_events,
            'signals': account_signals,
            'alerts': alerts,
            'scenarios': scenarios,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'seed': self.seed,
                'num_customers': num_customers,
                'num_companies': num_companies,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'typology_rate': typology_rate,
                'adverse_media_rate': adverse_media_rate,
            },
            'statistics': {
                'total_transactions': len(all_transactions),
                'suspicious_transactions': len(suspicious_txns),
                'scenarios': len(scenarios),
                'alerts': alert_stats,
            },
        }
    
    def generate_customers(self, count: int) -> List[Dict]:
        """Generate individual customer entities."""
        customers = []
        
        countries = list(self.country_weights.keys())
        weights = list(self.country_weights.values())
        
        segments = list(CUSTOMER_SEGMENTS.keys())
        segment_weights = [0.6, 0.1, 0.15, 0.05, 0.02, 0.03, 0.02, 0.03]  # retail heavy
        
        for i in range(count):
            country = np.random.choice(countries, p=weights)
            segment = np.random.choice(segments, p=segment_weights)
            
            locale = REGIONS.get('americas', {}).get('countries', {}).get(country, {}).get('locale', 'en_US')
            faker = self.fakers.get(locale, self.faker)
            
            # PEP probability based on segment
            is_pep = segment == 'pep' or (segment == 'hnw' and np.random.random() < 0.05)
            
            customer = {
                'id': f"CUST_{i:08d}",
                'entity_type': 'person',
                'full_name': faker.name(),
                'first_name': faker.first_name(),
                'last_name': faker.last_name(),
                'date_of_birth': faker.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
                'nationality': country,
                'country_of_residence': country,
                'address': faker.address().replace('\n', ', '),
                'city': faker.city(),
                'postal_code': faker.postcode(),
                'email': faker.email(),
                'phone': faker.phone_number(),
                'segment': segment,
                'is_pep': is_pep,
                'pep_type': np.random.choice(['domestic', 'foreign', 'international_org']) if is_pep else None,
                'occupation': faker.job(),
                'employer': faker.company() if np.random.random() < 0.7 else None,
                'annual_income': self._generate_income(segment),
                'source_of_wealth': np.random.choice([
                    'employment', 'business', 'inheritance', 'investments', 'real_estate'
                ]),
                'onboarding_date': (date.today() - timedelta(days=np.random.randint(30, 3650))).isoformat(),
                'kyc_date': (date.today() - timedelta(days=np.random.randint(0, 365))).isoformat(),
                'risk_rating': self._assign_risk_rating(segment, country, is_pep),
            }
            customers.append(customer)
        
        return customers
    
    def generate_companies(self, count: int) -> List[Dict]:
        """Generate company entities."""
        companies = []
        
        countries = list(self.country_weights.keys())
        weights = list(self.country_weights.values())
        
        industries = [
            'Technology', 'Financial Services', 'Healthcare', 'Manufacturing',
            'Retail', 'Real Estate', 'Energy', 'Pharmaceuticals', 'Consulting',
            'Transportation', 'Telecommunications', 'Media', 'Agriculture',
        ]
        
        company_types = ['corporate', 'smb', 'ngo', 'msb']
        type_weights = [0.4, 0.4, 0.1, 0.1]
        
        for i in range(count):
            country = np.random.choice(countries, p=weights)
            company_type = np.random.choice(company_types, p=type_weights)
            industry = np.random.choice(industries)
            
            locale = REGIONS.get('americas', {}).get('countries', {}).get(country, {}).get('locale', 'en_US')
            faker = self.fakers.get(locale, self.faker)
            
            company = {
                'id': f"COMP_{i:08d}",
                'entity_type': 'company',
                'name': faker.company(),
                'legal_name': faker.company() + ' ' + np.random.choice(['Inc.', 'LLC', 'Ltd.', 'Corp.']),
                'industry': industry,
                'company_type': company_type,
                'country_of_incorporation': country,
                'country_of_operation': country,
                'address': faker.address().replace('\n', ', '),
                'city': faker.city(),
                'postal_code': faker.postcode(),
                'registration_number': faker.bothify('??######'),
                'tax_id': faker.bothify('##-#######'),
                'incorporation_date': faker.date_between(start_date='-30y', end_date='-1y').isoformat(),
                'employee_count': self._generate_employee_count(company_type),
                'annual_revenue': self._generate_revenue(company_type),
                'is_publicly_traded': company_type == 'corporate' and np.random.random() < 0.3,
                'stock_symbol': faker.bothify('????').upper() if np.random.random() < 0.2 else None,
                'onboarding_date': (date.today() - timedelta(days=np.random.randint(30, 1825))).isoformat(),
                'kyc_date': (date.today() - timedelta(days=np.random.randint(0, 365))).isoformat(),
                'risk_rating': self._assign_risk_rating(company_type, country, False),
            }
            companies.append(company)
        
        return companies
    
    def generate_accounts(self, entities: List[Dict]) -> List[Dict]:
        """
        Generate accounts for entities.
        
        Note: Accounts contain KYC-declared fields only.
        expected_volume and corridors are NOT stored - those are derived signals.
        """
        accounts = []
        
        for entity in entities:
            entity_type = entity.get('entity_type', 'person')
            segment = entity.get('segment', entity.get('company_type', 'retail'))
            country = entity.get('country_of_residence', entity.get('country_of_incorporation', 'US'))
            
            # Number of accounts per entity
            if segment in ['corporate', 'correspondent']:
                num_accounts = np.random.randint(2, 5)
            elif segment in ['hnw', 'smb']:
                num_accounts = np.random.randint(1, 4)
            else:
                num_accounts = np.random.randint(1, 3)
            
            segment_config = get_segment_config(segment)
            
            for j in range(num_accounts):
                # Select product type
                if entity_type == 'company':
                    product_type = np.random.choice([
                        AccountType.BUSINESS_CHECKING,
                        AccountType.BUSINESS_SAVINGS,
                        AccountType.TREASURY,
                    ], p=[0.6, 0.3, 0.1])
                else:
                    product_type = np.random.choice([
                        AccountType.CHECKING,
                        AccountType.SAVINGS,
                        AccountType.MONEY_MARKET,
                    ], p=[0.6, 0.3, 0.1])
                
                # Currency based on country
                currency = self._get_currency(country)
                
                # Open date
                onboarding = entity.get('onboarding_date')
                if onboarding:
                    open_date = date.fromisoformat(onboarding) + timedelta(days=np.random.randint(0, 30))
                else:
                    open_date = date.today() - timedelta(days=np.random.randint(30, 1825))
                
                # KYC-declared values (may differ from actual behavior)
                declared_turnover = np.random.uniform(*segment_config['monthly_volume_range'])
                
                account = Account(
                    account_id=f"ACCT_{len(accounts):08d}",
                    customer_id=entity['id'],
                    product_type=product_type,
                    currency=currency,
                    country=country,
                    branch=self._generate_branch(country),
                    open_date=open_date,
                    status=AccountStatus.ACTIVE,
                    channel_profile=segment_config['channels'],
                    declared_segment=segment,
                    declared_monthly_turnover=declared_turnover,
                    declared_purpose=self._generate_purpose(segment),
                    declared_source_of_funds=entity.get('source_of_wealth', 'business'),
                    is_pep=entity.get('is_pep', False),
                    is_high_risk=entity.get('risk_rating', 'low') in ['high', 'critical'],
                    kyc_date=date.fromisoformat(entity.get('kyc_date', date.today().isoformat())),
                    next_review_date=date.today() + timedelta(days=np.random.randint(30, 365)),
                )
                
                # Add customer name for reference
                account_dict = account.to_dict()
                account_dict['customer_name'] = entity.get('full_name', entity.get('name', ''))
                
                accounts.append(account_dict)
        
        return accounts
    
    def generate_counterparties(self, count: int) -> List[Dict]:
        """Generate external counterparty entities."""
        counterparties = []
        
        countries = list(self.country_weights.keys())
        weights = list(self.country_weights.values())
        
        for i in range(count):
            country = np.random.choice(countries, p=weights)
            
            locale = REGIONS.get('americas', {}).get('countries', {}).get(country, {}).get('locale', 'en_US')
            faker = self.fakers.get(locale, self.faker)
            
            is_company = np.random.random() < 0.6
            
            counterparty = {
                'id': f"CP_{i:08d}",
                'account_id': f"EXT_{i:08d}",
                'name': faker.company() if is_company else faker.name(),
                'type': 'company' if is_company else 'person',
                'country': country,
                'bank_name': faker.company() + ' Bank',
                'bank_country': country,
            }
            counterparties.append(counterparty)
        
        return counterparties
    
    def generate_baseline_transactions(
        self,
        accounts: List[Dict],
        counterparties: List[Dict],
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        """Generate normal (non-suspicious) baseline transactions."""
        transactions = []
        
        num_days = (end_date - start_date).days
        
        for account in accounts:
            segment = account.get('declared_segment', 'retail')
            segment_config = get_segment_config(segment)
            
            # Generate transactions for each day
            current_date = start_date
            while current_date <= end_date:
                # Skip if account not yet open
                open_date = account.get('open_date')
                if open_date:
                    if isinstance(open_date, str):
                        open_date = date.fromisoformat(open_date)
                    if current_date < open_date:
                        current_date += timedelta(days=1)
                        continue
                
                # Day-of-week effect
                dow = current_date.weekday()
                if dow >= 5:  # Weekend
                    dow_mult = 0.3
                else:
                    dow_mult = 1.0
                
                # Generate transactions based on frequency
                for txn_type, monthly_freq in segment_config['txn_frequency'].items():
                    daily_prob = (monthly_freq / 30) * dow_mult
                    
                    if np.random.random() < daily_prob:
                        txn = self._create_baseline_transaction(
                            account, txn_type, current_date, counterparties, segment_config
                        )
                        transactions.append(txn)
                
                current_date += timedelta(days=1)
        
        return transactions
    
    def _create_baseline_transaction(
        self,
        account: Dict,
        txn_type: str,
        txn_date: date,
        counterparties: List[Dict],
        segment_config: Dict,
    ) -> Dict:
        """Create a single baseline transaction."""
        # Amount based on segment
        min_amt, max_amt = segment_config['avg_txn_size']
        amount = np.random.uniform(min_amt, max_amt)
        
        # Direction based on transaction type
        if txn_type in ['salary', 'customer', 'donation_in', 'remittance_in']:
            direction = 'credit'
        elif txn_type in ['rent', 'utilities', 'shopping', 'supplier', 'payroll', 'tax']:
            direction = 'debit'
        else:
            direction = np.random.choice(['credit', 'debit'])
        
        # Channel
        channels = list(segment_config['channels'].keys())
        channel_weights = list(segment_config['channels'].values())
        channel = np.random.choice(channels, p=channel_weights)
        
        # Counterparty
        counterparty = np.random.choice(counterparties) if counterparties else {}
        
        # Corridor (domestic vs cross-border)
        corridors = segment_config['corridors']
        is_cross_border = np.random.random() > corridors.get('domestic', 0.9)
        
        if is_cross_border:
            dest_country = np.random.choice(list(self.country_weights.keys()))
        else:
            dest_country = account.get('country', 'US')
        
        # Transaction type mapping
        type_mapping = {
            'salary': TransactionType.ACH,
            'rent': TransactionType.ACH,
            'utilities': TransactionType.ACH,
            'shopping': TransactionType.CARD,
            'transfer': TransactionType.INTERNAL_TRANSFER,
            'wire': TransactionType.WIRE,
            'supplier': TransactionType.WIRE,
            'customer': TransactionType.WIRE,
            'payroll': TransactionType.ACH,
            'investment': TransactionType.WIRE,
            'fx': TransactionType.FX,
        }
        
        mapped_type = type_mapping.get(txn_type, TransactionType.WIRE)
        
        txn = {
            'txn_id': f"TXN_{uuid4().hex[:12]}",
            'timestamp': datetime.combine(txn_date, datetime.min.time().replace(
                hour=np.random.randint(8, 18),
                minute=np.random.randint(0, 60)
            )).isoformat(),
            'amount': round(amount, 2),
            'currency': account.get('currency', 'USD'),
            'txn_type': mapped_type.value if isinstance(mapped_type, TransactionType) else mapped_type,
            'direction': direction,
            'channel': channel,
            'from_account_id': account.get('account_id') if direction == 'debit' else counterparty.get('account_id'),
            'to_account_id': counterparty.get('account_id') if direction == 'debit' else account.get('account_id'),
            'counterparty_id': counterparty.get('id'),
            'originator_name_raw': account.get('customer_name', '') if direction == 'debit' else counterparty.get('name', ''),
            'beneficiary_name_raw': counterparty.get('name', '') if direction == 'debit' else account.get('customer_name', ''),
            'orig_country': account.get('country', 'US'),
            'dest_country': dest_country,
            'reference': f"REF{np.random.randint(100000, 999999)}",
            'purpose': txn_type,
            # Ground truth (not suspicious)
            '_is_suspicious': False,
            '_typology': None,
            '_scenario_id': None,
        }
        
        return txn
    
    def _generate_income(self, segment: str) -> float:
        """Generate annual income based on segment."""
        ranges = {
            'retail': (30000, 100000),
            'hnw': (500000, 10000000),
            'pep': (100000, 2000000),
        }
        min_inc, max_inc = ranges.get(segment, (30000, 100000))
        return round(np.random.uniform(min_inc, max_inc), 2)
    
    def _generate_employee_count(self, company_type: str) -> int:
        """Generate employee count based on company type."""
        ranges = {
            'smb': (5, 200),
            'corporate': (500, 50000),
            'ngo': (10, 500),
            'msb': (5, 100),
        }
        min_emp, max_emp = ranges.get(company_type, (10, 100))
        return np.random.randint(min_emp, max_emp)
    
    def _generate_revenue(self, company_type: str) -> float:
        """Generate annual revenue based on company type."""
        ranges = {
            'smb': (100000, 10000000),
            'corporate': (10000000, 10000000000),
            'ngo': (50000, 50000000),
            'msb': (500000, 100000000),
        }
        min_rev, max_rev = ranges.get(company_type, (100000, 10000000))
        return round(np.random.uniform(min_rev, max_rev), 2)
    
    def _assign_risk_rating(self, segment: str, country: str, is_pep: bool) -> str:
        """Assign risk rating based on factors."""
        country_risk = get_country_risk(country)
        
        if is_pep or country_risk > 70:
            return 'high'
        elif segment in ['msb', 'correspondent'] or country_risk > 50:
            return 'medium'
        elif country_risk > 30:
            return 'low'
        else:
            return 'low'
    
    def _get_currency(self, country: str) -> str:
        """Get currency for a country."""
        for region_data in REGIONS.values():
            if country in region_data['countries']:
                return region_data['countries'][country].get('currency', 'USD')
        return 'USD'
    
    def _generate_branch(self, country: str) -> str:
        """Generate branch code."""
        if country == 'IN':
            state = np.random.choice(INDIA_CONFIG['states'])
            cities = INDIA_CONFIG['cities_by_state'].get(state, ['Mumbai'])
            city = np.random.choice(cities)
            return f"{city}-{np.random.randint(1, 20):02d}"
        else:
            return f"BR-{np.random.randint(1, 100):03d}"
    
    def _generate_purpose(self, segment: str) -> str:
        """Generate declared account purpose."""
        purposes = {
            'retail': ['personal banking', 'savings', 'salary account'],
            'hnw': ['wealth management', 'investment', 'private banking'],
            'smb': ['business operations', 'payroll', 'vendor payments'],
            'corporate': ['treasury operations', 'trade finance', 'cash management'],
            'ngo': ['charitable operations', 'grant management', 'donations'],
            'msb': ['remittance services', 'currency exchange', 'money transfer'],
        }
        return np.random.choice(purposes.get(segment, ['general banking']))
    
    def save_dataset(self, dataset: Dict, output_dir: str) -> None:
        """Save dataset to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save each component
        for key, data in dataset.items():
            if isinstance(data, list) and data:
                # Save as JSON
                with open(output_path / f"{key}.json", 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                # Also save as CSV if it's a list of dicts
                if isinstance(data[0], dict):
                    df = pd.DataFrame(data)
                    df.to_csv(output_path / f"{key}.csv", index=False)
            elif isinstance(data, dict):
                with open(output_path / f"{key}.json", 'w') as f:
                    json.dump(data, f, indent=2, default=str)
        
        print(f"Dataset saved to {output_path}")


def generate_sample_dataset(
    output_dir: str = "data/synthetic",
    num_customers: int = 500,
    num_companies: int = 100,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Convenience function to generate and save a sample dataset.
    
    Args:
        output_dir: Directory to save output files
        num_customers: Number of customers to generate
        num_companies: Number of companies to generate
        seed: Random seed for reproducibility
        
    Returns:
        Generated dataset dictionary
    """
    generator = AMLDataGenerator(seed=seed)
    
    dataset = generator.generate_full_dataset(
        num_customers=num_customers,
        num_companies=num_companies,
        typology_rate=0.05,
        adverse_media_rate=0.05,
    )
    
    generator.save_dataset(dataset, output_dir)
    
    return dataset


if __name__ == "__main__":
    # Generate sample dataset when run directly
    dataset = generate_sample_dataset(
        output_dir="data/synthetic_aml",
        num_customers=500,
        num_companies=100,
    )
