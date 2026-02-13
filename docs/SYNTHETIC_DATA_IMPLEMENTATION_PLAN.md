# Synthetic Data Generator Implementation Plan

## Overview

Extend the existing `SyntheticDataGenerator` to produce realistic, labeled data for **AML/Transaction Surveillance** model training and testing. The implementation integrates concepts from IBM AMLSim while leveraging your existing entity/relationship generation.

---

## Architecture Summary

### Layered Data Architecture (Raw → Signals → Alerts)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RAW EVENT DATA LAYER                               │
│  (Ground truth - what actually happened)                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐  │
│  │ Entities  │ │ Accounts  │ │Transactions│ │   News    │ │ Corporate Events  │  │
│  │(Person/Co)│ │           │ │           │ │  Events   │ │ (M&A, Actions)    │  │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────────┬─────────┘  │
│        └─────────────┴─────────────┴─────────────┴─────────────────┘            │
│                                    │                                            │
│                          [Typology Injection - Hidden]                          │
└────────────────────────────────────┼────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ANALYSIS / SIGNAL LAYER                               │
│  (Model-generated features - rule-based or ML)                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Behavioral      │  │ Network         │  │ Entity          │                  │
│  │ Signals         │  │ Signals         │  │ Signals         │                  │
│  │ - velocity      │  │ - centrality    │  │ - PEP proximity │                  │
│  │ - volume_zscore │  │ - clustering    │  │ - sanctions hit │                  │
│  │ - pattern_score │  │ - risk_flow     │  │ - adverse_media │                  │
│  │ - peer_deviation│  │ - shared_attrs  │  │ - jurisdiction  │                  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                  │
│           └────────────────────┴────────────────────┘                           │
└────────────────────────────────────┼────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ALERT LAYER                                        │
│  (Rule-based alert generation from signals)                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         Alert Rules Engine                              │    │
│  │  - Threshold rules (signal > X)                                         │    │
│  │  - Combination rules (signal_A AND signal_B)                            │    │
│  │  - Sequence rules (pattern over time)                                   │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                    │                                            │
│                                    ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         Alert Distribution                              │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │    │
│  │  │   Low Risk   │  │  Medium Risk │  │  High Risk   │  │  SAR-able   │  │    │
│  │  │    ~70%      │  │    ~20%      │  │    ~8%       │  │   ~1-2%     │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────┼────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CASE LAYER                                         │
│  (Investigation outcomes with analyst noise)                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Alerts → Cases → Dispositions (closed_no_issue | monitored | escalated | SAR) │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
  ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
  │  SQL/NoSQL  │            │  Graph DB   │            │   Search    │
  │  (profiles) │            │  (network)  │            │   (lookup)  │
  └─────────────┘            └─────────────┘            └─────────────┘
```

### Key Principle: Separation of Concerns

| Layer | What it contains | Who generates it |
|-------|------------------|------------------|
| **Raw Events** | Transactions, news, corporate actions | Synthetic generator (with hidden typology injection) |
| **Signals** | Derived features, scores, flags | Analysis models (rule-based or ML) |
| **Alerts** | Actionable items for investigation | Alert rules engine (thresholds on signals) |
| **Cases** | Investigation records with outcomes | Case management simulation |

---

## Phase 1: Core Transaction Infrastructure

### 1.1 New Entity Types

Add to `src/antipode/graph/models.py`:

```python
class EntityType(str, Enum):
    # ... existing ...
    ACCOUNT = "Account"
    TRANSACTION = "Transaction"
    COUNTERPARTY = "Counterparty"
    ALERT = "Alert"
    CASE = "Case"

class RelationshipType(str, Enum):
    # ... existing ...
    HAS_ACCOUNT = "HAS_ACCOUNT"
    TRANSACTS_WITH = "TRANSACTS_WITH"
    PAYS = "PAYS"
    RECEIVES_FROM = "RECEIVES_FROM"
    ALERT_ON = "ALERT_ON"
    CASE_CONTAINS = "CASE_CONTAINS"
```

### 1.2 New Data Models

Create `src/antipode/data/models/account.py`:

```python
@dataclass
class Account:
    account_id: str
    customer_id: str                    # FK to Person or Company
    product_type: str                   # DDA, savings, card, wallet, brokerage
    currency: str
    country: str
    branch: Optional[str]
    open_date: date
    close_date: Optional[date]
    status: str                         # active, dormant, closed, frozen
    channel_profile: str                # online, mobile, branch, API
    daily_limit: float
    monthly_limit: float
    expected_monthly_volume: float      # baseline for anomaly detection
    expected_corridors: List[str]       # expected destination countries
```

Create `src/antipode/data/models/transaction.py`:

```python
@dataclass
class Transaction:
    txn_id: str
    timestamp: datetime
    amount: float
    currency: str
    direction: str                      # credit, debit
    txn_type: str                       # wire, ACH, SEPA, cash, card, internal, crypto
    channel: str                        # branch, online, mobile, API
    from_account_id: str
    to_account_id: Optional[str]        # for internal transfers
    counterparty_id: Optional[str]      # for external transfers
    originator_name_raw: str            # free-form, messy
    beneficiary_name_raw: str
    orig_country: str
    dest_country: str
    payment_reference: Optional[str]
    bank_bic: Optional[str]
    # Hidden ground truth (not exposed to models)
    _is_suspicious: bool = False
    _typology: Optional[str] = None
    _scenario_id: Optional[str] = None
```

Create `src/antipode/data/models/counterparty.py`:

```python
@dataclass
class Counterparty:
    counterparty_id: str
    name_raw: str
    country: Optional[str]
    bank_country: Optional[str]
    risk_flags: List[str]               # some missing/wrong intentionally
```

### 1.3 Customer Segments

Create `src/antipode/data/config/segments.py`:

```python
CUSTOMER_SEGMENTS = {
    "retail_salaried": {
        "description": "Regular employed individuals",
        "monthly_volume_range": (2000, 15000),
        "txn_frequency": {"salary": 1, "bills": 4, "retail": 20, "wire": 0.5},
        "channels": {"online": 0.6, "mobile": 0.3, "branch": 0.1},
        "corridors": {"domestic": 0.95, "cross_border": 0.05},
    },
    "smb": {
        "description": "Small-medium businesses",
        "monthly_volume_range": (50000, 500000),
        "txn_frequency": {"payroll": 2, "supplier": 15, "tax": 0.25, "wire": 5},
        "channels": {"online": 0.7, "API": 0.2, "branch": 0.1},
        "corridors": {"domestic": 0.8, "cross_border": 0.2},
    },
    "cash_intensive": {
        "description": "Cash-heavy businesses (restaurants, retail)",
        "monthly_volume_range": (30000, 200000),
        "txn_frequency": {"cash_deposit": 20, "supplier": 10, "wire": 3},
        "channels": {"branch": 0.6, "online": 0.3, "mobile": 0.1},
        "corridors": {"domestic": 0.9, "cross_border": 0.1},
    },
    "hnw": {
        "description": "High net worth individuals",
        "monthly_volume_range": (100000, 5000000),
        "txn_frequency": {"wire": 5, "investment": 3, "luxury": 2},
        "channels": {"online": 0.5, "branch": 0.3, "API": 0.2},
        "corridors": {"domestic": 0.6, "cross_border": 0.4},
    },
    "corporate": {
        "description": "Large corporations",
        "monthly_volume_range": (1000000, 100000000),
        "txn_frequency": {"payroll": 4, "supplier": 50, "treasury": 10, "fx": 5},
        "channels": {"API": 0.6, "online": 0.3, "branch": 0.1},
        "corridors": {"domestic": 0.5, "cross_border": 0.5},
    },
}
```

### 1.4 Account Generator

**Important**: `expected_monthly_volume` and `expected_corridors` are **NOT** stored on raw account data.
These are **derived signals** computed by analysis models from historical transaction patterns.

Add to `SyntheticDataGenerator`:

```python
def generate_accounts(
    self,
    customers: List[Dict],
    accounts_per_customer: Tuple[int, int] = (1, 3)
) -> List[Dict[str, Any]]:
    """Generate accounts linked to customers
    
    Note: Raw account data does NOT include expected_volume or expected_corridors.
    Those are derived signals computed later from transaction history.
    """
    accounts = []
    for customer in customers:
        segment = self._assign_segment(customer)
        num_accounts = np.random.randint(*accounts_per_customer)
        
        for j in range(num_accounts):
            account = {
                'account_id': f"ACCT_{len(accounts):08d}",
                'customer_id': customer['id'],
                'product_type': self._select_product_type(segment),
                'currency': self._select_currency(customer.get('jurisdiction', 'US')),
                'country': customer.get('jurisdiction', 'US'),
                'branch': self._generate_branch(customer.get('jurisdiction')),
                'open_date': self._generate_open_date(customer),
                'close_date': None,
                'status': 'active',
                'channel_profile': self._select_channel_profile(segment),
                # Segment is used internally for generation but could be
                # stored as declared_segment (from onboarding) vs actual behavior
                'declared_segment': segment,
                # KYC-declared fields (may differ from actual behavior)
                'declared_monthly_turnover': self._generate_declared_turnover(segment),
                'declared_purpose': self._generate_declared_purpose(segment),
            }
            accounts.append(account)
    return accounts
```

### 1.5 Regional Configuration (Americas, EMEA, APAC)

Create `src/antipode/data/config/regions.py`:

```python
REGIONS = {
    "americas": {
        "countries": {
            "US": {"weight": 0.50, "currency": "USD", "locale": "en_US"},
            "CA": {"weight": 0.08, "currency": "CAD", "locale": "en_CA"},
            "BR": {"weight": 0.05, "currency": "BRL", "locale": "pt_BR"},
            "MX": {"weight": 0.03, "currency": "MXN", "locale": "es_MX"},
        },
        "reporting_threshold": 10000,  # USD
        "regulators": ["FinCEN", "FINTRAC", "COAF"],
    },
    "emea": {
        "countries": {
            "GB": {"weight": 0.12, "currency": "GBP", "locale": "en_GB"},
            "DE": {"weight": 0.08, "currency": "EUR", "locale": "de_DE"},
            "FR": {"weight": 0.06, "currency": "EUR", "locale": "fr_FR"},
            "CH": {"weight": 0.04, "currency": "CHF", "locale": "de_CH"},
            "NL": {"weight": 0.03, "currency": "EUR", "locale": "nl_NL"},
            "AE": {"weight": 0.03, "currency": "AED", "locale": "ar_AE"},
            "ZA": {"weight": 0.02, "currency": "ZAR", "locale": "en_ZA"},
            "SA": {"weight": 0.02, "currency": "SAR", "locale": "ar_SA"},
        },
        "reporting_threshold": 10000,  # EUR equivalent
        "regulators": ["FCA", "BaFin", "ACPR", "FINMA", "DNB"],
    },
    "apac": {
        "countries": {
            "IN": {"weight": 0.15, "currency": "INR", "locale": "en_IN"},
            "SG": {"weight": 0.06, "currency": "SGD", "locale": "en_SG"},
            "HK": {"weight": 0.05, "currency": "HKD", "locale": "zh_HK"},
            "AU": {"weight": 0.04, "currency": "AUD", "locale": "en_AU"},
            "JP": {"weight": 0.04, "currency": "JPY", "locale": "ja_JP"},
            "CN": {"weight": 0.03, "currency": "CNY", "locale": "zh_CN"},
            "MY": {"weight": 0.02, "currency": "MYR", "locale": "ms_MY"},
        },
        "reporting_threshold": 500000,  # INR / varies by country
        "regulators": ["FIU-IND", "MAS", "HKMA", "AUSTRAC", "JAFIC"],
    },
}

# High-risk jurisdictions (for corridor risk)
HIGH_RISK_JURISDICTIONS = [
    "IR", "KP", "SY", "CU", "VE", "MM", "AF", "YE", "LY", "SS",
    # Grey list (FATF)
    "PK", "NG", "PH", "TZ", "UG",
]

# Offshore financial centers
OFFSHORE_JURISDICTIONS = [
    "KY", "VG", "BM", "PA", "JE", "GG", "IM", "LI", "MC", "AD",
]

# India-specific configuration
INDIA_CONFIG = {
    "states": [
        "Maharashtra", "Karnataka", "Tamil Nadu", "Delhi", "Gujarat",
        "Telangana", "West Bengal", "Rajasthan", "Uttar Pradesh", "Kerala",
    ],
    "cities_by_state": {
        "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Thane"],
        "Karnataka": ["Bengaluru", "Mysuru", "Hubli"],
        "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"],
        "Delhi": ["New Delhi", "Noida", "Gurgaon"],
        "Gujarat": ["Ahmedabad", "Surat", "Vadodara"],
        # ... etc
    },
    "reporting_thresholds": {
        "cash": 1000000,      # INR 10 lakh
        "wire_international": 500000,  # INR 5 lakh
    },
    "regulators": ["FIU-IND", "RBI", "SEBI"],
    "id_types": ["PAN", "Aadhaar", "Passport", "Voter_ID", "Driving_License"],
}
```

### 1.6 Baseline Transaction Generator

```python
def generate_baseline_transactions(
    self,
    accounts: List[Dict],
    counterparties: List[Dict],
    start_date: date,
    end_date: date
) -> List[Dict[str, Any]]:
    """Generate normal transaction behavior based on customer segments"""
    transactions = []
    
    for account in accounts:
        segment = account['segment']
        segment_config = CUSTOMER_SEGMENTS[segment]
        
        # Generate transactions day by day
        current_date = start_date
        while current_date <= end_date:
            daily_txns = self._generate_daily_transactions(
                account, segment_config, current_date, counterparties
            )
            transactions.extend(daily_txns)
            current_date += timedelta(days=1)
    
    return transactions

def _generate_daily_transactions(
    self,
    account: Dict,
    segment_config: Dict,
    txn_date: date,
    counterparties: List[Dict]
) -> List[Dict]:
    """Generate transactions for a single day with temporal realism"""
    txns = []
    
    # Apply day-of-week effects
    dow_multiplier = self._get_dow_multiplier(txn_date, segment_config)
    
    # Apply end-of-month effects (payroll, rent, etc.)
    eom_multiplier = self._get_eom_multiplier(txn_date, segment_config)
    
    for txn_type, monthly_freq in segment_config['txn_frequency'].items():
        # Convert monthly frequency to daily probability
        daily_prob = (monthly_freq / 30) * dow_multiplier * eom_multiplier
        
        if np.random.random() < daily_prob:
            txn = self._create_transaction(
                account, txn_type, txn_date, counterparties, segment_config
            )
            txns.append(txn)
    
    return txns
```

---

## Phase 1B: News & Corporate Events Layer

### 1B.1 News Event Types

Create `src/antipode/data/models/news_event.py`:

```python
@dataclass
class NewsEvent:
    event_id: str
    timestamp: datetime
    entity_id: str                      # Company or Person this relates to
    entity_type: str                    # company, person
    
    # Event classification
    event_category: str                 # See EVENT_CATEGORIES below
    event_type: str                     # Specific type within category
    severity: str                       # positive, neutral, negative, critical
    
    # Content
    headline: str
    summary: str
    source: str                         # news outlet, regulator, exchange
    source_credibility: str             # tier1, tier2, tier3, social
    
    # For trade surveillance (market-moving events)
    is_material: bool                   # Could affect stock price
    disclosure_status: str              # pre_announcement, announced, rumor
    
    # Hidden ground truth
    _is_synthetic_adverse: bool = False
    _linked_typology: Optional[str] = None


EVENT_CATEGORIES = {
    "adverse_media": {
        "types": [
            "fraud_allegation",
            "corruption_investigation",
            "sanctions_violation",
            "money_laundering",
            "tax_evasion",
            "environmental_violation",
            "labor_violation",
            "data_breach",
            "executive_misconduct",
            "regulatory_action",
        ],
        "severity_default": "negative",
    },
    "regulatory": {
        "types": [
            "sec_enforcement",
            "doj_investigation",
            "fca_action",
            "sebi_order",
            "rbi_penalty",
            "consent_order",
            "cease_desist",
            "license_revocation",
        ],
        "severity_default": "critical",
    },
    "corporate_action": {
        "types": [
            "merger_announcement",
            "acquisition_announcement",
            "spinoff",
            "stock_split",
            "dividend_declaration",
            "buyback_announcement",
            "rights_issue",
            "delisting",
        ],
        "severity_default": "neutral",
    },
    "financial": {
        "types": [
            "earnings_announcement",
            "earnings_miss",
            "earnings_beat",
            "guidance_update",
            "credit_rating_change",
            "debt_default",
            "bankruptcy_filing",
            "restructuring",
        ],
        "severity_default": "neutral",
    },
    "clinical_trial": {  # For pharma/biotech
        "types": [
            "trial_initiation",
            "trial_results_positive",
            "trial_results_negative",
            "fda_approval",
            "fda_rejection",
            "trial_halt",
            "safety_concern",
        ],
        "severity_default": "neutral",
    },
    "leadership": {
        "types": [
            "ceo_change",
            "cfo_change",
            "board_change",
            "executive_departure",
            "executive_arrest",
            "whistleblower_complaint",
        ],
        "severity_default": "neutral",
    },
    "market": {
        "types": [
            "trading_halt",
            "unusual_volume",
            "price_spike",
            "short_interest_surge",
            "insider_trading_filing",
            "large_block_trade",
        ],
        "severity_default": "neutral",
    },
}
```

### 1B.2 News Event Generator

```python
class NewsEventGenerator:
    """Generate realistic news and corporate events"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.news_sources = {
            "tier1": ["Reuters", "Bloomberg", "WSJ", "FT", "CNBC"],
            "tier2": ["Business Insider", "MarketWatch", "Economic Times", "Mint"],
            "tier3": ["Industry blogs", "Local news", "Trade publications"],
            "regulatory": ["SEC", "DOJ", "FCA", "SEBI", "RBI", "FinCEN"],
        }
    
    def generate_news_events(
        self,
        companies: List[Dict],
        persons: List[Dict],
        start_date: date,
        end_date: date,
        adverse_event_rate: float = 0.05,  # 5% of entities get adverse news
    ) -> List[Dict]:
        """Generate news events for entities"""
        events = []
        
        # Corporate events (routine)
        for company in companies:
            events.extend(self._generate_routine_corporate_events(company, start_date, end_date))
        
        # Adverse media (for subset of entities)
        adverse_entities = self._select_adverse_entities(companies, persons, adverse_event_rate)
        for entity in adverse_entities:
            events.extend(self._generate_adverse_events(entity, start_date, end_date))
        
        # Market-moving events (for trade surveillance)
        if self.config.get('include_market_events', True):
            events.extend(self._generate_market_events(companies, start_date, end_date))
        
        return sorted(events, key=lambda x: x['timestamp'])
    
    def _generate_routine_corporate_events(
        self,
        company: Dict,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Generate routine corporate events (earnings, M&A, etc.)"""
        events = []
        
        # Quarterly earnings (4 per year)
        for quarter_end in self._get_quarter_ends(start_date, end_date):
            if np.random.random() < 0.9:  # 90% report earnings
                event = {
                    'event_id': f"NEWS_{uuid4().hex[:12]}",
                    'timestamp': quarter_end + timedelta(days=np.random.randint(15, 45)),
                    'entity_id': company['id'],
                    'entity_type': 'company',
                    'event_category': 'financial',
                    'event_type': np.random.choice(['earnings_beat', 'earnings_miss', 'earnings_announcement'], p=[0.4, 0.3, 0.3]),
                    'severity': 'neutral',
                    'headline': f"{company['name']} Reports Q{self._get_quarter(quarter_end)} Earnings",
                    'source': np.random.choice(self.news_sources['tier1']),
                    'is_material': True,
                    'disclosure_status': 'announced',
                }
                events.append(event)
        
        # M&A events (rare)
        if np.random.random() < 0.02:  # 2% chance per company
            events.append(self._generate_ma_event(company, start_date, end_date))
        
        return events
    
    def _generate_adverse_events(
        self,
        entity: Dict,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Generate adverse media events for flagged entities"""
        events = []
        
        # Select adverse event types
        num_events = np.random.randint(1, 4)
        event_types = np.random.choice(
            EVENT_CATEGORIES['adverse_media']['types'],
            size=num_events,
            replace=False
        )
        
        for event_type in event_types:
            event_date = start_date + timedelta(days=np.random.randint(0, (end_date - start_date).days))
            
            event = {
                'event_id': f"NEWS_{uuid4().hex[:12]}",
                'timestamp': datetime.combine(event_date, datetime.min.time()) + timedelta(hours=np.random.randint(6, 20)),
                'entity_id': entity['id'],
                'entity_type': 'company' if 'COMP' in entity['id'] else 'person',
                'event_category': 'adverse_media',
                'event_type': event_type,
                'severity': np.random.choice(['negative', 'critical'], p=[0.7, 0.3]),
                'headline': self._generate_adverse_headline(entity, event_type),
                'source': np.random.choice(self.news_sources['tier1'] + self.news_sources['tier2']),
                'is_material': event_type in ['fraud_allegation', 'regulatory_action', 'sanctions_violation'],
                'disclosure_status': 'announced',
                '_is_synthetic_adverse': True,
            }
            events.append(event)
        
        return events
```

### 1B.3 Linking News to Transactions (for Trade Surveillance)

```python
class MarketMovingEventLinker:
    """Link news events to transaction patterns for insider trading detection"""
    
    def inject_insider_pattern(
        self,
        news_event: Dict,
        accounts: List[Dict],
        transactions: List[Dict],
    ) -> List[Dict]:
        """
        Inject suspicious trading pattern before material news
        
        Pattern: Unusual trading activity in days before announcement
        """
        if not news_event.get('is_material'):
            return []
        
        # Select accounts to participate in insider pattern
        # (connected to company via ownership/employment)
        connected_accounts = self._find_connected_accounts(
            news_event['entity_id'], accounts
        )
        
        if not connected_accounts:
            return []
        
        # Generate pre-announcement trades
        announcement_date = news_event['timestamp']
        insider_txns = []
        
        for account in connected_accounts[:3]:  # Limit participants
            # Trades 1-5 days before announcement
            for days_before in range(1, np.random.randint(2, 6)):
                trade_date = announcement_date - timedelta(days=days_before)
                
                txn = {
                    'txn_id': f"TXN_{uuid4().hex[:12]}",
                    'timestamp': trade_date,
                    'amount': np.random.uniform(10000, 500000),
                    'txn_type': 'securities_trade',
                    'direction': 'debit' if news_event['severity'] == 'positive' else 'credit',
                    # Hidden ground truth
                    '_is_suspicious': True,
                    '_typology': 'insider_trading',
                    '_linked_event_id': news_event['event_id'],
                }
                insider_txns.append(txn)
        
        return insider_txns
```

---

## Phase 1C: Signal Generation Layer

### 1C.1 Signal Types

Create `src/antipode/data/signals/definitions.py`:

```python
SIGNAL_DEFINITIONS = {
    # Behavioral signals (computed from transaction history)
    "behavioral": {
        "velocity_30d": {
            "description": "Transaction count in last 30 days",
            "computation": "count(txns where ts > now - 30d)",
            "type": "numeric",
        },
        "volume_30d": {
            "description": "Total volume in last 30 days",
            "computation": "sum(amount where ts > now - 30d)",
            "type": "numeric",
        },
        "volume_zscore": {
            "description": "Current month volume vs historical mean (z-score)",
            "computation": "(current_month_vol - mean_monthly_vol) / std_monthly_vol",
            "type": "numeric",
        },
        "peer_deviation": {
            "description": "Deviation from peer group behavior",
            "computation": "customer_metric / peer_group_median",
            "type": "numeric",
        },
        "in_out_ratio": {
            "description": "Ratio of incoming to outgoing funds",
            "computation": "sum(credits) / sum(debits)",
            "type": "numeric",
        },
        "rapid_movement_score": {
            "description": "Score for funds moving in and out quickly",
            "computation": "weighted_sum(txns where out_ts - in_ts < 48h)",
            "type": "numeric",
        },
        "structuring_score": {
            "description": "Score for transactions near reporting threshold",
            "computation": "count(txns where threshold - 1000 < amount < threshold)",
            "type": "numeric",
        },
        "counterparty_concentration": {
            "description": "HHI of counterparty distribution",
            "computation": "sum(counterparty_share^2)",
            "type": "numeric",
        },
        "new_counterparty_rate": {
            "description": "Rate of new counterparties in recent period",
            "computation": "count(new_counterparties_30d) / count(all_counterparties)",
            "type": "numeric",
        },
        "corridor_risk_score": {
            "description": "Weighted score based on destination countries",
            "computation": "sum(amount * country_risk_weight)",
            "type": "numeric",
        },
    },
    
    # Network signals (computed from graph)
    "network": {
        "degree_centrality": {
            "description": "Number of direct connections",
            "computation": "count(edges)",
            "type": "numeric",
        },
        "risk_flow_in": {
            "description": "Incoming flow from high-risk nodes",
            "computation": "sum(incoming_amount where source_risk > threshold)",
            "type": "numeric",
        },
        "shared_attribute_score": {
            "description": "Score for shared addresses/phones/devices",
            "computation": "weighted_count(shared_attributes)",
            "type": "numeric",
        },
        "pep_distance": {
            "description": "Shortest path distance to known PEP",
            "computation": "min(path_length to PEP nodes)",
            "type": "numeric",
        },
        "sanctions_distance": {
            "description": "Shortest path distance to sanctioned entity",
            "computation": "min(path_length to sanctioned nodes)",
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
        "adverse_media_severity": {
            "description": "Max severity of adverse media",
            "computation": "max(news_severity)",
            "type": "categorical",
        },
        "jurisdiction_risk": {
            "description": "Risk level of entity jurisdiction",
            "computation": "lookup(jurisdiction_risk_table)",
            "type": "categorical",
        },
        "kyc_age_days": {
            "description": "Days since last KYC refresh",
            "computation": "now - last_kyc_date",
            "type": "numeric",
        },
        "declared_vs_actual_volume": {
            "description": "Ratio of actual to declared volume",
            "computation": "actual_monthly_vol / declared_monthly_vol",
            "type": "numeric",
        },
    },
}
```

### 1C.2 Signal Generator

```python
class SignalGenerator:
    """
    Generate signals from raw event data.
    
    This simulates what analysis models (rule-based or ML) would produce.
    Signals are DERIVED data, not raw events.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        # Add noise to signals to simulate model imperfection
        self.signal_noise_std = config.get('signal_noise_std', 0.1)
    
    def generate_signals(
        self,
        accounts: List[Dict],
        transactions: List[Dict],
        news_events: List[Dict],
        graph_data: Dict,
        as_of_date: date,
    ) -> Dict[str, List[Dict]]:
        """
        Generate all signals for all accounts as of a given date.
        
        Returns dict with:
        - account_signals: List of signal records per account
        - customer_signals: List of signal records per customer
        """
        account_signals = []
        
        for account in accounts:
            account_txns = [t for t in transactions 
                          if t['from_account_id'] == account['account_id'] 
                          or t['to_account_id'] == account['account_id']]
            
            signals = {
                'account_id': account['account_id'],
                'customer_id': account['customer_id'],
                'as_of_date': as_of_date,
                
                # Behavioral signals
                'velocity_30d': self._compute_velocity(account_txns, as_of_date, 30),
                'volume_30d': self._compute_volume(account_txns, as_of_date, 30),
                'volume_zscore': self._compute_volume_zscore(account_txns, as_of_date),
                'in_out_ratio': self._compute_in_out_ratio(account_txns, as_of_date),
                'rapid_movement_score': self._compute_rapid_movement(account_txns, as_of_date),
                'structuring_score': self._compute_structuring_score(account_txns, as_of_date),
                'counterparty_concentration': self._compute_counterparty_hhi(account_txns),
                'corridor_risk_score': self._compute_corridor_risk(account_txns),
                
                # Network signals (from graph)
                'degree_centrality': self._get_graph_metric(graph_data, account['account_id'], 'degree'),
                'risk_flow_in': self._get_graph_metric(graph_data, account['account_id'], 'risk_flow'),
                'pep_distance': self._get_graph_metric(graph_data, account['customer_id'], 'pep_distance'),
                
                # Entity signals
                'adverse_media_flag': self._check_adverse_media(account['customer_id'], news_events),
                'declared_vs_actual_volume': self._compute_declared_vs_actual(account, account_txns),
            }
            
            # Add noise to numeric signals
            signals = self._add_signal_noise(signals)
            
            account_signals.append(signals)
        
        return {'account_signals': account_signals}
    
    def _add_signal_noise(self, signals: Dict) -> Dict:
        """Add realistic noise to signals (model imperfection)"""
        noisy_signals = signals.copy()
        
        for key, value in signals.items():
            if isinstance(value, (int, float)) and key not in ['account_id', 'customer_id']:
                noise = np.random.normal(0, abs(value) * self.signal_noise_std)
                noisy_signals[key] = value + noise
        
        return noisy_signals
```

---

## Phase 2: Typology Engine (AMLSim-inspired)

### 2.1 Typology Definitions

Create `src/antipode/data/typologies/definitions.py`:

```python
TYPOLOGIES = {
    "structuring": {
        "description": "Breaking large amounts into smaller transactions to avoid reporting thresholds",
        "indicators": ["amounts_just_below_threshold", "multiple_branches", "short_timeframe"],
        "params": {
            "threshold": 10000,
            "margin": 500,              # amounts between threshold-margin and threshold
            "num_transactions": (5, 15),
            "timeframe_days": (1, 5),
        }
    },
    "rapid_movement": {
        "description": "Funds received and moved out quickly (layering)",
        "indicators": ["in_out_velocity", "different_counterparties", "cross_border"],
        "params": {
            "velocity_hours": (1, 48),  # time between in and out
            "amount_retention": (0.9, 0.99),  # % moved out
            "hops": (2, 5),
        }
    },
    "fan_in": {
        "description": "Multiple sources sending to single account (collection)",
        "indicators": ["many_originators", "consolidation", "similar_amounts"],
        "params": {
            "num_sources": (5, 20),
            "timeframe_days": (1, 7),
            "amount_variance": 0.1,
        }
    },
    "fan_out": {
        "description": "Single source distributing to multiple accounts (distribution)",
        "indicators": ["many_beneficiaries", "similar_amounts", "short_timeframe"],
        "params": {
            "num_destinations": (5, 20),
            "timeframe_days": (1, 7),
            "amount_variance": 0.1,
        }
    },
    "cycle": {
        "description": "Circular flow of funds (round-tripping)",
        "indicators": ["circular_path", "similar_amounts", "layered_entities"],
        "params": {
            "cycle_length": (3, 6),     # number of hops
            "amount_decay": (0.95, 0.99),
            "timeframe_days": (3, 14),
        }
    },
    "mule": {
        "description": "Account used as pass-through for illicit funds",
        "indicators": ["new_account", "high_volume_sudden", "many_counterparties"],
        "params": {
            "account_age_days": (30, 90),
            "volume_spike_multiplier": (5, 20),
            "num_counterparties": (10, 50),
        }
    },
    "high_risk_corridor": {
        "description": "Transactions to/from high-risk jurisdictions",
        "indicators": ["hr_jurisdiction", "unusual_for_customer", "large_amounts"],
        "params": {
            "jurisdictions": ["IR", "KP", "SY", "CU", "VE", "MM"],
            "amount_multiplier": (2, 10),
        }
    },
}
```

### 2.2 Typology Injector

Create `src/antipode/data/typologies/injector.py`:

```python
class TypologyInjector:
    """Injects money laundering patterns into transaction data"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.scenarios = []  # Track injected scenarios for ground truth
    
    def inject_typologies(
        self,
        accounts: List[Dict],
        transactions: List[Dict],
        counterparties: List[Dict],
        typology_config: Dict
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Inject typologies and return updated transactions + scenario registry
        
        typology_config example:
        {
            "structuring": {"prevalence": 0.02, "accounts": "random"},
            "rapid_movement": {"prevalence": 0.01, "accounts": "high_risk"},
            "fan_in": {"prevalence": 0.005, "accounts": "random"},
        }
        """
        injected_txns = []
        
        for typology_name, config in typology_config.items():
            # Select accounts to participate
            participant_accounts = self._select_participants(
                accounts, config['prevalence'], config.get('accounts', 'random')
            )
            
            for account in participant_accounts:
                scenario_id = f"SCENARIO_{len(self.scenarios):06d}"
                
                # Generate typology-specific transactions
                typology_txns = self._generate_typology_transactions(
                    typology_name, account, counterparties, scenario_id
                )
                injected_txns.extend(typology_txns)
                
                # Record scenario for ground truth
                self.scenarios.append({
                    'scenario_id': scenario_id,
                    'typology': typology_name,
                    'primary_account': account['account_id'],
                    'customer_id': account['customer_id'],
                    'transaction_ids': [t['txn_id'] for t in typology_txns],
                    'start_date': min(t['timestamp'] for t in typology_txns),
                    'end_date': max(t['timestamp'] for t in typology_txns),
                    'total_amount': sum(t['amount'] for t in typology_txns),
                })
        
        # Merge with baseline transactions
        all_transactions = transactions + injected_txns
        all_transactions.sort(key=lambda x: x['timestamp'])
        
        return all_transactions, self.scenarios
    
    def _generate_typology_transactions(
        self,
        typology_name: str,
        account: Dict,
        counterparties: List[Dict],
        scenario_id: str
    ) -> List[Dict]:
        """Generate transactions matching a specific typology pattern"""
        
        if typology_name == "structuring":
            return self._generate_structuring(account, scenario_id)
        elif typology_name == "rapid_movement":
            return self._generate_rapid_movement(account, counterparties, scenario_id)
        elif typology_name == "fan_in":
            return self._generate_fan_in(account, counterparties, scenario_id)
        elif typology_name == "fan_out":
            return self._generate_fan_out(account, counterparties, scenario_id)
        elif typology_name == "cycle":
            return self._generate_cycle(account, counterparties, scenario_id)
        # ... etc
    
    def _generate_structuring(self, account: Dict, scenario_id: str) -> List[Dict]:
        """Generate structuring pattern: multiple deposits just under threshold"""
        params = TYPOLOGIES["structuring"]["params"]
        threshold = params["threshold"]
        margin = params["margin"]
        num_txns = np.random.randint(*params["num_transactions"])
        timeframe = np.random.randint(*params["timeframe_days"])
        
        txns = []
        base_date = datetime.now() - timedelta(days=np.random.randint(30, 180))
        
        for i in range(num_txns):
            amount = np.random.uniform(threshold - margin, threshold - 50)
            txn_date = base_date + timedelta(
                days=np.random.randint(0, timeframe),
                hours=np.random.randint(9, 17)
            )
            
            txn = {
                'txn_id': f"TXN_{uuid4().hex[:12]}",
                'timestamp': txn_date,
                'amount': round(amount, 2),
                'currency': 'USD',
                'direction': 'credit',
                'txn_type': 'cash',
                'channel': np.random.choice(['branch'] * 3 + ['atm']),
                'from_account_id': None,
                'to_account_id': account['account_id'],
                'counterparty_id': None,
                'originator_name_raw': 'CASH DEPOSIT',
                'beneficiary_name_raw': account.get('customer_name', ''),
                'orig_country': account['country'],
                'dest_country': account['country'],
                # Hidden ground truth
                '_is_suspicious': True,
                '_typology': 'structuring',
                '_scenario_id': scenario_id,
            }
            txns.append(txn)
        
        return txns
```

---

## Phase 3: Weak Label Alert Generation

### 3.1 Alert Distribution (Realistic)

**Target distribution** (based on real-world AML programs):

| Risk Level | % of Alerts | Description | Typical Outcome |
|------------|-------------|-------------|-----------------|
| **Low** | ~70% | Weak signals, single rule hit, low amounts | Auto-close or quick dismiss |
| **Medium** | ~20% | Multiple signals, some anomaly, needs review | Most closed after review |
| **High** | ~8% | Strong signals, multiple rules, network risk | Escalated, some monitored |
| **SAR-able** | ~1-2% | Clear pattern, sustained activity, evidence | Filed SAR/STR |

### 3.2 Alert Model

Create `src/antipode/data/models/alert.py`:

```python
# Alert risk levels (not just tiers)
class AlertRiskLevel(str, Enum):
    LOW = "low"           # ~70% of alerts
    MEDIUM = "medium"     # ~20% of alerts
    HIGH = "high"         # ~8% of alerts
    CRITICAL = "critical" # ~1-2% of alerts (SAR-able)


@dataclass
class Alert:
    alert_id: str
    created_ts: datetime
    rule_id: str
    rule_name: str
    account_id: str
    customer_id: str
    transaction_ids: List[str]
    
    # Alert scoring (what models see)
    risk_level: AlertRiskLevel          # low, medium, high, critical
    score: float                        # 0-100 confidence
    risk_factors: List[str]
    
    # Signals that triggered this alert (from signal layer)
    triggering_signals: Dict[str, float]
    
    # Case linkage
    case_id: Optional[str] = None
    
    # Hidden ground truth (for evaluation only)
    _true_positive: Optional[bool] = None
    _scenario_id: Optional[str] = None
```

### 3.3 Alert Rules Engine (Signal-Based)

Alerts are generated from **signals**, not directly from raw transactions.
This enforces the separation: Raw Events → Signals → Alerts.

```python
class AlertRulesEngine:
    """
    Generate alerts from signals (not raw transactions).
    
    Rules operate on the signal layer, not raw data.
    This ensures proper separation of concerns.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.rules = self._load_rules()
        
        # Target distribution
        self.target_distribution = {
            AlertRiskLevel.LOW: 0.70,
            AlertRiskLevel.MEDIUM: 0.20,
            AlertRiskLevel.HIGH: 0.08,
            AlertRiskLevel.CRITICAL: 0.02,  # SAR-able
        }
    
    def _load_rules(self) -> List[Dict]:
        """Define alert rules based on signal thresholds"""
        return [
            {
                'rule_id': 'STRUCT_001',
                'rule_name': 'Structuring Pattern',
                'signal_conditions': [
                    ('structuring_score', '>', 3),
                ],
                'base_risk': AlertRiskLevel.MEDIUM,
                'escalation_conditions': [
                    ('volume_30d', '>', 50000, AlertRiskLevel.HIGH),
                    ('adverse_media_flag', '==', True, AlertRiskLevel.CRITICAL),
                ],
            },
            {
                'rule_id': 'RAPID_001',
                'rule_name': 'Rapid Movement',
                'signal_conditions': [
                    ('rapid_movement_score', '>', 0.7),
                    ('in_out_ratio', 'between', (0.9, 1.1)),
                ],
                'base_risk': AlertRiskLevel.MEDIUM,
                'escalation_conditions': [
                    ('corridor_risk_score', '>', 50, AlertRiskLevel.HIGH),
                    ('pep_distance', '<', 3, AlertRiskLevel.CRITICAL),
                ],
            },
            {
                'rule_id': 'VOL_ANOM_001',
                'rule_name': 'Volume Anomaly',
                'signal_conditions': [
                    ('volume_zscore', '>', 2.5),
                ],
                'base_risk': AlertRiskLevel.LOW,
                'escalation_conditions': [
                    ('volume_zscore', '>', 4, AlertRiskLevel.MEDIUM),
                    ('declared_vs_actual_volume', '>', 3, AlertRiskLevel.HIGH),
                ],
            },
            {
                'rule_id': 'CORR_001',
                'rule_name': 'High-Risk Corridor',
                'signal_conditions': [
                    ('corridor_risk_score', '>', 30),
                ],
                'base_risk': AlertRiskLevel.LOW,
                'escalation_conditions': [
                    ('corridor_risk_score', '>', 70, AlertRiskLevel.MEDIUM),
                    ('sanctions_distance', '<', 2, AlertRiskLevel.CRITICAL),
                ],
            },
            {
                'rule_id': 'NET_001',
                'rule_name': 'Network Risk',
                'signal_conditions': [
                    ('risk_flow_in', '>', 10000),
                    ('pep_distance', '<', 4),
                ],
                'base_risk': AlertRiskLevel.MEDIUM,
                'escalation_conditions': [
                    ('pep_distance', '==', 1, AlertRiskLevel.CRITICAL),
                ],
            },
            {
                'rule_id': 'MEDIA_001',
                'rule_name': 'Adverse Media',
                'signal_conditions': [
                    ('adverse_media_flag', '==', True),
                ],
                'base_risk': AlertRiskLevel.MEDIUM,
                'escalation_conditions': [
                    ('adverse_media_severity', '==', 'critical', AlertRiskLevel.HIGH),
                ],
            },
        ]
    
    def generate_alerts(
        self,
        account_signals: List[Dict],
        scenarios: List[Dict],  # For ground truth tracking
    ) -> List[Dict]:
        """Generate alerts from signals with target distribution"""
        alerts = []
        
        # Build scenario lookup for ground truth
        scenario_by_account = {s['primary_account']: s for s in scenarios}
        
        for signals in account_signals:
            account_id = signals['account_id']
            
            for rule in self.rules:
                if self._rule_matches(signals, rule):
                    risk_level = self._determine_risk_level(signals, rule)
                    
                    alert = {
                        'alert_id': f"ALERT_{uuid4().hex[:12]}",
                        'created_ts': signals['as_of_date'],
                        'rule_id': rule['rule_id'],
                        'rule_name': rule['rule_name'],
                        'account_id': account_id,
                        'customer_id': signals['customer_id'],
                        'risk_level': risk_level.value,
                        'score': self._compute_score(signals, rule),
                        'risk_factors': self._extract_risk_factors(signals, rule),
                        'triggering_signals': self._get_triggering_signals(signals, rule),
                        # Ground truth
                        '_true_positive': account_id in scenario_by_account,
                        '_scenario_id': scenario_by_account.get(account_id, {}).get('scenario_id'),
                    }
                    alerts.append(alert)
        
        # Adjust distribution to match targets (add noise alerts for low tier)
        alerts = self._adjust_distribution(alerts, account_signals)
        
        return alerts
    
    def _adjust_distribution(
        self,
        alerts: List[Dict],
        account_signals: List[Dict]
    ) -> List[Dict]:
        """
        Adjust alert distribution to match realistic targets.
        Add false positive alerts to reach ~70% low risk.
        """
        current_counts = Counter(a['risk_level'] for a in alerts)
        total = len(alerts)
        
        # If we don't have enough low-risk alerts, generate FPs
        target_low = int(total / 0.30 * 0.70)  # Scale up to get 70% low
        current_low = current_counts.get('low', 0)
        
        if current_low < target_low:
            # Generate additional low-risk FP alerts
            fp_needed = target_low - current_low
            fp_alerts = self._generate_false_positive_alerts(
                account_signals, fp_needed
            )
            alerts.extend(fp_alerts)
        
        return alerts
```

### 3.4 Detection Rules (Noisy)

Create `src/antipode/data/alerts/rules.py`:

```python
class DetectionRules:
    """Simulates noisy detection rules that generate alerts"""
    
    def __init__(self, config: Dict):
        self.config = config
        # Tunable noise parameters
        self.false_positive_rate = config.get('false_positive_rate', 0.7)
        self.false_negative_rate = config.get('false_negative_rate', 0.2)
    
    def run_rules(
        self,
        transactions: List[Dict],
        accounts: List[Dict],
        scenarios: List[Dict]
    ) -> List[Dict]:
        """Run detection rules and generate alerts with realistic noise"""
        alerts = []
        
        # Build lookup for ground truth
        suspicious_txn_ids = set()
        txn_to_scenario = {}
        for scenario in scenarios:
            for txn_id in scenario['transaction_ids']:
                suspicious_txn_ids.add(txn_id)
                txn_to_scenario[txn_id] = scenario
        
        # Rule 1: Threshold proximity (structuring detector)
        alerts.extend(self._rule_threshold_proximity(transactions, suspicious_txn_ids, txn_to_scenario))
        
        # Rule 2: Velocity (rapid movement detector)
        alerts.extend(self._rule_velocity(transactions, accounts, suspicious_txn_ids, txn_to_scenario))
        
        # Rule 3: Counterparty concentration
        alerts.extend(self._rule_counterparty_concentration(transactions, accounts, suspicious_txn_ids, txn_to_scenario))
        
        # Rule 4: High-risk corridor
        alerts.extend(self._rule_hr_corridor(transactions, suspicious_txn_ids, txn_to_scenario))
        
        # Rule 5: Volume anomaly
        alerts.extend(self._rule_volume_anomaly(transactions, accounts, suspicious_txn_ids, txn_to_scenario))
        
        return alerts
    
    def _rule_threshold_proximity(
        self,
        transactions: List[Dict],
        suspicious_txn_ids: Set[str],
        txn_to_scenario: Dict
    ) -> List[Dict]:
        """Detect transactions near reporting thresholds"""
        alerts = []
        threshold = 10000
        margin = 1000
        
        # Group transactions by account and time window
        # ... implementation ...
        
        for account_id, txn_group in grouped_txns.items():
            near_threshold = [t for t in txn_group if threshold - margin < t['amount'] < threshold]
            
            if len(near_threshold) >= 3:
                # Determine if this is a true positive
                is_tp = any(t['txn_id'] in suspicious_txn_ids for t in near_threshold)
                
                # Apply noise
                if is_tp and np.random.random() < self.false_negative_rate:
                    continue  # Miss the true positive
                
                if not is_tp and np.random.random() > self.false_positive_rate:
                    continue  # Don't generate false positive
                
                alert = self._create_alert(
                    rule_id='THRESH_PROX_001',
                    rule_name='Threshold Proximity',
                    account_id=account_id,
                    transactions=near_threshold,
                    is_tp=is_tp,
                    scenario_id=txn_to_scenario.get(near_threshold[0]['txn_id'], {}).get('scenario_id')
                )
                alerts.append(alert)
        
        return alerts
```

### 3.3 Alert Tier Assignment

```python
def _assign_tier(self, alert: Dict, transactions: List[Dict], account: Dict) -> int:
    """
    Assign alert tier based on multiple factors (not just ground truth)
    
    Tier 1: Likely false positive
    Tier 2: Interesting, needs investigation
    Tier 3: High priority, potential SAR
    """
    score = 0
    
    # Factor 1: Number of risk indicators
    score += len(alert.get('risk_factors', [])) * 10
    
    # Factor 2: Amount involved
    total_amount = sum(t['amount'] for t in transactions)
    if total_amount > 100000:
        score += 30
    elif total_amount > 50000:
        score += 20
    elif total_amount > 10000:
        score += 10
    
    # Factor 3: Customer risk rating
    customer_risk = account.get('customer_risk_rating', 'medium')
    if customer_risk == 'high':
        score += 25
    elif customer_risk == 'medium':
        score += 10
    
    # Factor 4: Cross-border involvement
    if any(t.get('orig_country') != t.get('dest_country') for t in transactions):
        score += 15
    
    # Factor 5: Multiple rules triggered (if applicable)
    # ... 
    
    # Factor 6: Network proximity to known bad actors
    # ...
    
    # Add noise to score
    score += np.random.normal(0, 10)
    
    # Assign tier
    if score >= 70:
        return 3
    elif score >= 40:
        return 2
    else:
        return 1
```

### 3.4 Case Generation with Noisy Outcomes

Create `src/antipode/data/alerts/cases.py`:

```python
@dataclass
class Case:
    case_id: str
    alert_ids: List[str]
    customer_id: str
    opened_ts: datetime
    closed_ts: Optional[datetime]
    status: str                         # open, closed, escalated
    disposition: Optional[str]          # closed_no_issue, monitored, escalated, filed_SAR
    analyst_id: str
    investigation_notes: Optional[str]
    
    # Hidden ground truth
    _contains_true_positive: bool
    _scenario_ids: List[str]


class CaseGenerator:
    """Generate cases from alerts with realistic analyst behavior"""
    
    def __init__(self, config: Dict):
        self.config = config
        # Analyst error rates
        self.tier1_escalation_rate = config.get('tier1_escalation_rate', 0.05)  # FPs that get escalated
        self.tier3_miss_rate = config.get('tier3_miss_rate', 0.1)  # TPs that get closed incorrectly
        self.investigation_delay_days = config.get('investigation_delay_days', (1, 30))
    
    def generate_cases(self, alerts: List[Dict]) -> List[Dict]:
        """Generate cases with noisy analyst decisions"""
        cases = []
        
        # Group alerts by customer
        alerts_by_customer = defaultdict(list)
        for alert in alerts:
            alerts_by_customer[alert['customer_id']].append(alert)
        
        for customer_id, customer_alerts in alerts_by_customer.items():
            # Decide whether to open a case
            max_tier = max(a['tier'] for a in customer_alerts)
            
            if max_tier == 1 and np.random.random() > 0.3:
                continue  # Most Tier 1 don't become cases
            
            case = self._create_case(customer_id, customer_alerts)
            case = self._assign_disposition(case, customer_alerts)
            cases.append(case)
        
        return cases
    
    def _assign_disposition(self, case: Dict, alerts: List[Dict]) -> Dict:
        """Assign case disposition with realistic noise"""
        contains_tp = case['_contains_true_positive']
        max_tier = max(a['tier'] for a in alerts)
        
        if contains_tp:
            # True positive case
            if max_tier == 3:
                if np.random.random() < self.tier3_miss_rate:
                    disposition = 'closed_no_issue'  # Analyst error
                else:
                    disposition = np.random.choice(
                        ['filed_SAR', 'escalated', 'monitored'],
                        p=[0.6, 0.25, 0.15]
                    )
            else:
                disposition = np.random.choice(
                    ['filed_SAR', 'escalated', 'monitored', 'closed_no_issue'],
                    p=[0.3, 0.3, 0.2, 0.2]
                )
        else:
            # False positive case
            if np.random.random() < self.tier1_escalation_rate:
                disposition = 'escalated'  # Analyst over-caution
            else:
                disposition = 'closed_no_issue'
        
        case['disposition'] = disposition
        case['status'] = 'closed'
        case['closed_ts'] = case['opened_ts'] + timedelta(
            days=np.random.randint(*self.investigation_delay_days)
        )
        
        return case
```

---

## Phase 4: Output Adapters

### 4.1 SQL Output (CSV/Parquet)

Create `src/antipode/data/output/sql_adapter.py`:

```python
class SQLOutputAdapter:
    """Export data in SQL-friendly formats"""
    
    def export(self, dataset: Dict, output_dir: str, format: str = 'csv'):
        """Export all tables to files"""
        os.makedirs(output_dir, exist_ok=True)
        
        tables = {
            'customers': self._prepare_customers(dataset),
            'accounts': self._prepare_accounts(dataset),
            'transactions': self._prepare_transactions(dataset),
            'counterparties': self._prepare_counterparties(dataset),
            'alerts': self._prepare_alerts(dataset),
            'cases': self._prepare_cases(dataset),
            # Ground truth tables (separate, for evaluation only)
            '_scenarios': self._prepare_scenarios(dataset),
            '_labels': self._prepare_labels(dataset),
        }
        
        for table_name, df in tables.items():
            if format == 'csv':
                df.to_csv(f"{output_dir}/{table_name}.csv", index=False)
            elif format == 'parquet':
                df.to_parquet(f"{output_dir}/{table_name}.parquet", index=False)
```

### 4.2 Graph Output

Create `src/antipode/data/output/graph_adapter.py`:

```python
class GraphOutputAdapter:
    """Export data for Neo4j graph database"""
    
    def export(self, dataset: Dict, output_dir: str):
        """Export nodes and edges for Neo4j import"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Nodes
        self._export_nodes(dataset, output_dir)
        
        # Edges with computed strengths
        self._export_edges(dataset, output_dir)
    
    def _export_edges(self, dataset: Dict, output_dir: str):
        """Export edges with relationship strength"""
        edges = []
        
        # Customer -> Account
        for account in dataset['accounts']:
            edges.append({
                'from_id': account['customer_id'],
                'to_id': account['account_id'],
                'type': 'HAS_ACCOUNT',
                'properties': {
                    'since': account['open_date'],
                    'is_primary': account.get('is_primary', False),
                }
            })
        
        # Account -> Counterparty (aggregated)
        txn_aggregates = self._aggregate_transactions(dataset['transactions'])
        for (from_acct, to_cp), agg in txn_aggregates.items():
            edges.append({
                'from_id': from_acct,
                'to_id': to_cp,
                'type': 'PAYS',
                'properties': {
                    'txn_count': agg['count'],
                    'total_volume': agg['total'],
                    'avg_amount': agg['avg'],
                    'last_ts': agg['last_ts'],
                    'corridors': list(agg['corridors']),
                    'strength': self._compute_strength(agg),
                }
            })
        
        # ... more edge types
        
        with open(f"{output_dir}/edges.json", 'w') as f:
            json.dump(edges, f, indent=2, default=str)
    
    def _compute_strength(self, agg: Dict) -> float:
        """Compute relationship strength from aggregates"""
        # Normalize factors
        freq_score = min(agg['count'] / 100, 1.0) * 0.3
        vol_score = min(agg['total'] / 1000000, 1.0) * 0.3
        recency_score = self._recency_score(agg['last_ts']) * 0.2
        diversity_score = len(agg['corridors']) / 10 * 0.2
        
        return round(freq_score + vol_score + recency_score + diversity_score, 3)
```

### 4.3 Search Index Output

Create `src/antipode/data/output/search_adapter.py`:

```python
class SearchOutputAdapter:
    """Export data for Elasticsearch/OpenSearch"""
    
    def export(self, dataset: Dict, output_dir: str):
        """Export entity documents for search indexing"""
        docs = []
        
        # Customer docs
        for customer in dataset['customers']:
            doc = {
                'entity_id': customer['id'],
                'entity_type': customer['entity_type'],
                'name_variants': self._extract_name_variants(customer),
                'identifiers': customer.get('identifiers', {}),
                'addresses': self._get_customer_addresses(customer, dataset),
                'dob_year': self._extract_dob_year(customer),
                'nationality': customer.get('nationality'),
                'jurisdiction': customer.get('jurisdiction'),
                'risk_highlights': self._extract_risk_highlights(customer, dataset),
                'fuzzy_keys': self._generate_fuzzy_keys(customer),
            }
            docs.append(doc)
        
        with open(f"{output_dir}/search_docs.json", 'w') as f:
            json.dump(docs, f, indent=2, default=str)
```

---

## Phase 5: Configuration & CLI

### 5.1 Master Configuration

Create `src/antipode/data/config/generation_config.yaml`:

```yaml
# Synthetic Data Generation Configuration

seed: 42

# Entity counts
entities:
  companies: 500
  persons: 2000
  addresses: 1000

# Account generation
accounts:
  per_customer_range: [1, 3]
  product_types:
    - DDA
    - savings
    - card

# Transaction generation
transactions:
  start_date: "2024-01-01"
  end_date: "2024-12-31"
  
# Typology injection
typologies:
  structuring:
    prevalence: 0.02
    account_selection: random
  rapid_movement:
    prevalence: 0.01
    account_selection: high_risk
  fan_in:
    prevalence: 0.005
    account_selection: random
  fan_out:
    prevalence: 0.005
    account_selection: random
  cycle:
    prevalence: 0.003
    account_selection: random
  mule:
    prevalence: 0.008
    account_selection: new_accounts

# Alert generation
alerts:
  false_positive_rate: 0.7
  false_negative_rate: 0.15
  
# Case generation
cases:
  tier1_escalation_rate: 0.05
  tier3_miss_rate: 0.08
  investigation_delay_days: [1, 30]

# Data quality (noise injection)
data_quality:
  missing_beneficiary_country: 0.05
  missing_counterparty_name: 0.03
  typo_rate: 0.02
  duplicate_rate: 0.01

# Output
output:
  formats: [csv, json]
  sql_dir: "output/sql"
  graph_dir: "output/graph"
  search_dir: "output/search"
  ground_truth_dir: "output/ground_truth"
```

### 5.2 Updated CLI

Update `src/antipode/data/synthetic_data_generator.py`:

```python
def main():
    parser = argparse.ArgumentParser(description='Generate synthetic compliance data')
    parser.add_argument('--config', type=str, default='config/generation_config.yaml')
    parser.add_argument('--output-dir', type=str, default='synthetic_data')
    parser.add_argument('--format', choices=['csv', 'parquet', 'json'], default='csv')
    parser.add_argument('--load-to-graph', action='store_true')
    parser.add_argument('--seed', type=int, default=42)
    
    # Quick overrides
    parser.add_argument('--companies', type=int)
    parser.add_argument('--persons', type=int)
    parser.add_argument('--days', type=int, help='Number of days of transactions')
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Apply overrides
    if args.companies:
        config['entities']['companies'] = args.companies
    # ... etc
    
    # Generate
    generator = SyntheticDataGenerator(seed=args.seed, config=config)
    dataset = generator.generate_full_dataset()
    
    # Export
    SQLOutputAdapter().export(dataset, f"{args.output_dir}/sql", args.format)
    GraphOutputAdapter().export(dataset, f"{args.output_dir}/graph")
    SearchOutputAdapter().export(dataset, f"{args.output_dir}/search")
```

---

## File Structure (After Implementation)

```
src/antipode/data/
├── __init__.py
├── synthetic_data_generator.py      # Main orchestrator (extended)
├── config/
│   ├── generation_config.yaml       # Master config
│   └── segments.py                  # Customer segment definitions
├── models/
│   ├── __init__.py
│   ├── account.py
│   ├── transaction.py
│   ├── counterparty.py
│   ├── alert.py
│   └── case.py
├── typologies/
│   ├── __init__.py
│   ├── definitions.py               # Typology patterns
│   └── injector.py                  # Pattern injection logic
├── alerts/
│   ├── __init__.py
│   ├── rules.py                     # Detection rules (noisy)
│   └── cases.py                     # Case generation
├── output/
│   ├── __init__.py
│   ├── sql_adapter.py
│   ├── graph_adapter.py
│   └── search_adapter.py
└── quality/
    ├── __init__.py
    └── noise_injector.py            # Data quality issues
```

---

## Implementation Order

### Sprint 1 (Week 1-2): Core Infrastructure
- [ ] Add new entity types to `models.py`
- [ ] Create `Account`, `Transaction`, `Counterparty` data models
- [ ] Implement `generate_accounts()` in main generator
- [ ] Implement basic `generate_baseline_transactions()`
- [ ] Add customer segment definitions

### Sprint 2 (Week 3-4): Typology Engine
- [ ] Create typology definitions
- [ ] Implement `TypologyInjector` with 3-4 patterns (structuring, rapid_movement, fan_in, fan_out)
- [ ] Add scenario registry for ground truth tracking
- [ ] Test typology injection

### Sprint 3 (Week 5-6): Alert & Case Generation
- [ ] Implement detection rules with noise
- [ ] Add alert tier assignment logic
- [ ] Implement case generation with noisy outcomes
- [ ] Create ground truth export

### Sprint 4 (Week 7-8): Output & Polish
- [ ] Implement SQL output adapter
- [ ] Implement Graph output adapter
- [ ] Implement Search output adapter
- [ ] Add data quality noise injection
- [ ] Update CLI and config
- [ ] Documentation and examples

---

## Validation Metrics

After generation, validate:

1. **Transaction balance**: Sum of credits ≈ sum of debits (within tolerance)
2. **Typology coverage**: Each typology has expected prevalence
3. **Alert distribution**: Tier 1 > Tier 2 > Tier 3
4. **Label noise**: FP rate and FN rate match config
5. **Temporal consistency**: No transactions before account open date
6. **Graph connectivity**: No orphan nodes

---

## Future Enhancements (Phase 5+)

- **Trade surveillance module**: Orders, trades, instruments, market abuse patterns
- **Network features**: Shared devices, IPs, phones
- **Multi-source simulation**: Different data quality per source system
- **Streaming mode**: Generate data in real-time for streaming tests
- **Privacy-preserving**: Differential privacy for sensitive attributes
