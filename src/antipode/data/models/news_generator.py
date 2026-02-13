"""
News and corporate event generator for synthetic data.
Generates realistic news events including adverse media, M&A, corporate actions, and clinical trials.
"""

import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4

from .news_event import (
    NewsEvent, EVENT_CATEGORIES, NEWS_SOURCES,
    EventSeverity, DisclosureStatus, SourceCredibility
)


class NewsEventGenerator:
    """Generate realistic news and corporate events."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, seed: int = 42):
        self.config = config or {}
        np.random.seed(seed)
        
        self.news_sources = NEWS_SOURCES
        
        # Headline templates by event type
        self.headline_templates = {
            # Adverse media
            "fraud_allegation": [
                "{entity} Faces Fraud Allegations in {jurisdiction}",
                "Fraud Investigation Launched Against {entity}",
                "{entity} Accused of Financial Fraud",
            ],
            "corruption_investigation": [
                "{entity} Under Investigation for Corruption",
                "DOJ Probes {entity} for Alleged Bribery",
                "{entity} Executives Face Corruption Charges",
            ],
            "sanctions_violation": [
                "{entity} Accused of Sanctions Violations",
                "OFAC Investigates {entity} for Sanctions Breach",
                "{entity} May Have Violated Iran Sanctions",
            ],
            "money_laundering": [
                "{entity} Linked to Money Laundering Probe",
                "AML Concerns Raised Over {entity} Transactions",
                "{entity} Under Investigation for Suspicious Transactions",
            ],
            "tax_evasion": [
                "{entity} Faces Tax Evasion Charges",
                "IRS Investigates {entity} for Tax Fraud",
                "{entity} Accused of Offshore Tax Schemes",
            ],
            "regulatory_action": [
                "Regulators Take Action Against {entity}",
                "{entity} Receives Regulatory Warning",
                "{entity} Fined by Financial Regulator",
            ],
            # Corporate actions
            "merger_announcement": [
                "{entity} Announces Merger with {target}",
                "{entity} to Merge with {target} in ${amount}B Deal",
                "{entity} and {target} Agree to Combine",
            ],
            "acquisition_announcement": [
                "{entity} to Acquire {target} for ${amount}B",
                "{entity} Announces Acquisition of {target}",
                "{target} Agrees to Be Acquired by {entity}",
            ],
            "earnings_beat": [
                "{entity} Beats Q{quarter} Earnings Expectations",
                "{entity} Reports Strong Q{quarter} Results",
                "{entity} Exceeds Analyst Estimates in Q{quarter}",
            ],
            "earnings_miss": [
                "{entity} Misses Q{quarter} Earnings Estimates",
                "{entity} Reports Disappointing Q{quarter} Results",
                "{entity} Falls Short of Q{quarter} Expectations",
            ],
            # Clinical trials
            "fda_approval": [
                "FDA Approves {entity}'s {drug} for {indication}",
                "{entity} Receives FDA Approval for {drug}",
                "{entity}'s {drug} Gets Green Light from FDA",
            ],
            "trial_results_positive": [
                "{entity}'s {drug} Shows Positive Phase {phase} Results",
                "{entity} Announces Successful Trial for {drug}",
                "{drug} Meets Primary Endpoints in Phase {phase} Trial",
            ],
            "trial_results_negative": [
                "{entity}'s {drug} Fails Phase {phase} Trial",
                "{entity} Reports Disappointing {drug} Trial Results",
                "{drug} Misses Primary Endpoints in Phase {phase}",
            ],
            # Leadership
            "ceo_change": [
                "{entity} Announces CEO Transition",
                "{entity} Names New Chief Executive",
                "{entity} CEO to Step Down",
            ],
            "executive_arrest": [
                "{entity} Executive Arrested on Fraud Charges",
                "Former {entity} CFO Indicted",
                "{entity} Executive Faces Criminal Charges",
            ],
        }
        
        # Drug names for clinical trials
        self.drug_prefixes = ["Ven", "Rem", "Pem", "Niv", "Ola", "Rib", "Pal", "Abi", "Enz"]
        self.drug_suffixes = ["mab", "nib", "tide", "zumab", "tinib", "ciclib", "parib"]
        self.indications = [
            "non-small cell lung cancer", "breast cancer", "melanoma",
            "rheumatoid arthritis", "multiple sclerosis", "Alzheimer's disease",
            "type 2 diabetes", "chronic kidney disease", "heart failure",
        ]
    
    def generate_news_events(
        self,
        companies: List[Dict],
        persons: List[Dict],
        start_date: date,
        end_date: date,
        adverse_event_rate: float = 0.05,
    ) -> List[Dict]:
        """
        Generate news events for entities.
        
        Args:
            companies: List of company entities
            persons: List of person entities
            start_date: Start of date range
            end_date: End of date range
            adverse_event_rate: Fraction of entities that get adverse news
            
        Returns:
            List of news event dictionaries
        """
        events = []
        
        # Corporate events (routine) for companies
        for company in companies:
            events.extend(self._generate_routine_corporate_events(company, start_date, end_date))
        
        # Adverse media (for subset of entities)
        adverse_entities = self._select_adverse_entities(companies, persons, adverse_event_rate)
        for entity in adverse_entities:
            events.extend(self._generate_adverse_events(entity, start_date, end_date))
        
        # Market-moving events (for trade surveillance)
        if self.config.get('include_market_events', True):
            events.extend(self._generate_market_events(companies, start_date, end_date))
        
        # Clinical trial events for pharma companies
        pharma_companies = [c for c in companies if c.get('industry') in ['Pharmaceuticals', 'Healthcare', 'Biotechnology']]
        for company in pharma_companies:
            if np.random.random() < 0.3:  # 30% of pharma companies have trial news
                events.extend(self._generate_clinical_trial_events(company, start_date, end_date))
        
        return sorted(events, key=lambda x: x.get('timestamp', datetime.min))
    
    def _select_adverse_entities(
        self,
        companies: List[Dict],
        persons: List[Dict],
        rate: float
    ) -> List[Dict]:
        """Select entities to receive adverse media."""
        all_entities = companies + persons
        num_adverse = max(1, int(len(all_entities) * rate))
        return list(np.random.choice(all_entities, size=min(num_adverse, len(all_entities)), replace=False))
    
    def _generate_routine_corporate_events(
        self,
        company: Dict,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Generate routine corporate events (earnings, etc.)."""
        events = []
        
        # Quarterly earnings
        for quarter_end in self._get_quarter_ends(start_date, end_date):
            if np.random.random() < 0.9:  # 90% report earnings
                event_type = np.random.choice(
                    ['earnings_beat', 'earnings_miss', 'earnings_announcement'],
                    p=[0.4, 0.3, 0.3]
                )
                
                quarter = self._get_quarter(quarter_end)
                headline = self._generate_headline(event_type, company, quarter=quarter)
                
                event = NewsEvent(
                    event_id=f"NEWS_{uuid4().hex[:12]}",
                    timestamp=datetime.combine(
                        quarter_end + timedelta(days=np.random.randint(15, 45)),
                        datetime.min.time()
                    ) + timedelta(hours=np.random.randint(6, 18)),
                    entity_id=company.get('id', company.get('entity_id', '')),
                    entity_type='company',
                    event_category='financial',
                    event_type=event_type,
                    severity=EventSeverity.NEUTRAL if event_type == 'earnings_beat' else EventSeverity.NEGATIVE,
                    headline=headline,
                    source=np.random.choice(self.news_sources['tier1']),
                    source_credibility=SourceCredibility.TIER1,
                    is_material=True,
                    disclosure_status=DisclosureStatus.ANNOUNCED,
                )
                events.append(event.to_dict())
        
        # M&A events (rare)
        if np.random.random() < 0.02:
            events.append(self._generate_ma_event(company, start_date, end_date))
        
        return events
    
    def _generate_adverse_events(
        self,
        entity: Dict,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Generate adverse media events for flagged entities."""
        events = []
        
        adverse_types = EVENT_CATEGORIES['adverse_media']['types']
        num_events = np.random.randint(1, 4)
        selected_types = np.random.choice(adverse_types, size=min(num_events, len(adverse_types)), replace=False)
        
        for event_type in selected_types:
            days_range = (end_date - start_date).days
            if days_range <= 0:
                days_range = 1
            event_date = start_date + timedelta(days=np.random.randint(0, days_range))
            
            entity_id = entity.get('id', entity.get('entity_id', ''))
            entity_type = 'company' if 'COMP' in str(entity_id) or entity.get('type') == 'company' else 'person'
            
            headline = self._generate_headline(event_type, entity)
            
            event = NewsEvent(
                event_id=f"NEWS_{uuid4().hex[:12]}",
                timestamp=datetime.combine(event_date, datetime.min.time()) + timedelta(hours=np.random.randint(6, 20)),
                entity_id=entity_id,
                entity_type=entity_type,
                event_category='adverse_media',
                event_type=event_type,
                severity=np.random.choice([EventSeverity.NEGATIVE, EventSeverity.CRITICAL], p=[0.7, 0.3]),
                headline=headline,
                source=np.random.choice(self.news_sources['tier1'] + self.news_sources['tier2']),
                source_credibility=np.random.choice([SourceCredibility.TIER1, SourceCredibility.TIER2]),
                is_material=event_type in ['fraud_allegation', 'regulatory_action', 'sanctions_violation'],
                disclosure_status=DisclosureStatus.ANNOUNCED,
                _is_synthetic_adverse=True,
            )
            events.append(event.to_dict())
        
        return events
    
    def _generate_market_events(
        self,
        companies: List[Dict],
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Generate market-moving events."""
        events = []
        
        # Select some companies for market events
        num_events = max(1, len(companies) // 20)  # ~5% of companies
        selected = np.random.choice(companies, size=min(num_events, len(companies)), replace=False)
        
        market_types = EVENT_CATEGORIES['market']['types']
        
        for company in selected:
            event_type = np.random.choice(market_types)
            days_range = (end_date - start_date).days
            if days_range <= 0:
                days_range = 1
            event_date = start_date + timedelta(days=np.random.randint(0, days_range))
            
            event = NewsEvent(
                event_id=f"NEWS_{uuid4().hex[:12]}",
                timestamp=datetime.combine(event_date, datetime.min.time()) + timedelta(hours=np.random.randint(9, 16)),
                entity_id=company.get('id', company.get('entity_id', '')),
                entity_type='company',
                event_category='market',
                event_type=event_type,
                severity=EventSeverity.NEUTRAL,
                headline=f"{company.get('name', 'Company')} Experiences {event_type.replace('_', ' ').title()}",
                source=np.random.choice(self.news_sources['tier1']),
                source_credibility=SourceCredibility.TIER1,
                is_material=event_type in ['trading_halt', 'price_spike', 'price_drop'],
                disclosure_status=DisclosureStatus.ANNOUNCED,
            )
            events.append(event.to_dict())
        
        return events
    
    def _generate_clinical_trial_events(
        self,
        company: Dict,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Generate clinical trial events for pharma companies."""
        events = []
        
        drug_name = np.random.choice(self.drug_prefixes) + np.random.choice(self.drug_suffixes)
        indication = np.random.choice(self.indications)
        phase = np.random.choice([1, 2, 3], p=[0.2, 0.4, 0.4])
        
        # Trial result
        result_type = np.random.choice(
            ['trial_results_positive', 'trial_results_negative', 'trial_results_mixed'],
            p=[0.4, 0.35, 0.25]
        )
        
        days_range = (end_date - start_date).days
        if days_range <= 0:
            days_range = 1
        event_date = start_date + timedelta(days=np.random.randint(0, days_range))
        
        headline = self._generate_headline(
            result_type, company, drug=drug_name, indication=indication, phase=phase
        )
        
        severity = EventSeverity.POSITIVE if 'positive' in result_type else (
            EventSeverity.NEGATIVE if 'negative' in result_type else EventSeverity.NEUTRAL
        )
        
        event = NewsEvent(
            event_id=f"NEWS_{uuid4().hex[:12]}",
            timestamp=datetime.combine(event_date, datetime.min.time()) + timedelta(hours=np.random.randint(6, 18)),
            entity_id=company.get('id', company.get('entity_id', '')),
            entity_type='company',
            event_category='clinical_trial',
            event_type=result_type,
            severity=severity,
            headline=headline,
            source=np.random.choice(self.news_sources['tier1']),
            source_credibility=SourceCredibility.TIER1,
            is_material=True,
            disclosure_status=DisclosureStatus.ANNOUNCED,
        )
        events.append(event.to_dict())
        
        # Possibly add FDA decision
        if phase == 3 and 'positive' in result_type and np.random.random() < 0.3:
            fda_date = event_date + timedelta(days=np.random.randint(60, 180))
            if fda_date <= end_date:
                fda_result = np.random.choice(['fda_approval', 'fda_rejection'], p=[0.7, 0.3])
                fda_event = NewsEvent(
                    event_id=f"NEWS_{uuid4().hex[:12]}",
                    timestamp=datetime.combine(fda_date, datetime.min.time()) + timedelta(hours=np.random.randint(8, 17)),
                    entity_id=company.get('id', company.get('entity_id', '')),
                    entity_type='company',
                    event_category='clinical_trial',
                    event_type=fda_result,
                    severity=EventSeverity.POSITIVE if fda_result == 'fda_approval' else EventSeverity.CRITICAL,
                    headline=self._generate_headline(fda_result, company, drug=drug_name, indication=indication),
                    source="FDA",
                    source_credibility=SourceCredibility.REGULATORY,
                    is_material=True,
                    disclosure_status=DisclosureStatus.ANNOUNCED,
                )
                events.append(fda_event.to_dict())
        
        return events
    
    def _generate_ma_event(
        self,
        company: Dict,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Generate M&A event."""
        days_range = (end_date - start_date).days
        if days_range <= 0:
            days_range = 1
        event_date = start_date + timedelta(days=np.random.randint(0, days_range))
        
        event_type = np.random.choice(['merger_announcement', 'acquisition_announcement'])
        amount = np.random.uniform(0.5, 50)  # Billions
        
        event = NewsEvent(
            event_id=f"NEWS_{uuid4().hex[:12]}",
            timestamp=datetime.combine(event_date, datetime.min.time()) + timedelta(hours=np.random.randint(6, 18)),
            entity_id=company.get('id', company.get('entity_id', '')),
            entity_type='company',
            event_category='corporate_action',
            event_type=event_type,
            severity=EventSeverity.NEUTRAL,
            headline=f"{company.get('name', 'Company')} Announces ${amount:.1f}B {event_type.replace('_', ' ').title()}",
            source=np.random.choice(self.news_sources['tier1']),
            source_credibility=SourceCredibility.TIER1,
            is_material=True,
            disclosure_status=DisclosureStatus.ANNOUNCED,
        )
        return event.to_dict()
    
    def _generate_headline(
        self,
        event_type: str,
        entity: Dict,
        **kwargs
    ) -> str:
        """Generate a headline for an event."""
        templates = self.headline_templates.get(event_type, ["{entity} News Event"])
        template = np.random.choice(templates)
        
        entity_name = entity.get('name', entity.get('full_name', 'Company'))
        
        return template.format(
            entity=entity_name,
            jurisdiction=entity.get('jurisdiction', 'US'),
            target="Target Corp",
            amount=kwargs.get('amount', np.random.uniform(1, 20)),
            quarter=kwargs.get('quarter', np.random.randint(1, 5)),
            drug=kwargs.get('drug', 'Drug'),
            indication=kwargs.get('indication', 'condition'),
            phase=kwargs.get('phase', 3),
        )
    
    def _get_quarter_ends(self, start_date: date, end_date: date) -> List[date]:
        """Get quarter end dates in range."""
        quarter_ends = []
        current = date(start_date.year, 3, 31)
        
        while current <= end_date:
            if current >= start_date:
                quarter_ends.append(current)
            
            # Move to next quarter
            if current.month == 3:
                current = date(current.year, 6, 30)
            elif current.month == 6:
                current = date(current.year, 9, 30)
            elif current.month == 9:
                current = date(current.year, 12, 31)
            else:
                current = date(current.year + 1, 3, 31)
        
        return quarter_ends
    
    def _get_quarter(self, quarter_end: date) -> int:
        """Get quarter number from quarter end date."""
        month = quarter_end.month
        if month <= 3:
            return 1
        elif month <= 6:
            return 2
        elif month <= 9:
            return 3
        else:
            return 4
