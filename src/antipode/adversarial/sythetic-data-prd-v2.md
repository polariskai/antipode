# Product Requirements Document
## Agentic Synthetic Financial Data Generation System

**Version:** 1.0  
**Last Updated:** January 17, 2026  
**Document Owner:** Product Team  
**Status:** Draft for Review

---

## Executive Summary

### Product Vision
Build an AI-powered synthetic data generation platform that creates realistic, privacy-compliant financial transaction datasets with labeled suspicious activities for training and testing compliance surveillance systems.

### Business Objectives
- **Primary:** Enable rapid development and testing of AI-based compliance surveillance without access to real customer data
- **Secondary:** Create shareable datasets for vendor evaluation, model benchmarking, and regulatory demonstrations
- **Tertiary:** Accelerate time-to-market for compliance AI products from 12-18 months to 3-6 months

### Success Metrics
- Generate 10M+ synthetic transactions with <5% statistical divergence from real financial data distributions
- Achieve 95%+ precision in ground truth labeling for suspicious activities
- Reduce compliance AI development cycle time by 60%
- Enable 100% privacy-compliant data sharing with external partners

---

## Problem Statement

### Current Challenges
1. **Data Access Barriers:** Real financial transaction data is subject to strict privacy regulations (GDPR, CCPA, banking secrecy laws), making it difficult to access for AI development
2. **Limited Labeled Data:** Suspicious activity cases are rare (0.1-1% of transactions) and historical labels are often incomplete or inaccurate
3. **Testing Constraints:** Cannot test new detection algorithms on production data without compliance risks
4. **Vendor Evaluation:** Impossible to share real data with vendors for POC/evaluation without extensive legal processes
5. **Scenario Coverage:** Real data may not contain examples of all suspicious activity typologies, limiting model training

### User Personas

**Persona 1: AI/ML Engineer**
- Needs large volumes of labeled training data
- Wants to test edge cases and rare scenarios
- Requires fast iteration cycles without data access approvals

**Persona 2: Compliance Analyst/Subject Matter Expert**
- Needs to validate that synthetic data reflects real-world patterns
- Wants control over typology representation and sophistication levels
- Requires explainable data generation process for regulatory audit

**Persona 3: Product Manager**
- Needs to demonstrate capabilities to regulators and customers
- Wants shareable datasets for vendor evaluations
- Requires cost-effective alternative to real data acquisition

---

## Product Overview

### Core Capabilities

#### 1. Entity & Profile Generation
Generate realistic synthetic entities including:
- **Individuals:** Demographics, financial profiles, behavioral patterns, life events
- **Companies:** Industry classification, size, revenue, business relationships
- **Accounts:** Checking, savings, investment, credit accounts with appropriate attributes
- **Relationship Networks:** Family ties, business partnerships, beneficial ownership structures

#### 2. Normal Transaction Generation
Create baseline transactional activity across:
- **Retail Banking:** Deposits, withdrawals, bill payments, P2P transfers, card purchases
- **Business Banking:** Payroll, supplier payments, receivables, tax payments
- **Investment:** Trades, settlements, dividends, portfolio rebalancing
- **International:** Wire transfers, FX, trade finance, remittances

#### 3. Suspicious Activity Injection
Synthesize known financial crime typologies:
- **AML:** Structuring, layering, integration, trade-based money laundering
- **Insider Trading:** Pre-announcement trading, tipping patterns, front-running
- **Market Manipulation:** Wash trading, spoofing, pump-and-dump schemes
- **Fraud:** Account takeover, synthetic identity fraud, check kiting

#### 4. Quality Assurance & Validation
Ensure synthetic data meets quality standards:
- Statistical validation against real-world distributions
- Temporal consistency and causality preservation
- Network graph realism (clustering coefficients, degree distributions)
- Privacy verification (no leakage of real data patterns)

#### 5. Ground Truth Labeling
Provide complete labels for all synthetic data:
- Transaction-level labels (normal vs. suspicious)
- Typology classification for suspicious activities
- Entity involvement mapping
- Timeline and causality chains
- Severity/sophistication scores

---

## Functional Requirements

### FR1: Entity Generation System

#### FR1.1 Individual Profile Generation
**Priority:** P0 (Must Have)

**Requirements:**
- Generate individual profiles with attributes:
  - Demographics: age (18-90), gender, location (city/state/country), occupation, education level
  - Financial: annual income ($0-$10M+), net worth, credit score (300-850), debt levels
  - Behavioral: banking frequency, channel preferences (online/branch/mobile), risk tolerance
  - Life stage: student, young professional, family, established, retiree
- Ensure statistical correlation between attributes (e.g., income correlates with age and occupation)
- Support configurable distribution parameters (e.g., income distribution by percentile)
- Output format: JSON with complete profile schema

**Acceptance Criteria:**
- Can generate 10,000+ unique individual profiles in <1 hour
- Profiles pass statistical distribution tests (Chi-square p>0.05)
- No duplicate identities generated
- All required attributes populated with valid values

#### FR1.2 Company Profile Generation
**Priority:** P0 (Must Have)

**Requirements:**
- Generate company profiles with attributes:
  - Business: industry (NAICS code), business model, incorporation date, size (employees/revenue)
  - Financial: annual revenue, EBITDA, cash flow patterns, seasonality
  - Operations: geographic presence, number of locations, supplier/customer base
  - Ownership: structure (public/private/partnership), beneficial owners, parent/subsidiary relationships
- Model realistic business relationships (suppliers, customers, service providers)
- Support industry-specific patterns (e.g., retail seasonality, manufacturing capital intensity)
- Output format: JSON with complete profile schema

**Acceptance Criteria:**
- Can generate 5,000+ unique company profiles in <1 hour
- Industry distributions match real-world business demographics
- Revenue and size metrics are internally consistent
- Business relationships form realistic network structures

#### FR1.3 Account Profile Generation
**Priority:** P0 (Must Have)

**Requirements:**
- Generate account profiles for individuals and companies:
  - Types: checking, savings, money market, credit card, investment (brokerage, IRA, 401k), loan
  - Attributes: opening date, balance, credit limit, interest rate, status (active/dormant/closed)
  - Access: ownership (single/joint), authorized users, online banking status
- Link accounts to appropriate entity types (e.g., 401k only for individuals)
- Model realistic account ownership patterns (average 3-5 accounts per individual)
- Support account lifecycle events (opening, closing, dormancy)

**Acceptance Criteria:**
- Each entity has 1-10 accounts based on profile
- Account balances reflect entity financial capacity
- Account types appropriate for entity type and demographics
- Account opening dates respect entity creation dates

#### FR1.4 Relationship Network Generation
**Priority:** P1 (Should Have)

**Requirements:**
- Generate relationship networks between entities:
  - Family: spouse, children, parents, siblings with appropriate age constraints
  - Business: employer-employee, partnership, vendor-customer, beneficial ownership
  - Social: friends, colleagues, club memberships
  - Financial: joint accounts, authorized users, power of attorney
- Create realistic network topology (small-world networks, power-law degree distributions)
- Support configurable network density and clustering parameters
- Output format: Graph structure (nodes + edges) with relationship types

**Acceptance Criteria:**
- Network exhibits realistic clustering (coefficient 0.2-0.4)
- Degree distribution follows power law
- No isolated nodes (all entities have at least one relationship)
- Relationship types are semantically valid (e.g., no child-employer relationships)

---

### FR2: Normal Transaction Generation

#### FR2.1 Retail Banking Transactions
**Priority:** P0 (Must Have)

**Requirements:**
- Generate realistic retail banking transactions:
  - **Deposits:** Payroll (bi-weekly/monthly), checks, cash deposits, transfers-in
  - **Withdrawals:** ATM (daily limits), checks, cash, transfers-out
  - **Bill Payments:** Recurring (rent, utilities, subscriptions) and one-time
  - **Card Purchases:** Debit/credit with merchant categories, online vs. in-person
  - **P2P Transfers:** Venmo-style transfers to network connections
- Model temporal patterns:
  - Day-of-week effects (more spending on weekends)
  - Time-of-day patterns (payroll hits midnight, ATM usage during day)
  - Monthly cycles (bills due on specific dates, payroll on 1st/15th)
  - Seasonal patterns (holiday spending, tax refunds)
- Model amount distributions:
  - Transaction amounts follow realistic distributions per category
  - Account for inflation and income level effects on spending
  - Include outliers (large purchases) at appropriate frequencies
- Maintain account balance consistency (no overdrafts unless account has overdraft protection)

**Acceptance Criteria:**
- Generate 100K+ transactions per 10K entities per month
- Transaction amounts within expected ranges per category
- Temporal patterns exhibit expected day/time effects (verified via statistical tests)
- Account balances remain non-negative (or respect overdraft limits)
- Each entity has transaction frequency consistent with their profile

#### FR2.2 Business Banking Transactions
**Priority:** P0 (Must Have)

**Requirements:**
- Generate realistic business banking transactions:
  - **Payables:** Supplier invoices, contractor payments, rent, utilities
  - **Receivables:** Customer payments, invoice settlements
  - **Payroll:** Employee salaries (bi-weekly/monthly), tax withholdings
  - **Taxes:** Quarterly estimated taxes, annual filings, sales tax remittances
  - **Capital:** Equipment purchases, facility investments, loan payments
- Model business-specific patterns:
  - Industry-appropriate transaction frequencies and amounts
  - Seasonality (e.g., retail peak in Q4, agriculture harvest cycles)
  - Business size effects (large companies have higher volumes)
  - Supplier/customer relationship stability (recurring vs. one-time)
- Ensure cash flow realism:
  - Revenue and expenses consistent with company profile
  - Positive cash flow on average (with occasional negative months)
  - Working capital cycles (receivables lag sales, payables lag purchases)

**Acceptance Criteria:**
- Business transactions represent 20-30% of total transaction volume
- Transaction amounts scale with company size
- Seasonal patterns evident in time-series analysis
- Cash flows remain viable (companies don't consistently run negative balances)

#### FR2.3 Investment Transactions
**Priority:** P1 (Should Have)

**Requirements:**
- Generate realistic investment transactions:
  - **Trades:** Stock/ETF/bond purchases and sales with market prices
  - **Settlements:** T+2 settlement for trades
  - **Dividends:** Quarterly dividend receipts for holdings
  - **Interest:** Bond coupon payments, money market interest
  - **Contributions:** IRA/401k contributions (respecting annual limits)
  - **Withdrawals:** RMDs for retirees, early withdrawals with penalties
- Model investor behavior:
  - Trading frequency based on investor profile (passive vs. active)
  - Portfolio allocation consistent with risk tolerance
  - Rebalancing behavior (quarterly/annually)
  - Tax-loss harvesting in taxable accounts
- Use realistic market data:
  - Price movements based on synthetic market indices
  - Dividend yields and frequencies realistic for asset types
  - Transaction costs (commissions, fees) included

**Acceptance Criteria:**
- Investment transactions represent 5-10% of total volume
- Portfolio allocations match investor risk profiles
- Trading frequencies consistent with active/passive strategies
- Annual contribution limits respected for tax-advantaged accounts

#### FR2.4 International Transactions
**Priority:** P1 (Should Have)

**Requirements:**
- Generate realistic international transactions:
  - **Wire Transfers:** Domestic and international with appropriate fees
  - **FX Conversions:** Currency exchanges with realistic spreads
  - **Trade Finance:** Letters of credit, documentary collections for businesses
  - **Remittances:** Cross-border person-to-person transfers
- Model cross-border patterns:
  - Higher transaction amounts for international wires vs. domestic
  - FX conversion occurs for transactions in different currencies
  - Geographic clustering (more transactions to countries with relationship ties)
  - Compliance metadata (purpose codes, beneficiary info)

**Acceptance Criteria:**
- International transactions represent 2-5% of total volume
- FX rates applied correctly with realistic spreads
- Wire transfer fees included based on amount and destination
- Remittance corridors exhibit realistic patterns (e.g., US→Mexico)

---

### FR3: Suspicious Activity Generation

#### FR3.1 AML Typology Generation
**Priority:** P0 (Must Have)

**Requirements:**
- Generate AML suspicious activity scenarios:
  - **Structuring (Smurfing):** Multiple transactions just under reporting threshold ($10K in US)
    - Variants: Single account multiple transactions, multiple accounts (smurfs), split across time
    - Sophistication levels: Obvious (many $9,500 transactions), Moderate (varying amounts $8K-$9.5K), Advanced (randomized amounts over longer periods)
  - **Layering:** Complex movement of funds through multiple accounts/entities
    - Variants: Circular transfers, nested shell companies, rapid movement
    - Sophistication levels: Simple (A→B→C→A), Moderate (5+ hops with delays), Advanced (international hops with FX)
  - **Trade-Based ML:** Over/under-invoicing, phantom shipments
    - Variants: Inflated invoices, multiple invoices for single shipment, no corresponding goods
    - Sophistication levels: Moderate (10-20% price inflation), Advanced (100%+ inflation or phantom)
  - **Cash-Intensive Business Abuse:** Front companies with inflated revenues
    - Variants: Restaurants, laundromats, car washes with unrealistic transaction volumes
    - Sophistication levels: Moderate (2x normal revenue), Advanced (5x+ with supporting "customers")

**Acceptance Criteria:**
- Can generate 1,000+ labeled AML scenarios across typologies
- Each scenario has complete timeline and entity involvement mapping
- Sophistication levels produce measurable detection difficulty differences
- Ground truth labels include typology, involved entities, timeline, severity score

#### FR3.2 Insider Trading Generation
**Priority:** P0 (Must Have)

**Requirements:**
- Generate insider trading scenarios:
  - **Pre-Announcement Trading:** Trading before material events (earnings, M&A, regulatory)
    - Timing: 1-30 days before announcement
    - Amounts: Unusual size relative to normal trading behavior
    - Direction: Consistent with eventual announcement (buy before good news)
  - **Tipping:** Information flow from insider to family/friends who then trade
    - Network: Insider → Tip recipient → Trades
    - Timing: Coordinated trading by network members before announcement
  - **Front-Running:** Trading ahead of large client orders
    - Pattern: Broker/advisor trades immediately before executing client order
    - Size: Smaller than client order but significant for broker's account
- Model corporate event calendar:
  - Quarterly earnings announcements
  - M&A activity, product launches, regulatory approvals
  - Executive trading windows and blackout periods
- Create realistic corporate connections:
  - Executives, board members, employees
  - Advisors, consultants, lawyers with MNPI access
  - Family members and close associates

**Acceptance Criteria:**
- Insider trading scenarios represent 0.01-0.1% of investment transactions
- Timing correlation between trades and announcements is statistically significant
- Tipping networks exhibit realistic relationship patterns
- False positive scenarios included (legitimate trading before coincidental announcements)

#### FR3.3 Market Manipulation Generation
**Priority:** P1 (Should Have)

**Requirements:**
- Generate market manipulation scenarios:
  - **Wash Trading:** Simultaneous buy/sell of same security to create false volume
    - Pattern: Matched trades within minutes, no change in beneficial ownership
    - Frequency: Repeated throughout day
  - **Spoofing/Layering:** Fake orders to move prices, cancel before execution
    - Pattern: Large orders placed, price moves, orders cancelled, opposite trade executed
    - Timing: Rapid sequence (seconds to minutes)
  - **Pump and Dump:** Coordinated buying to inflate price, then sell
    - Network: Multiple coordinated traders
    - Timeline: Days to weeks of accumulation, pump phase, dump phase

**Acceptance Criteria:**
- Market manipulation scenarios detectable via order book analysis
- Coordinated trading patterns across multiple entities
- Scenarios include realistic false positives (legitimate coordinated trading)

#### FR3.4 Fraud Scenario Generation
**Priority:** P2 (Nice to Have)

**Requirements:**
- Generate fraud scenarios:
  - **Account Takeover:** Sudden change in transaction patterns after credentials compromised
  - **Synthetic Identity:** New identity with no credit history makes rapid credit applications
  - **Check Kiting:** Exploiting float time between banks
- Model fraud signatures:
  - Sudden geographic changes (transactions from new locations)
  - Velocity changes (sudden spike in transaction frequency)
  - Channel changes (never used online banking, suddenly active)

**Acceptance Criteria:**
- Fraud scenarios represent 0.1-0.5% of transactions
- Each scenario has clear before/after fraud initiation patterns
- Realistic false positives included (legitimate life changes)

---

### FR4: Agent System Architecture

#### FR4.1 Scenario Director Agent
**Priority:** P0 (Must Have)

**Requirements:**
- Orchestrate overall data generation process:
  - Accept high-level generation parameters (entity count, transaction volume, date range, suspicious activity rate)
  - Create generation plan with phases and dependencies
  - Coordinate specialist agents and manage execution
  - Monitor progress and adjust parameters based on quality metrics
- Maintain global state:
  - Entity registry (all created entities and attributes)
  - Transaction ledger (all transactions for consistency)
  - Relationship graph (entity connections)
  - Global timeline (ensure temporal ordering)
  - Scenario tracker (active suspicious activities)
- Quality control:
  - Monitor statistical distributions vs. targets
  - Detect and resolve inconsistencies
  - Trigger re-generation for out-of-spec outputs

**Acceptance Criteria:**
- Can generate complete dataset (entities + transactions + suspicious activities) without human intervention
- Global state remains consistent across all agent outputs
- Quality metrics monitored in real-time with alerts for deviations
- Generation plan adapts to quality issues automatically

#### FR4.2 Profile Generation Agents
**Priority:** P0 (Must Have)

**Requirements:**
- Implement specialized agents:
  - **Individual Profile Agent:** Creates person profiles per FR1.1
  - **Company Profile Agent:** Creates business profiles per FR1.2
  - **Network Generation Agent:** Creates relationships per FR1.4
- Agent capabilities:
  - Access to domain knowledge (demographics, industry norms, etc.)
  - Statistically sound randomization with configurable distributions
  - Consistency validation (e.g., age-appropriate occupation)
  - Output in standardized JSON schema
- Performance:
  - Generate 100+ profiles per minute per agent instance
  - Support parallel execution of multiple agent instances
  - Idempotent operation (same seed produces same output)

**Acceptance Criteria:**
- Each agent produces valid outputs per schema
- Outputs pass statistical distribution tests
- Parallel agent execution produces consistent results
- Agent can explain its generation logic (for audit purposes)

#### FR4.3 Transaction Generation Agents
**Priority:** P0 (Must Have)

**Requirements:**
- Implement specialized agents per FR2.x:
  - **Retail Banking Agent**
  - **Business Banking Agent**
  - **Investment Agent**
  - **International Transaction Agent**
- Agent capabilities:
  - Access entity profiles and account information
  - Generate transactions following temporal and amount distributions
  - Maintain account balance consistency
  - Handle multi-entity transactions (transfers, payments)
  - Update global transaction ledger
- Performance:
  - Generate 10,000+ transactions per minute per agent instance
  - Support parallel execution across entity cohorts
  - Minimize memory footprint (stream processing where possible)

**Acceptance Criteria:**
- Transactions respect account balance constraints
- Temporal patterns match expected distributions
- Multi-entity transactions properly reference both parties
- Transaction volume scales linearly with entity count

#### FR4.4 Suspicious Activity Agents
**Priority:** P0 (Must Have)

**Requirements:**
- Implement specialized agents per FR3.x:
  - **AML Typology Agent**
  - **Insider Trading Agent**
  - **Market Manipulation Agent**
- Agent capabilities:
  - Create scenario blueprints (entities, accounts, timeline, transaction sequence)
  - Coordinate with transaction agents to inject suspicious transactions
  - Generate complete ground truth labels
  - Vary sophistication levels based on parameters
  - Ensure scenarios are detectable but realistic
- Scenario management:
  - Track active scenarios to prevent overlap/interference
  - Respect entity behavioral constraints (don't use conservative investor for aggressive manipulation)
  - Blend suspicious transactions with normal activity

**Acceptance Criteria:**
- Suspicious scenarios span realistic timeframes (days to months)
- Ground truth labels include all required metadata
- Scenarios at different sophistication levels exhibit measurable detection difficulty
- Suspicious transactions blend naturally with normal activity

#### FR4.5 Agent Memory & Coordination
**Priority:** P0 (Must Have)

**Requirements:**
- Implement shared memory system:
  - **Entity Registry:** Fast lookup of any entity by ID with full profile
  - **Transaction Ledger:** Append-only log of all transactions with indexing by entity, account, time
  - **Relationship Graph:** Graph database for network queries
  - **Timeline:** Global clock with event ordering
  - **Scenario Tracker:** Active suspicious activities with status
- Coordination mechanisms:
  - Message passing between agents (scenario requests, confirmations)
  - Locking for concurrent access to shared entities/accounts
  - Event sourcing for audit trail of all agent actions
- Performance:
  - Sub-second access time for entity/transaction lookups
  - Support 100+ concurrent agents accessing shared memory
  - Scalable to 10M+ transactions in memory

**Acceptance Criteria:**
- All agents can access shared memory without conflicts
- Concurrent updates maintain consistency
- Complete audit trail of all agent actions available
- Memory system supports required throughput

---

### FR5: Data Quality & Validation

#### FR5.1 Statistical Validation
**Priority:** P0 (Must Have)

**Requirements:**
- Validate synthetic data against expected distributions:
  - **Univariate:** Transaction amounts, frequencies, account balances
  - **Bivariate:** Correlations (income vs. spending, company size vs. transaction volume)
  - **Temporal:** Day-of-week, time-of-day, seasonal patterns
  - **Network:** Degree distributions, clustering coefficients, path lengths
- Implement statistical tests:
  - Kolmogorov-Smirnov test for distribution matching
  - Chi-square test for categorical distributions
  - Autocorrelation tests for temporal patterns
  - Graph metrics for network topology
- Generate validation reports:
  - Test results with p-values
  - Visualizations (histograms, time series, network graphs)
  - Comparison to target distributions
  - Flagged anomalies requiring investigation

**Acceptance Criteria:**
- All distributions pass statistical tests at p>0.05 significance
- Validation report generated automatically after each generation run
- Failed tests trigger alerts and prevent data export
- Visual comparison charts included in report

#### FR5.2 Consistency Validation
**Priority:** P0 (Must Have)

**Requirements:**
- Validate internal consistency:
  - **Account Balances:** No negative balances (unless overdraft), balances match transaction history
  - **Temporal Ordering:** All transactions respect creation dates of entities/accounts, no time-travel
  - **Relationship Logic:** Relationships respect constraints (age, entity type)
  - **Amount Constraints:** Transactions respect account limits, regulatory thresholds
- Implement validation rules:
  - Account balance reconciliation at each time point
  - Chronological ordering verification
  - Relationship constraint checking
  - Referential integrity (all IDs reference valid entities)
- Generate consistency report:
  - Count of violations by type
  - Examples of violations for debugging
  - Severity classification (critical vs. warning)

**Acceptance Criteria:**
- Zero critical consistency violations in exported data
- Validation runs in <10% of generation time
- Violations include sufficient context for debugging
- Automated remediation for common violations

#### FR5.3 Privacy Validation
**Priority:** P0 (Must Have)

**Requirements:**
- Verify no real data leakage:
  - No real names, addresses, SSNs, account numbers
  - Synthetic IDs do not match real ID patterns (e.g., valid SSNs)
  - Geographic coordinates are approximate (block level, not precise)
  - No verbatim patterns from real transaction data (if any was used for reference)
- Implement privacy checks:
  - Scan for PII patterns (regex for SSN, credit card, phone)
  - Validate synthetic ID generation (Luhn check fails for credit cards)
  - Check geographic precision (coordinates rounded)
  - Uniqueness verification (no ID collisions with known real IDs)
- Generate privacy report:
  - Confirmation of zero PII detected
  - Synthetic ID generation methodology
  - Anonymization techniques applied

**Acceptance Criteria:**
- Zero PII detected in automated scans
- All IDs fail real-ID validation checks
- Privacy report included with dataset documentation
- Export blocked if privacy checks fail

#### FR5.4 Ground Truth Validation
**Priority:** P0 (Must Have)

**Requirements:**
- Validate suspicious activity labels:
  - All labeled transactions have complete metadata
  - Scenario timelines are correct and complete
  - Entity involvement is accurately mapped
  - Severity scores are consistent within typology
- Cross-validate with detection systems:
  - Run basic rule-based detector on synthetic data
  - Verify labeled suspicious activities are detected
  - Check false positive rate on normal transactions
  - Ensure sophistication levels correlate with detection difficulty
- Generate ground truth report:
  - Count of scenarios by typology and sophistication
  - Detection rate by simple rules
  - Distribution of severity scores
  - Examples of each typology

**Acceptance Criteria:**
- 100% of labeled scenarios have complete metadata
- Simple rules detect >90% of low-sophistication scenarios
- High-sophistication scenarios have <50% detection rate by simple rules
- Ground truth labels are in documented, parseable format

---

### FR6: Data Export & Distribution

#### FR6.1 Export Formats
**Priority:** P0 (Must Have)

**Requirements:**
- Support multiple export formats:
  - **Transactions:** CSV, Parquet (for large datasets)
  - **Entities:** JSON, CSV
  - **Relationships:** GraphML, JSON
  - **Ground Truth Labels:** JSON, CSV
  - **Metadata:** JSON schema definitions
- Include comprehensive metadata:
  - Generation parameters (date range, entity count, etc.)
  - Schema documentation
  - Statistical summary
  - Validation report results
- Package exports:
  - Single archive (ZIP/TAR) containing all files
  - README with dataset description and usage instructions
  - Changelog/version tracking

**Acceptance Criteria:**
- All formats are industry-standard and widely supported
- Schemas are documented with examples
- Exports include all necessary files for standalone use
- Archive size optimized (compression where appropriate)

#### FR6.2 Data Versioning & Reproducibility
**Priority:** P1 (Should Have)

**Requirements:**
- Version all generated datasets:
  - Unique version ID for each generation run
  - Store generation parameters and random seeds
  - Tag with release version (e.g., v1.0-structuring-basic)
- Enable reproducibility:
  - Same parameters + seed → identical output
  - Document all agent versions and prompts used
  - Store configuration files with dataset
- Maintain dataset registry:
  - Catalog of all generated datasets
  - Searchable by attributes (size, typologies, date range)
  - Download links and usage statistics

**Acceptance Criteria:**
- Datasets can be regenerated exactly from stored parameters
- Version history tracked in registry
- Users can find datasets by required characteristics
- Configuration files enable exact reproduction

#### FR6.3 Documentation & Examples
**Priority:** P0 (Must Have)

**Requirements:**
- Provide comprehensive documentation:
  - **Dataset Description:** Entity counts, transaction volumes, date ranges, typology coverage
  - **Schema Reference:** Field definitions, data types, constraints, relationships
  - **Ground Truth Guide:** How to use labels, label schema, example queries
  - **Quality Report:** Statistical validation results, known limitations
  - **Getting Started:** Example code (Python/R/SQL) to load and explore data
- Create tutorial notebooks:
  - Loading data into popular tools (Pandas, Spark, SQL databases)
  - Basic EDA (exploratory data analysis)
  - Simple detector implementation
  - Label usage examples
- Provide sample datasets:
  - Small dataset (1K entities, 100K transactions) for quick testing
  - Medium dataset (10K entities, 1M transactions) for development
  - Large dataset (100K entities, 10M+ transactions) for production testing

**Acceptance Criteria:**
- Documentation covers all major use cases
- Tutorial notebooks run without errors on sample data
- Sample datasets downloadable without registration
- Documentation includes troubleshooting section

---

## Non-Functional Requirements

### NFR1: Performance
- **Generation Speed:** Generate 1M transactions in <30 minutes on standard cloud VM (8 vCPU, 32GB RAM)
- **Scalability:** System can scale to 100M+ transactions without architectural changes
- **Parallel Processing:** Support 100+ concurrent agent instances
- **Memory Efficiency:** Peak memory usage <2x final dataset size

### NFR2: Reliability
- **Consistency:** Generated data must maintain referential integrity and balance consistency
- **Error Handling:** Graceful degradation on agent errors, no partial/corrupted outputs
- **Resumability:** Long-running generation jobs can resume from checkpoint after interruption
- **Testing:** 90%+ code coverage, integration tests for all agent types

### NFR3: Usability
- **Configuration:** Simple YAML/JSON config file for generation parameters
- **Monitoring:** Real-time progress dashboard showing generation status and metrics
- **Debugging:** Detailed logging of agent actions for troubleshooting
- **Feedback:** Clear error messages with actionable remediation steps

### NFR4: Security & Privacy
- **Zero PII:** Automated scanning to prevent any real PII in outputs
- **Access Control:** Role-based access to generation system (not required for exported data)
- **Audit Trail:** Complete log of all generation runs and parameters
- **Compliance:** Documentation suitable for regulatory review

### NFR5: Maintainability
- **Modularity:** Agent implementations are independent and can be updated separately
- **Extensibility:** New typologies can be added without modifying core system
- **Observability:** Metrics and logging for all system components
- **Documentation:** Code is well-documented with inline comments and architecture diagrams

---

## Technical Architecture

### System Components

#### 1. Agent Orchestration Layer
- **Technology:** Python + LangChain/CrewAI or custom framework
- **Responsibilities:** Agent lifecycle management, coordination, shared memory access
- **Scalability:** Kubernetes for horizontal scaling of agent pools

#### 2. Shared Memory System
- **Entity Registry:** PostgreSQL with JSONB for flexible profiles
- **Transaction Ledger:** TimescaleDB (PostgreSQL extension) for time-series data
- **Relationship Graph:** Neo4j graph database
- **Configuration:** Redis for distributed locks and coordination
- **Scalability:** Read replicas for transaction ledger, graph sharding for large networks

#### 3. Agent Runtime
- **LLM Backend:** Claude 3.5 Sonnet via Anthropic API (for agent reasoning)
- **Prompt Management:** Version-controlled prompt templates
- **Caching:** Response caching for repeated agent queries
- **Fallbacks:** Deterministic fallbacks for failed LLM calls (use statistical sampling)

#### 4. Validation Pipeline
- **Statistical Tests:** Python (SciPy, statsmodels)
- **Visualization:** Matplotlib, Plotly for validation reports
- **Privacy Scanning:** Regex + ML-based PII detection
- **Orchestration:** Apache Airflow or Prefect for workflow management

#### 5. Export Pipeline
- **Data Processing:** Pandas, Polars for transformations
- **Serialization:** Parquet (PyArrow), CSV, JSON writers
- **Compression:** GZIP for archives
- **Storage:** S3-compatible object storage for dataset registry

### Data Schemas

#### Entity Schema (JSON)
```json
{
  "entity_id": "IND_0001",
  "entity_type": "individual",
  "profile": {
    "demographics": {
      "age": 35,
      "gender": "F",
      "location": {"city": "Austin", "state": "TX", "country": "US"},
      "occupation": "Software Engineer",
      "education": "Bachelors"
    },
    "financial": {
      "annual_income": 125000,
      "net_worth": 250000,
      "credit_score": 780
    },
    "behavioral": {
      "banking_frequency": "daily",
      "risk_tolerance": "moderate",
      "digital_savvy": "high"
    }
  },
  "accounts": ["CHK_0001", "SAV_0001", "INV_0001"],
  "created_date": "2020-01-15"
}
```

#### Transaction Schema (CSV)
```
transaction_id,timestamp,from_account,to_account,amount,currency,type,channel,merchant_category,location,status
TXN_000001,2024-03-15T14:32:11Z,CHK_0001,CHK_0542,250.00,USD,transfer,online,,US-TX-Austin,completed
TXN_000002,2024-03-15T18:45:33Z,CHK_0001,,45.67,USD,card_purchase,pos,grocery,US-TX-Austin,completed
```

#### Ground Truth Label Schema (JSON)
```json
{
  "scenario_id": "SUSP_AML_0001",
  "typology": "structuring",
  "sophistication_level": "moderate",
  "severity_score": 7.5,
  "timeline": {
    "start_date": "2024-03-01",
    "end_date": "2024-03-15",
    "key_events": [
      {"date": "2024-03-01", "description": "Pattern initiation"},
      {"date": "2024-03-15", "description": "Pattern completion"}
    ]
  },
  "involved_entities": [
    {"entity_id": "IND_0042", "role": "primary"},
    {"entity_id": "IND_0043", "role": "smurf"},
    {"entity_id": "IND_0044", "role": "smurf"}
  ],
  "involved_accounts": ["CHK_0123", "CHK_0124", "CHK_0125"],
  "transaction_ids": ["TXN_045123", "TXN_045234", "TXN_045345"],
  "pattern_description": "Multiple deposits just under $10K threshold across 3 accounts over 2 weeks",
  "detection_hints": ["amount_structuring", "temporal_clustering", "network_coordination"]
}
```

---

## Development Roadmap

### Phase 1: Foundation (Weeks 1-4)
**Goal:** Prove core agent concept with minimal viable dataset

**Deliverables:**
- Individual Profile Agent (1,000 entities)
- Retail Banking Agent (100K normal transactions)
- Structuring Typology Agent (100 obvious cases)
- Basic validation pipeline
- CSV export capability

**Success Criteria:**
- Can generate complete dataset end-to-end
- Transactions pass basic consistency checks
- Simple rule-based detector catches >90% of structuring cases

### Phase 2: Scale & Quality (Weeks 5-8)
**Goal:** Expand to production-scale data with quality assurance

**Deliverables:**
- Company Profile Agent (5,000 entities)
- Business Banking Agent
- Network Generation Agent
- Statistical validation pipeline
- Validation dashboard
- Parquet export for large datasets

**Success Criteria:**
- Generate 1M+ transactions with 10K entities
- All statistical tests pass
- Validation report generated automatically
- Can reproduce datasets from configuration

### Phase 3: Typology Expansion (Weeks 9-12)
**Goal:** Cover major AML and insider trading typologies

**Deliverables:**
- AML Agent: Layering, trade-based ML
- Insider Trading Agent: Pre-announcement, tipping
- Investment Transaction Agent
- Sophistication level controls
- Enhanced ground truth labels

**Success Criteria:**
- 5+ typologies implemented
- Each typology has 3 sophistication levels
- Detection difficulty correlates with sophistication
- Ground truth labels validated by SMEs

### Phase 4: Polish & Distribution (Weeks 13-16)
**Goal:** Production-ready system with documentation and examples

**Deliverables:**
- International Transaction Agent
- Market Manipulation Agent (if time permits)
- Comprehensive documentation
- Tutorial notebooks
- Sample datasets (small/medium/large)
- Dataset registry and versioning
- Performance optimization

**Success Criteria:**
- Generate 10M transactions in <1 hour
- Documentation complete and reviewed
- 3 reference datasets published
- System handed off to operations team

---

## Success Metrics & KPIs

### Development Phase Metrics
- **Agent Development Velocity:** Agents implemented per week (target: 2-3)
- **Test Coverage:** Code coverage percentage (target: >90%)
- **Bug Resolution Time:** Average time to fix defects (target: <2 days)

### Data Quality Metrics
- **Statistical Validity:** Percentage of distributions passing tests (target: 100%)
- **Consistency Rate:** Percentage of transactions with zero consistency violations (target: 100%)
- **Privacy Score:** PII detection false positive rate (target: 0%)
- **Label Completeness:** Percentage of suspicious scenarios with complete labels (target: 100%)

### System Performance Metrics
- **Generation Throughput:** Transactions generated per minute (target: >10K)
- **Agent Utilization:** Percentage of time agents are actively generating (target: >80%)
- **Memory Efficiency:** Peak memory / dataset size ratio (target: <2x)
- **Error Rate:** Percentage of generation runs with failures (target: <1%)

### Business Impact Metrics
- **Development Cycle Reduction:** Time saved vs. real data acquisition (target: 60% reduction)
- **Dataset Usage:** Number of teams/projects using synthetic data (target: 5+)
- **Detection Model Performance:** F1 score improvement on synthetic-trained models (baseline TBD)
- **Cost Savings:** Cost of synthetic generation vs. real data licensing (target: 80% savings)

---

## Risk Assessment & Mitigation

### Technical Risks

**Risk 1: Agent Output Quality Insufficient**
- **Probability:** Medium
- **Impact:** High
- **Mitigation:** 
  - Start with simple agents and iterate based on validation metrics
  - Implement deterministic fallbacks for critical components
  - Use few-shot examples and detailed prompts
  - Regular SME review of outputs

**Risk 2: LLM API Costs Exceed Budget**
- **Probability:** Medium
- **Impact:** Medium
- **Mitigation:**
  - Implement aggressive caching for repeated queries
  - Use smaller/cheaper models for simple tasks (profile generation)
  - Monitor token usage and optimize prompts
  - Build hybrid system with deterministic components where possible

**Risk 3: Performance Does Not Meet Scale Requirements**
- **Probability:** Low
- **Impact:** High
- **Mitigation:**
  - Early performance benchmarking and profiling
  - Horizontal scaling architecture from day 1
  - Optimize hot paths (transaction generation)
  - Use efficient data structures (streaming, batch processing)

**Risk 4: Privacy Validation Misses Real Data Leakage**
- **Probability:** Low
- **Impact:** Critical
- **Mitigation:**
  - Multiple layers of privacy scanning (automated + manual)
  - Never train on or reference real customer data
  - Regular privacy audits
  - Legal/compliance review before any data sharing

### Business Risks

**Risk 5: Synthetic Data Not Realistic Enough for Production Use**
- **Probability:** Medium
- **Impact:** High
- **Mitigation:**
  - Continuous validation against real-world statistical benchmarks
  - SME review at each phase
  - A/B testing: models trained on synthetic vs. real data
  - Gradual rollout with production validation

**Risk 6: Regulatory Concerns About Synthetic Data Usage**
- **Probability:** Low
- **Impact:** Medium
- **Mitigation:**
  - Engage compliance and legal early in design
  - Document methodology thoroughly
  - Publish whitepaper on approach
  - Obtain external audit/certification if needed

**Risk 7: Team Lacks Domain Expertise in Financial Crime**
- **Probability:** Low
- **Impact:** Medium
- **Mitigation:**
  - Hire or contract compliance SMEs
  - Partner with industry experts
  - Use established typology frameworks (FATF, FinCEN)
  - Validate scenarios with practitioners

---

## Open Questions & Decisions Needed

### Technical Decisions
1. **LLM Provider:** Anthropic Claude vs. OpenAI GPT-4 vs. hybrid approach?
   - **Recommendation:** Start with Claude 3.5 Sonnet for quality, evaluate GPT-4 for cost optimization
   
2. **Agent Framework:** LangChain vs. CrewAI vs. custom implementation?
   - **Recommendation:** Start with LangChain for rapid prototyping, refactor to custom if needed

3. **Database Technology:** PostgreSQL + Neo4j vs. single graph database (e.g., TigerGraph)?
   - **Recommendation:** PostgreSQL + Neo4j for proven scalability and ecosystem

4. **Deployment Platform:** AWS vs. GCP vs. Azure?
   - **Recommendation:** Cloud-agnostic design, deploy to company's existing cloud provider

### Business Decisions
5. **Dataset Licensing:** Open source vs. proprietary vs. hybrid?
   - **Options:** MIT license (fully open), commercial license (paid), freemium (small datasets free)
   - **Decision Needed:** Week 2

6. **Target Users:** Internal only vs. external distribution?
   - **Options:** Internal R&D only, sell to financial institutions, open source for community
   - **Decision Needed:** Week 1

7. **Quality Bar:** Research-grade vs. production-grade?
   - **Trade-off:** Speed to market vs. quality/realism
   - **Decision Needed:** Week 1

### Scope Decisions
8. **Cryptocurrency Transactions:** In scope for Phase 1-4?
   - **Recommendation:** Out of scope for MVP, add in Phase 5 if demand exists

9. **Fraud Typologies:** Priority level?
   - **Recommendation:** P2 (nice to have), focus on AML and insider trading first

10. **Multi-Jurisdiction Support:** US-only vs. international?
    - **Recommendation:** Start US-only, add EU/APAC in Phase 5

---

## Appendix

### A. Glossary

- **AML:** Anti-Money Laundering
- **Entity:** A person, company, or legal entity in the synthetic dataset
- **Ground Truth:** Known labels for suspicious activities (what is actually suspicious vs. what a model detects)
- **Layering:** Money laundering technique involving complex fund movements to obscure origin
- **MNPI:** Material Non-Public Information (relevant to insider trading)
- **Smurfing:** Using multiple people to conduct transactions below reporting thresholds
- **Structuring:** Breaking up large transactions to avoid regulatory reporting thresholds
- **Typology:** A category or pattern of suspicious activity (e.g., structuring is a typology)

### B. Reference Documents

- FATF Recommendations (Financial Action Task Force)
- FinCEN SAR Narratives and Examples
- SEC Insider Trading Guidelines
- Basel AML Index
- [Company] Internal Compliance Policies

### C. Stakeholder Contact List

- **Product Owner:** [Name, email]
- **Technical Lead:** [Name, email]
- **Compliance SME:** [Name, email]
- **Data Science Lead:** [Name, email]
- **Legal Counsel:** [Name, email]

### D. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-17 | Product Team | Initial draft for review |

---

## Approval Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | | | |
| Engineering Lead | | | |
| Compliance Lead | | | |
| Legal Counsel | | | |