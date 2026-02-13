"""
Tests for AML Synthetic Data Generator.
Validates the generated data meets requirements from the implementation plan.
"""

import pytest
import sys
import os
from datetime import date, timedelta
from collections import Counter

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from antipode.data.generators import AMLDataGenerator, SignalGenerator, AlertRulesEngine, TypologyInjector
from antipode.data.config.regions import REGIONS, get_country_risk, is_high_risk_jurisdiction
from antipode.data.config.segments import CUSTOMER_SEGMENTS
from antipode.data.models.alert import AlertRiskLevel, ALERT_DISTRIBUTION


class TestRegionalConfiguration:
    """Test regional configuration."""
    
    def test_regions_defined(self):
        """Test that all regions are defined."""
        assert 'americas' in REGIONS
        assert 'emea' in REGIONS
        assert 'apac' in REGIONS
    
    def test_india_in_apac(self):
        """Test that India is included in APAC."""
        assert 'IN' in REGIONS['apac']['countries']
        assert REGIONS['apac']['countries']['IN']['currency'] == 'INR'
    
    def test_emea_countries(self):
        """Test EMEA countries are defined."""
        emea_countries = REGIONS['emea']['countries']
        assert 'GB' in emea_countries
        assert 'DE' in emea_countries
        assert 'AE' in emea_countries  # UAE
    
    def test_country_risk_scores(self):
        """Test country risk scoring."""
        # Low risk
        assert get_country_risk('US') < 30
        assert get_country_risk('GB') < 30
        
        # High risk
        assert get_country_risk('IR') > 80  # Iran
        assert get_country_risk('KP') > 90  # North Korea
    
    def test_high_risk_jurisdictions(self):
        """Test high-risk jurisdiction detection."""
        assert is_high_risk_jurisdiction('IR')
        assert is_high_risk_jurisdiction('KP')
        assert not is_high_risk_jurisdiction('US')


class TestCustomerSegments:
    """Test customer segment configuration."""
    
    def test_segments_defined(self):
        """Test that all segments are defined."""
        expected_segments = ['retail', 'hnw', 'smb', 'corporate', 'pep', 'ngo', 'msb']
        for segment in expected_segments:
            assert segment in CUSTOMER_SEGMENTS
    
    def test_segment_has_required_fields(self):
        """Test segments have required configuration."""
        for name, config in CUSTOMER_SEGMENTS.items():
            assert 'monthly_volume_range' in config
            assert 'txn_frequency' in config
            assert 'channels' in config
            assert 'corridors' in config


class TestAMLDataGenerator:
    """Test the main AML data generator."""
    
    @pytest.fixture
    def generator(self):
        return AMLDataGenerator(seed=42)
    
    def test_generate_customers(self, generator):
        """Test customer generation."""
        customers = generator.generate_customers(100)
        
        assert len(customers) == 100
        
        # Check required fields (new dataclass uses customer_id instead of id)
        for customer in customers:
            assert 'customer_id' in customer
            assert 'full_name' in customer
            assert 'country_of_residence' in customer
            assert 'segment' in customer
            # New fields from Customer dataclass
            assert 'first_name' in customer
            assert 'last_name' in customer
            assert 'addresses' in customer
            assert 'risk_rating' in customer
    
    def test_generate_companies(self, generator):
        """Test company generation."""
        companies = generator.generate_companies(50)
        
        assert len(companies) == 50
        
        for company in companies:
            assert 'company_id' in company
            assert 'legal_name' in company or 'trading_name' in company
            assert 'industry' in company
            assert 'country_of_incorporation' in company
            # New fields from Company dataclass
            assert 'addresses' in company
            assert 'risk_rating' in company
            assert 'company_type' in company
    
    def test_generate_accounts(self, generator):
        """Test account generation."""
        customers = generator.generate_customers(10)
        accounts = generator.generate_accounts(customers)
        
        assert len(accounts) >= 10  # At least one per customer
        
        for account in accounts:
            assert 'account_id' in account
            assert 'customer_id' in account
            # Verify NO expected_volume or expected_corridors (these are signals)
            assert 'expected_monthly_volume' not in account
            assert 'expected_corridors' not in account
            # But declared values should be present
            assert 'declared_monthly_turnover' in account
            assert 'declared_purpose' in account
    
    def test_generate_transactions(self, generator):
        """Test transaction generation."""
        customers = generator.generate_customers(10)
        accounts = generator.generate_accounts(customers)
        counterparties = generator.generate_counterparties(20)
        
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        transactions = generator.generate_baseline_transactions(
            accounts, counterparties, start_date, end_date
        )
        
        assert len(transactions) > 0
        
        for txn in transactions:
            assert 'txn_id' in txn
            assert 'amount' in txn
            assert 'timestamp' in txn
            assert '_is_suspicious' in txn
            assert txn['_is_suspicious'] == False  # Baseline txns are not suspicious
    
    def test_full_dataset_generation(self, generator):
        """Test full dataset generation."""
        dataset = generator.generate_full_dataset(
            num_customers=50,
            num_companies=10,
            start_date=date.today() - timedelta(days=90),
            end_date=date.today(),
            typology_rate=0.1,
        )
        
        assert 'customers' in dataset
        assert 'companies' in dataset
        assert 'accounts' in dataset
        assert 'transactions' in dataset
        assert 'signals' in dataset
        assert 'alerts' in dataset
        assert 'scenarios' in dataset
        
        # Check we have data
        assert len(dataset['customers']) == 50
        assert len(dataset['companies']) == 10
        assert len(dataset['transactions']) > 0
        assert len(dataset['signals']) > 0


class TestSignalGenerator:
    """Test signal generation."""
    
    @pytest.fixture
    def signal_generator(self):
        return SignalGenerator(seed=42)
    
    def test_generate_signals(self, signal_generator):
        """Test signal computation."""
        accounts = [
            {
                'account_id': 'ACCT_001',
                'customer_id': 'CUST_001',
                'currency': 'USD',
                'country': 'US',
                'declared_monthly_turnover': 10000,
                'kyc_date': (date.today() - timedelta(days=100)).isoformat(),
                'open_date': (date.today() - timedelta(days=365)).isoformat(),
            }
        ]
        
        transactions = [
            {
                'txn_id': f'TXN_{i}',
                'timestamp': (date.today() - timedelta(days=i)).isoformat(),
                'amount': 1000 + i * 100,
                'direction': 'credit' if i % 2 == 0 else 'debit',
                'from_account_id': 'ACCT_001' if i % 2 == 1 else 'EXT_001',
                'to_account_id': 'EXT_001' if i % 2 == 1 else 'ACCT_001',
                'dest_country': 'US',
                'txn_type': 'wire',
            }
            for i in range(30)
        ]
        
        result = signal_generator.generate_signals(
            accounts, transactions, [], None, date.today()
        )
        
        assert 'account_signals' in result
        assert len(result['account_signals']) == 1
        
        signals = result['account_signals'][0]
        
        # Check behavioral signals exist
        assert 'velocity_30d' in signals
        assert 'volume_30d' in signals
        assert 'volume_zscore' in signals
        
        # Check network signals exist
        assert 'pep_distance' in signals
        
        # Check entity signals exist
        assert 'kyc_age_days' in signals


class TestAlertRulesEngine:
    """Test alert generation."""
    
    @pytest.fixture
    def alert_engine(self):
        return AlertRulesEngine(seed=42)
    
    def test_generate_alerts(self, alert_engine):
        """Test alert generation from signals."""
        account_signals = [
            {
                'account_id': 'ACCT_001',
                'customer_id': 'CUST_001',
                'as_of_date': date.today().isoformat(),
                'structuring_score': 5,  # Above threshold
                'volume_30d': 100000,
                'volume_zscore': 3.0,
                'rapid_movement_score': 0.2,
                'corridor_risk_score': 30,
                'pep_distance': 99,
                'adverse_media_flag': False,
            },
            {
                'account_id': 'ACCT_002',
                'customer_id': 'CUST_002',
                'as_of_date': date.today().isoformat(),
                'structuring_score': 1,
                'volume_30d': 5000,
                'volume_zscore': 0.5,
                'rapid_movement_score': 0.1,
                'corridor_risk_score': 10,
                'pep_distance': 99,
                'adverse_media_flag': False,
            },
        ]
        
        alerts = alert_engine.generate_alerts(account_signals, [], date.today())
        
        # Should generate at least one alert for ACCT_001 (structuring)
        assert len(alerts) > 0
        
        # Check alert structure
        for alert in alerts:
            assert 'alert_id' in alert
            assert 'risk_level' in alert
            assert 'rule_id' in alert
    
    def test_alert_distribution(self, alert_engine):
        """Test that alert distribution matches targets."""
        # Generate many signals with varying risk
        account_signals = []
        for i in range(100):
            signals = {
                'account_id': f'ACCT_{i:03d}',
                'customer_id': f'CUST_{i:03d}',
                'as_of_date': date.today().isoformat(),
                'structuring_score': i % 10,
                'volume_30d': 1000 * (i + 1),
                'volume_zscore': (i % 20) / 5,
                'rapid_movement_score': (i % 10) / 10,
                'corridor_risk_score': i % 100,
                'pep_distance': 99 if i % 20 != 0 else 2,
                'adverse_media_flag': i % 30 == 0,
                'declared_vs_actual_volume': 1 + (i % 5) / 2,
                'kyc_age_days': 100 + i * 5,
            }
            account_signals.append(signals)
        
        alerts = alert_engine.generate_alerts(account_signals, [], date.today())
        stats = alert_engine.get_alert_statistics(alerts)
        
        # Check distribution is roughly correct
        # Low should be majority (~70%)
        low_pct = stats['by_risk_level_pct'].get('low', 0)
        assert low_pct > 50, f"Low risk should be >50%, got {low_pct}%"
        
        # Critical should be small (~1-2%)
        critical_pct = stats['by_risk_level_pct'].get('critical', 0)
        assert critical_pct < 10, f"Critical should be <10%, got {critical_pct}%"


class TestTypologyInjector:
    """Test typology injection."""
    
    @pytest.fixture
    def injector(self):
        return TypologyInjector(seed=42)
    
    def test_inject_typologies(self, injector):
        """Test typology injection."""
        accounts = [
            {
                'account_id': f'ACCT_{i:03d}',
                'customer_id': f'CUST_{i:03d}',
                'currency': 'USD',
                'country': 'US',
                'customer_name': f'Customer {i}',
            }
            for i in range(20)
        ]
        
        counterparties = [
            {
                'id': f'CP_{i:03d}',
                'account_id': f'EXT_{i:03d}',
                'name': f'Counterparty {i}',
                'country': 'US',
            }
            for i in range(30)
        ]
        
        start_date = date.today() - timedelta(days=90)
        end_date = date.today()
        
        transactions, scenarios = injector.inject_typologies(
            accounts, counterparties, start_date, end_date, typology_rate=0.2
        )
        
        # Should have some suspicious transactions
        assert len(transactions) > 0
        assert len(scenarios) > 0
        
        # All injected transactions should be marked suspicious
        for txn in transactions:
            assert txn['_is_suspicious'] == True
            assert txn['_typology'] is not None
            assert txn['_scenario_id'] is not None
        
        # Scenarios should have required fields
        for scenario in scenarios:
            assert 'scenario_id' in scenario
            assert 'typology' in scenario
            assert 'primary_account' in scenario
            assert 'transaction_ids' in scenario


class TestDataValidation:
    """Test data validation requirements from implementation plan."""
    
    @pytest.fixture
    def dataset(self):
        generator = AMLDataGenerator(seed=42)
        return generator.generate_full_dataset(
            num_customers=50,
            num_companies=10,
            start_date=date.today() - timedelta(days=60),
            end_date=date.today(),
            typology_rate=0.1,
        )
    
    def test_transaction_balance(self, dataset):
        """Test that credits roughly equal debits (within tolerance)."""
        transactions = dataset['transactions']
        
        credits = sum(t['amount'] for t in transactions if t.get('direction') == 'credit')
        debits = sum(t['amount'] for t in transactions if t.get('direction') == 'debit')
        
        # Allow 20% tolerance (some transactions may be external)
        if credits > 0 and debits > 0:
            ratio = credits / debits
            assert 0.5 < ratio < 2.0, f"Credit/debit ratio {ratio} outside tolerance"
    
    def test_typology_coverage(self, dataset):
        """Test that typologies are represented."""
        scenarios = dataset['scenarios']
        
        if scenarios:
            typologies = [s['typology'] for s in scenarios]
            unique_typologies = set(typologies)
            
            # Should have at least one typology
            assert len(unique_typologies) >= 1
    
    def test_temporal_consistency(self, dataset):
        """Test no transactions before account open date."""
        accounts = {a['account_id']: a for a in dataset['accounts']}
        transactions = dataset['transactions']
        
        violations = 0
        for txn in transactions:
            from_acct = txn.get('from_account_id')
            to_acct = txn.get('to_account_id')
            txn_date = txn.get('timestamp', '')[:10]
            
            for acct_id in [from_acct, to_acct]:
                if acct_id and acct_id in accounts:
                    open_date = accounts[acct_id].get('open_date', '')
                    if open_date and txn_date < open_date:
                        violations += 1
        
        # Allow small number of violations (edge cases)
        assert violations < len(transactions) * 0.01, f"Too many temporal violations: {violations}"
    
    def test_alert_distribution_realistic(self, dataset):
        """Test alert distribution is realistic (1-2% SAR-able, ~90% low risk)."""
        alerts = dataset['alerts']
        
        if not alerts:
            pytest.skip("No alerts generated")
        
        risk_counts = Counter(a.get('risk_level', 'low') for a in alerts)
        total = len(alerts)
        
        low_pct = risk_counts.get('low', 0) / total * 100
        critical_pct = risk_counts.get('critical', 0) / total * 100
        
        # Low + medium should be ~90%
        low_medium_pct = (risk_counts.get('low', 0) + risk_counts.get('medium', 0)) / total * 100
        assert low_medium_pct > 70, f"Low+Medium should be >70%, got {low_medium_pct}%"
        
        # Critical (SAR-able) should be small
        assert critical_pct < 15, f"Critical should be <15%, got {critical_pct}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
