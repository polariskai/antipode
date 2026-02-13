-- ============================================================================
-- Antipode Bank Data Schema - PostgreSQL DDL
-- Version: 1.0
-- Created: 2026-01-26
--
-- This schema separates RAW TABLES (source-of-truth from core banking) from
-- DERIVED TABLES (computed by analytics/ML pipelines)
-- ============================================================================

-- Drop existing tables (for clean setup)
DROP TABLE IF EXISTS CorridorAnalysis CASCADE;
DROP TABLE IF EXISTS CounterpartyProfile CASCADE;
DROP TABLE IF EXISTS NetworkMetrics CASCADE;
DROP TABLE IF EXISTS CustomerRiskProfile CASCADE;
DROP TABLE IF EXISTS TransactionAggregation CASCADE;
DROP TABLE IF EXISTS AccountSignals CASCADE;
DROP TABLE IF EXISTS Alert CASCADE;
DROP TABLE IF EXISTS NewsEvent CASCADE;
DROP TABLE IF EXISTS CustomerRelationship CASCADE;
DROP TABLE IF EXISTS Transaction CASCADE;
DROP TABLE IF EXISTS Counterparty CASCADE;
DROP TABLE IF EXISTS AccountOwnership CASCADE;
DROP TABLE IF EXISTS Account CASCADE;
DROP TABLE IF EXISTS CustomerIdentifier CASCADE;
DROP TABLE IF EXISTS CustomerAddress CASCADE;
DROP TABLE IF EXISTS CompanyOfficer CASCADE;
DROP TABLE IF EXISTS CustomerCompany CASCADE;
DROP TABLE IF EXISTS CustomerPerson CASCADE;
DROP TABLE IF EXISTS Customer CASCADE;

-- ============================================================================
-- ENUMS AND TYPES
-- ============================================================================

CREATE TYPE customer_type_enum AS ENUM ('PERSON', 'COMPANY');
CREATE TYPE customer_status_enum AS ENUM ('ACTIVE', 'DORMANT', 'CLOSED', 'BLOCKED');
CREATE TYPE risk_rating_enum AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE customer_segment_enum AS ENUM ('RETAIL', 'HNW', 'SMB', 'CORPORATE', 'CORRESPONDENT', 'PEP');
CREATE TYPE gender_enum AS ENUM ('MALE', 'FEMALE', 'OTHER', 'UNDISCLOSED');
CREATE TYPE pep_type_enum AS ENUM ('NONE', 'DOMESTIC', 'FOREIGN', 'INTERNATIONAL_ORG', 'FAMILY_MEMBER', 'CLOSE_ASSOCIATE');
CREATE TYPE pep_status_enum AS ENUM ('NOT_PEP', 'CURRENT', 'FORMER');
CREATE TYPE fatca_status_enum AS ENUM ('US_PERSON', 'NON_US', 'RECALCITRANT');
CREATE TYPE crs_status_enum AS ENUM ('REPORTABLE', 'NON_REPORTABLE');
CREATE TYPE company_type_enum AS ENUM ('PUBLIC', 'PRIVATE', 'SMB', 'CORPORATE', 'NGO', 'MSB', 'SHELL', 'SPV');
CREATE TYPE company_status_enum AS ENUM ('ACTIVE', 'DORMANT', 'DISSOLVED', 'SUSPENDED', 'LIQUIDATION');
CREATE TYPE officer_role_enum AS ENUM ('DIRECTOR', 'CEO', 'CFO', 'SECRETARY', 'UBO', 'AUTHORIZED_SIGNATORY');
CREATE TYPE address_type_enum AS ENUM ('RESIDENTIAL', 'MAILING', 'REGISTERED', 'OPERATIONAL', 'BILLING');
CREATE TYPE id_type_enum AS ENUM ('PASSPORT', 'NATIONAL_ID', 'DRIVERS_LICENSE', 'TAX_ID', 'SSN', 'COMPANY_REG', 'LEI', 'BIC');
CREATE TYPE product_type_enum AS ENUM ('CHECKING', 'SAVINGS', 'MONEY_MARKET', 'BUSINESS_CHECKING', 'BUSINESS_SAVINGS', 'TREASURY', 'BROKERAGE', 'LOAN', 'CREDIT_CARD', 'NOSTRO', 'VOSTRO');
CREATE TYPE account_status_enum AS ENUM ('ACTIVE', 'DORMANT', 'SUSPENDED', 'CLOSED', 'PENDING');
CREATE TYPE ownership_type_enum AS ENUM ('PRIMARY', 'JOINT', 'BENEFICIAL', 'AUTHORIZED_SIGNATORY', 'CORPORATE');
CREATE TYPE signing_authority_enum AS ENUM ('SOLE', 'JOINT_ANY', 'JOINT_ALL', 'NONE');
CREATE TYPE txn_direction_enum AS ENUM ('CREDIT', 'DEBIT');
CREATE TYPE txn_type_enum AS ENUM ('WIRE', 'ACH', 'CASH_DEPOSIT', 'CASH_WITHDRAWAL', 'CHECK', 'CARD', 'INTERNAL_TRANSFER', 'FX', 'SECURITIES_TRADE', 'LOAN_PAYMENT', 'PAYROLL', 'REMITTANCE');
CREATE TYPE txn_channel_enum AS ENUM ('ONLINE', 'MOBILE', 'BRANCH', 'ATM', 'API', 'SWIFT', 'PHONE');
CREATE TYPE counterparty_type_enum AS ENUM ('PERSON', 'COMPANY', 'BANK', 'GOVERNMENT', 'UNKNOWN');
CREATE TYPE relationship_type_enum AS ENUM ('SPOUSE', 'PARENT', 'CHILD', 'SIBLING', 'EMPLOYER', 'EMPLOYEE', 'DIRECTOR_OF', 'UBO_OF', 'AUTHORIZED_FOR', 'GUARANTOR', 'BUSINESS_PARTNER');
CREATE TYPE news_category_enum AS ENUM ('FRAUD', 'BRIBERY', 'MONEY_LAUNDERING', 'SANCTIONS', 'TAX_EVASION', 'REGULATORY_ACTION', 'LITIGATION', 'BANKRUPTCY', 'ENVIRONMENTAL', 'OTHER');
CREATE TYPE severity_enum AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE source_credibility_enum AS ENUM ('OFFICIAL', 'MAJOR_NEWS', 'TRADE_PRESS', 'BLOG', 'SOCIAL', 'UNKNOWN');
CREATE TYPE news_status_enum AS ENUM ('ACTIVE', 'RESOLVED', 'DISMISSED', 'UNDER_INVESTIGATION');
CREATE TYPE alert_status_enum AS ENUM ('NEW', 'IN_PROGRESS', 'ESCALATED', 'CLOSED_SAR', 'CLOSED_NO_SAR', 'FALSE_POSITIVE');
CREATE TYPE disposition_reason_enum AS ENUM ('LEGITIMATE_ACTIVITY', 'INSUFFICIENT_EVIDENCE', 'CONFIRMED_SUSPICIOUS', 'CUSTOMER_EXPLAINED', 'DUPLICATE');
CREATE TYPE period_type_enum AS ENUM ('DAILY', 'WEEKLY', 'MONTHLY');
CREATE TYPE entity_type_enum AS ENUM ('CUSTOMER', 'ACCOUNT', 'COUNTERPARTY');

-- ============================================================================
-- RAW TABLES
-- ============================================================================

-- 1. Customer (Base Entity Table)
-- ============================================================================
CREATE TABLE Customer (
    customer_id VARCHAR(20) PRIMARY KEY,
    customer_type customer_type_enum NOT NULL,
    onboarding_date DATE NOT NULL,
    status customer_status_enum NOT NULL DEFAULT 'ACTIVE',
    risk_rating risk_rating_enum NOT NULL DEFAULT 'MEDIUM',
    segment customer_segment_enum NOT NULL,
    relationship_manager_id VARCHAR(20),
    kyc_date DATE,
    next_review_date DATE,
    source_system VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_customer_type ON Customer(customer_type);
CREATE INDEX idx_customer_status ON Customer(status);
CREATE INDEX idx_customer_segment ON Customer(segment);
CREATE INDEX idx_customer_risk ON Customer(risk_rating);

COMMENT ON TABLE Customer IS 'Unified customer table with type discriminator';

-- 2. CustomerPerson (Natural Person Details)
-- ============================================================================
CREATE TABLE CustomerPerson (
    customer_id VARCHAR(20) PRIMARY KEY REFERENCES Customer(customer_id) ON DELETE CASCADE,
    title VARCHAR(10),
    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    last_name VARCHAR(100) NOT NULL,
    full_name VARCHAR(300) NOT NULL,
    date_of_birth DATE NOT NULL,
    nationality CHAR(2) NOT NULL,
    country_of_residence CHAR(2) NOT NULL,
    country_of_birth CHAR(2),
    gender gender_enum,
    occupation VARCHAR(100),
    employer VARCHAR(200),
    industry VARCHAR(100),
    annual_income DECIMAL(18,2),
    source_of_wealth VARCHAR(500),
    is_pep BOOLEAN DEFAULT FALSE,
    pep_type pep_type_enum DEFAULT 'NONE',
    pep_status pep_status_enum DEFAULT 'NOT_PEP',
    pep_position VARCHAR(200),
    pep_country CHAR(2),
    tax_residency CHAR(2),
    fatca_status fatca_status_enum,
    crs_status crs_status_enum
);

CREATE INDEX idx_person_name ON CustomerPerson(last_name, first_name);
CREATE INDEX idx_person_dob ON CustomerPerson(date_of_birth);
CREATE INDEX idx_person_pep ON CustomerPerson(is_pep) WHERE is_pep = TRUE;

COMMENT ON TABLE CustomerPerson IS 'Extended attributes for individual customers';

-- 3. CustomerCompany (Legal Entity Details)
-- ============================================================================
CREATE TABLE CustomerCompany (
    customer_id VARCHAR(20) PRIMARY KEY REFERENCES Customer(customer_id) ON DELETE CASCADE,
    legal_name VARCHAR(300) NOT NULL,
    trading_name VARCHAR(300),
    company_type company_type_enum NOT NULL,
    legal_form VARCHAR(50),
    registration_number VARCHAR(100),
    registration_country CHAR(2) NOT NULL,
    registration_date DATE,
    tax_id VARCHAR(50),
    lei CHAR(20),
    industry_code VARCHAR(20),
    industry_description VARCHAR(200),
    operational_countries VARCHAR(500),
    employee_count INTEGER,
    annual_revenue DECIMAL(18,2),
    website VARCHAR(200),
    status company_status_enum DEFAULT 'ACTIVE',
    is_regulated BOOLEAN DEFAULT FALSE,
    regulator VARCHAR(200),
    license_number VARCHAR(100),
    is_listed BOOLEAN DEFAULT FALSE,
    stock_exchange VARCHAR(50),
    ticker_symbol VARCHAR(20)
);

CREATE INDEX idx_company_name ON CustomerCompany(legal_name);
CREATE INDEX idx_company_reg_country ON CustomerCompany(registration_country);
CREATE INDEX idx_company_type ON CustomerCompany(company_type);
CREATE INDEX idx_company_status ON CustomerCompany(status);

COMMENT ON TABLE CustomerCompany IS 'Extended attributes for corporate customers';

-- 4. CompanyOfficer (Company Directors/Officers)
-- ============================================================================
CREATE TABLE CompanyOfficer (
    officer_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL REFERENCES CustomerCompany(customer_id) ON DELETE CASCADE,
    person_customer_id VARCHAR(20) REFERENCES CustomerPerson(customer_id),
    full_name VARCHAR(300) NOT NULL,
    role officer_role_enum NOT NULL,
    date_of_birth DATE,
    nationality CHAR(2),
    appointment_date DATE,
    resignation_date DATE,
    ownership_percentage DECIMAL(5,2),
    is_ubo BOOLEAN DEFAULT FALSE,
    is_pep BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_officer_customer ON CompanyOfficer(customer_id);
CREATE INDEX idx_officer_person ON CompanyOfficer(person_customer_id);
CREATE INDEX idx_officer_ubo ON CompanyOfficer(is_ubo) WHERE is_ubo = TRUE;

COMMENT ON TABLE CompanyOfficer IS 'Key personnel for corporate customers';

-- 5. CustomerAddress
-- ============================================================================
CREATE TABLE CustomerAddress (
    address_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL REFERENCES Customer(customer_id) ON DELETE CASCADE,
    address_type address_type_enum NOT NULL,
    address_line_1 VARCHAR(200) NOT NULL,
    address_line_2 VARCHAR(200),
    city VARCHAR(100) NOT NULL,
    state_province VARCHAR(100),
    postal_code VARCHAR(20),
    country CHAR(2) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    verified_date DATE,
    effective_from DATE NOT NULL,
    effective_to DATE
);

CREATE INDEX idx_address_customer ON CustomerAddress(customer_id);
CREATE INDEX idx_address_country ON CustomerAddress(country);

COMMENT ON TABLE CustomerAddress IS 'Addresses for both persons and companies';

-- 6. CustomerIdentifier
-- ============================================================================
CREATE TABLE CustomerIdentifier (
    identifier_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL REFERENCES Customer(customer_id) ON DELETE CASCADE,
    id_type id_type_enum NOT NULL,
    id_number VARCHAR(100) NOT NULL,
    issuing_country CHAR(2) NOT NULL,
    issuing_authority VARCHAR(200),
    issue_date DATE,
    expiry_date DATE,
    is_primary BOOLEAN DEFAULT FALSE,
    verified BOOLEAN DEFAULT FALSE,
    verification_date DATE,
    verification_method VARCHAR(50)
);

CREATE INDEX idx_identifier_customer ON CustomerIdentifier(customer_id);
CREATE INDEX idx_identifier_type ON CustomerIdentifier(id_type);

COMMENT ON TABLE CustomerIdentifier IS 'Identity documents for customers';

-- 7. Account
-- ============================================================================
CREATE TABLE Account (
    account_id VARCHAR(20) PRIMARY KEY,
    account_number VARCHAR(34) UNIQUE NOT NULL,
    product_type product_type_enum NOT NULL,
    product_name VARCHAR(100),
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    country CHAR(2) NOT NULL,
    branch_code VARCHAR(20),
    branch_name VARCHAR(100),
    open_date DATE NOT NULL,
    close_date DATE,
    status account_status_enum NOT NULL DEFAULT 'ACTIVE',
    purpose VARCHAR(500),
    declared_monthly_turnover DECIMAL(18,2),
    declared_source_of_funds VARCHAR(500),
    is_joint BOOLEAN DEFAULT FALSE,
    is_high_risk BOOLEAN DEFAULT FALSE,
    kyc_date DATE,
    next_review_date DATE,
    source_system VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_account_status ON Account(status);
CREATE INDEX idx_account_product ON Account(product_type);
CREATE INDEX idx_account_country ON Account(country);
CREATE INDEX idx_account_number ON Account(account_number);

COMMENT ON TABLE Account IS 'Bank accounts';

-- 8. AccountOwnership
-- ============================================================================
CREATE TABLE AccountOwnership (
    ownership_id VARCHAR(20) PRIMARY KEY,
    account_id VARCHAR(20) NOT NULL REFERENCES Account(account_id) ON DELETE CASCADE,
    customer_id VARCHAR(20) NOT NULL REFERENCES Customer(customer_id) ON DELETE CASCADE,
    ownership_type ownership_type_enum NOT NULL,
    ownership_percentage DECIMAL(5,2) DEFAULT 100.00,
    signing_authority signing_authority_enum DEFAULT 'SOLE',
    daily_limit DECIMAL(18,2),
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_ownership_account ON AccountOwnership(account_id);
CREATE INDEX idx_ownership_customer ON AccountOwnership(customer_id);
CREATE INDEX idx_ownership_active ON AccountOwnership(is_active) WHERE is_active = TRUE;

COMMENT ON TABLE AccountOwnership IS 'Junction table for account ownership (supports joint accounts)';

-- 9. Counterparty
-- ============================================================================
CREATE TABLE Counterparty (
    counterparty_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    type counterparty_type_enum DEFAULT 'UNKNOWN',
    account_number VARCHAR(34),
    bank_code VARCHAR(11),
    bank_name VARCHAR(200),
    country CHAR(2),
    first_seen_date DATE,
    last_seen_date DATE,
    txn_count INTEGER DEFAULT 0,
    total_volume_usd DECIMAL(18,2) DEFAULT 0,
    source_system VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_counterparty_name ON Counterparty(name);
CREATE INDEX idx_counterparty_country ON Counterparty(country);
CREATE INDEX idx_counterparty_bank_code ON Counterparty(bank_code);

COMMENT ON TABLE Counterparty IS 'External parties involved in transactions';

-- 10. Transaction
-- ============================================================================
CREATE TABLE Transaction (
    txn_id VARCHAR(36) PRIMARY KEY,
    txn_ref VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    value_date DATE NOT NULL,
    posting_date DATE NOT NULL,
    account_id VARCHAR(20) NOT NULL REFERENCES Account(account_id),
    direction txn_direction_enum NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    amount_usd DECIMAL(18,2),
    exchange_rate DECIMAL(18,8),
    txn_type txn_type_enum NOT NULL,
    channel txn_channel_enum,

    -- Counterparty Details
    counterparty_id VARCHAR(20) REFERENCES Counterparty(counterparty_id),
    counterparty_account_number VARCHAR(34),
    counterparty_name_raw VARCHAR(300),
    counterparty_bank_code VARCHAR(11),
    counterparty_bank_name VARCHAR(200),
    counterparty_country CHAR(2),

    -- Originator Details (for wires)
    originator_name VARCHAR(300),
    originator_address VARCHAR(500),
    originator_account VARCHAR(34),
    originator_country CHAR(2),

    -- Beneficiary Details (for wires)
    beneficiary_name VARCHAR(300),
    beneficiary_address VARCHAR(500),
    beneficiary_account VARCHAR(34),
    beneficiary_country CHAR(2),

    -- Payment Details
    purpose_code VARCHAR(10),
    purpose_description VARCHAR(500),
    reference VARCHAR(140),
    end_to_end_id VARCHAR(35),

    -- Metadata
    batch_id VARCHAR(36),
    source_system VARCHAR(50),
    is_reversed BOOLEAN DEFAULT FALSE,
    reversal_of_txn_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ground Truth (synthetic data only - prefixed with _)
    _is_suspicious BOOLEAN,
    _typology VARCHAR(50),
    _scenario_id VARCHAR(36)
);

CREATE INDEX idx_txn_account ON Transaction(account_id);
CREATE INDEX idx_txn_timestamp ON Transaction(timestamp);
CREATE INDEX idx_txn_value_date ON Transaction(value_date);
CREATE INDEX idx_txn_counterparty ON Transaction(counterparty_id);
CREATE INDEX idx_txn_date_account ON Transaction(value_date, account_id);
CREATE INDEX idx_txn_type ON Transaction(txn_type);
CREATE INDEX idx_txn_direction ON Transaction(direction);
CREATE INDEX idx_txn_scenario ON Transaction(_scenario_id) WHERE _scenario_id IS NOT NULL;
CREATE INDEX idx_txn_suspicious ON Transaction(_is_suspicious) WHERE _is_suspicious = TRUE;

COMMENT ON TABLE Transaction IS 'Financial transactions linked to accounts';
COMMENT ON COLUMN Transaction._is_suspicious IS 'Ground truth: Synthetic data only';
COMMENT ON COLUMN Transaction._typology IS 'Ground truth: Synthetic data only';
COMMENT ON COLUMN Transaction._scenario_id IS 'Ground truth: Links to scenario generation';

-- 11. CustomerRelationship
-- ============================================================================
CREATE TABLE CustomerRelationship (
    relationship_id VARCHAR(20) PRIMARY KEY,
    from_customer_id VARCHAR(20) NOT NULL REFERENCES Customer(customer_id) ON DELETE CASCADE,
    to_customer_id VARCHAR(20) NOT NULL REFERENCES Customer(customer_id) ON DELETE CASCADE,
    relationship_type relationship_type_enum NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    verified BOOLEAN DEFAULT FALSE,
    verification_date DATE,
    notes VARCHAR(500)
);

CREATE INDEX idx_relationship_from ON CustomerRelationship(from_customer_id);
CREATE INDEX idx_relationship_to ON CustomerRelationship(to_customer_id);
CREATE INDEX idx_relationship_type ON CustomerRelationship(relationship_type);

COMMENT ON TABLE CustomerRelationship IS 'Relationships between customers';

-- 12. NewsEvent
-- ============================================================================
CREATE TABLE NewsEvent (
    event_id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(20) REFERENCES Customer(customer_id),
    entity_name VARCHAR(300) NOT NULL,
    headline VARCHAR(500) NOT NULL,
    summary TEXT,
    category news_category_enum NOT NULL,
    severity severity_enum NOT NULL,
    source VARCHAR(200),
    source_url VARCHAR(500),
    source_credibility source_credibility_enum DEFAULT 'UNKNOWN',
    event_date DATE,
    published_date DATE NOT NULL,
    countries_involved VARCHAR(100),
    amount_involved DECIMAL(18,2),
    status news_status_enum DEFAULT 'ACTIVE',
    match_confidence DECIMAL(3,2),
    verified_match BOOLEAN DEFAULT FALSE,
    source_system VARCHAR(50)
);

CREATE INDEX idx_news_customer ON NewsEvent(customer_id);
CREATE INDEX idx_news_category ON NewsEvent(category);
CREATE INDEX idx_news_severity ON NewsEvent(severity);
CREATE INDEX idx_news_published ON NewsEvent(published_date);

COMMENT ON TABLE NewsEvent IS 'Adverse media and news events linked to entities';

-- 13. Alert
-- ============================================================================
CREATE TABLE Alert (
    alert_id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(20) REFERENCES Account(account_id),
    customer_id VARCHAR(20) REFERENCES Customer(customer_id),
    alert_type VARCHAR(100) NOT NULL,
    risk_level severity_enum NOT NULL,
    score DECIMAL(5,2),
    status alert_status_enum NOT NULL DEFAULT 'NEW',
    assigned_to VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date DATE,
    closed_at TIMESTAMP,
    disposition_reason disposition_reason_enum,
    narrative TEXT,
    sar_filed BOOLEAN DEFAULT FALSE,
    sar_filing_date DATE,
    scenario_id VARCHAR(36)
);

CREATE INDEX idx_alert_account ON Alert(account_id);
CREATE INDEX idx_alert_customer ON Alert(customer_id);
CREATE INDEX idx_alert_status ON Alert(status);
CREATE INDEX idx_alert_type ON Alert(alert_type);
CREATE INDEX idx_alert_risk ON Alert(risk_level);
CREATE INDEX idx_alert_created ON Alert(created_at);

COMMENT ON TABLE Alert IS 'AML/TM alerts generated by detection systems';

-- R14. AlertTransaction (Junction Table)
-- ============================================================================
CREATE TABLE AlertTransaction (
    alert_txn_id VARCHAR(36) PRIMARY KEY,
    alert_id VARCHAR(36) NOT NULL REFERENCES Alert(alert_id) ON DELETE CASCADE,
    txn_id VARCHAR(36) NOT NULL REFERENCES Transaction(txn_id),
    role VARCHAR(20) NOT NULL DEFAULT 'TRIGGER',  -- TRIGGER, SUPPORTING, RELATED
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(alert_id, txn_id)
);

CREATE INDEX idx_alert_txn_alert ON AlertTransaction(alert_id);
CREATE INDEX idx_alert_txn_txn ON AlertTransaction(txn_id);

COMMENT ON TABLE AlertTransaction IS 'Junction table linking alerts to their triggering/supporting transactions';

-- ============================================================================
-- DERIVED TABLES (Analytics Layer)
-- ============================================================================

-- D1. AccountSignals
-- ============================================================================
CREATE TABLE AccountSignals (
    signal_id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(20) NOT NULL REFERENCES Account(account_id),
    as_of_date DATE NOT NULL,

    -- Volume Signals
    volume_7d DECIMAL(18,2),
    volume_30d DECIMAL(18,2),
    volume_90d DECIMAL(18,2),
    expected_monthly_volume DECIMAL(18,2),
    volume_deviation_pct DECIMAL(8,4),

    -- Velocity Signals
    txn_count_7d INTEGER,
    txn_count_30d INTEGER,
    velocity_zscore_7d DECIMAL(8,4),

    -- Behavioral Signals
    cash_intensity DECIMAL(5,4),
    round_amount_ratio DECIMAL(5,4),
    structuring_score DECIMAL(5,2),
    rapid_movement_score DECIMAL(5,2),

    -- Counterparty Signals
    counterparty_count_30d INTEGER,
    new_counterparty_rate DECIMAL(5,4),
    counterparty_concentration DECIMAL(5,4),

    -- Geographic Signals
    corridor_risk_score DECIMAL(5,2),
    high_risk_country_ratio DECIMAL(5,4),

    -- Metadata
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(account_id, as_of_date)
);

CREATE INDEX idx_signals_account_date ON AccountSignals(account_id, as_of_date);
CREATE INDEX idx_signals_computed ON AccountSignals(computed_at);

COMMENT ON TABLE AccountSignals IS 'Behavioral signals computed per account per time period';

-- D2. TransactionAggregation
-- ============================================================================
CREATE TABLE TransactionAggregation (
    agg_id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(20) NOT NULL REFERENCES Account(account_id),
    period_type period_type_enum NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Volume Metrics
    total_credit_amount DECIMAL(18,2),
    total_debit_amount DECIMAL(18,2),
    net_flow DECIMAL(18,2),
    total_credit_count INTEGER,
    total_debit_count INTEGER,

    -- Size Metrics
    avg_txn_size DECIMAL(18,2),
    max_txn_size DECIMAL(18,2),
    min_txn_size DECIMAL(18,2),
    stddev_txn_size DECIMAL(18,2),

    -- Type Breakdown
    wire_volume DECIMAL(18,2),
    cash_volume DECIMAL(18,2),
    ach_volume DECIMAL(18,2),
    card_volume DECIMAL(18,2),

    -- Counterparty Metrics
    unique_counterparties INTEGER,
    unique_countries INTEGER,

    -- Metadata
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(account_id, period_type, period_start)
);

CREATE INDEX idx_txnagg_account_period ON TransactionAggregation(account_id, period_type, period_start);

COMMENT ON TABLE TransactionAggregation IS 'Pre-aggregated transaction statistics';

-- D3. CustomerRiskProfile
-- ============================================================================
CREATE TABLE CustomerRiskProfile (
    profile_id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(20) NOT NULL REFERENCES Customer(customer_id),
    as_of_date DATE NOT NULL,

    -- Risk Scores
    composite_risk_score DECIMAL(5,2),
    inherent_risk_score DECIMAL(5,2),
    behavioral_risk_score DECIMAL(5,2),
    network_risk_score DECIMAL(5,2),

    -- Component Scores
    geographic_risk DECIMAL(5,2),
    product_risk DECIMAL(5,2),
    channel_risk DECIMAL(5,2),
    counterparty_risk DECIMAL(5,2),

    -- Proximity Scores
    pep_distance INTEGER DEFAULT 99,
    sanctions_distance INTEGER DEFAULT 99,
    adverse_media_score DECIMAL(5,2),

    -- Cluster Info
    cluster_id VARCHAR(36),
    cluster_risk_score DECIMAL(5,2),

    -- Model Info
    model_version VARCHAR(50),
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(customer_id, as_of_date)
);

CREATE INDEX idx_riskprofile_customer ON CustomerRiskProfile(customer_id, as_of_date);
CREATE INDEX idx_riskprofile_score ON CustomerRiskProfile(composite_risk_score);

COMMENT ON TABLE CustomerRiskProfile IS 'Computed risk profile per customer';

-- D4. NetworkMetrics
-- ============================================================================
CREATE TABLE NetworkMetrics (
    metric_id VARCHAR(36) PRIMARY KEY,
    entity_id VARCHAR(20) NOT NULL,
    entity_type entity_type_enum NOT NULL,
    as_of_date DATE NOT NULL,

    -- Centrality Metrics
    degree_centrality INTEGER,
    in_degree INTEGER,
    out_degree INTEGER,
    betweenness_centrality DECIMAL(8,6),
    closeness_centrality DECIMAL(8,6),
    pagerank DECIMAL(8,6),

    -- Flow Metrics
    total_flow_in DECIMAL(18,2),
    total_flow_out DECIMAL(18,2),
    risk_flow_in DECIMAL(18,2),
    risk_flow_out DECIMAL(18,2),

    -- Community Detection
    community_id VARCHAR(36),
    community_size INTEGER,
    community_risk_score DECIMAL(5,2),

    -- Metadata
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(entity_id, entity_type, as_of_date)
);

CREATE INDEX idx_network_entity ON NetworkMetrics(entity_id, entity_type);
CREATE INDEX idx_network_community ON NetworkMetrics(community_id);

COMMENT ON TABLE NetworkMetrics IS 'Graph-based metrics for entities';

-- D5. CounterpartyProfile
-- ============================================================================
CREATE TABLE CounterpartyProfile (
    profile_id VARCHAR(36) PRIMARY KEY,
    counterparty_id VARCHAR(20) NOT NULL REFERENCES Counterparty(counterparty_id),
    as_of_date DATE NOT NULL,

    -- Activity Metrics
    first_seen_date DATE,
    last_seen_date DATE,
    total_txn_count INTEGER,
    txn_count_30d INTEGER,
    total_volume_usd DECIMAL(18,2),
    volume_30d_usd DECIMAL(18,2),

    -- Risk Indicators
    risk_score DECIMAL(5,2),
    is_high_risk_country BOOLEAN,
    is_shell_indicator BOOLEAN,
    unique_customers INTEGER,

    -- Metadata
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(counterparty_id, as_of_date)
);

CREATE INDEX idx_cptyprofile_counterparty ON CounterpartyProfile(counterparty_id, as_of_date);
CREATE INDEX idx_cptyprofile_risk ON CounterpartyProfile(risk_score);

COMMENT ON TABLE CounterpartyProfile IS 'Derived profile for counterparties';

-- D6. CorridorAnalysis
-- ============================================================================
CREATE TABLE CorridorAnalysis (
    corridor_id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(20) NOT NULL REFERENCES Account(account_id),
    origin_country CHAR(2) NOT NULL,
    destination_country CHAR(2) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Volume Metrics
    txn_count INTEGER,
    total_volume_usd DECIMAL(18,2),
    avg_txn_size_usd DECIMAL(18,2),

    -- Risk Metrics
    corridor_risk_weight DECIMAL(5,2),
    is_unusual BOOLEAN,
    deviation_from_declared DECIMAL(5,2),

    -- Metadata
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(account_id, origin_country, destination_country, period_start)
);

CREATE INDEX idx_corridor_account ON CorridorAnalysis(account_id);
CREATE INDEX idx_corridor_countries ON CorridorAnalysis(origin_country, destination_country);

COMMENT ON TABLE CorridorAnalysis IS 'Geographic flow corridor analysis';

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_customer_updated_at
    BEFORE UPDATE ON Customer
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_account_updated_at
    BEFORE UPDATE ON Account
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_counterparty_updated_at
    BEFORE UPDATE ON Counterparty
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Complete customer view (person or company)
CREATE OR REPLACE VIEW vw_customer_complete AS
SELECT
    c.customer_id,
    c.customer_type,
    c.onboarding_date,
    c.status,
    c.risk_rating,
    c.segment,
    COALESCE(p.full_name, co.legal_name) as customer_name,
    p.nationality,
    co.registration_country,
    c.relationship_manager_id,
    c.kyc_date,
    c.next_review_date
FROM Customer c
LEFT JOIN CustomerPerson p ON c.customer_id = p.customer_id
LEFT JOIN CustomerCompany co ON c.customer_id = co.customer_id;

COMMENT ON VIEW vw_customer_complete IS 'Unified view of customers with key details';

-- Account with primary owner
CREATE OR REPLACE VIEW vw_account_with_owner AS
SELECT
    a.account_id,
    a.account_number,
    a.product_type,
    a.currency,
    a.status,
    a.open_date,
    ao.customer_id as primary_customer_id,
    COALESCE(p.full_name, co.legal_name) as primary_customer_name,
    c.risk_rating as customer_risk_rating
FROM Account a
JOIN AccountOwnership ao ON a.account_id = ao.account_id AND ao.ownership_type = 'PRIMARY'
JOIN Customer c ON ao.customer_id = c.customer_id
LEFT JOIN CustomerPerson p ON c.customer_id = p.customer_id
LEFT JOIN CustomerCompany co ON c.customer_id = co.customer_id;

COMMENT ON VIEW vw_account_with_owner IS 'Accounts with primary owner details';

-- ============================================================================
-- GRANTS (Example - adjust for your roles)
-- ============================================================================

-- Create application user role
-- CREATE ROLE bank_app_user WITH LOGIN PASSWORD 'your_secure_password';

-- Grant read/write on raw tables
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO bank_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bank_app_user;

-- Create analytics role (read-only on raw, read/write on derived)
-- CREATE ROLE bank_analytics WITH LOGIN PASSWORD 'analytics_password';
-- GRANT SELECT ON Customer, CustomerPerson, CustomerCompany, Account, Transaction TO bank_analytics;
-- GRANT ALL ON AccountSignals, TransactionAggregation, CustomerRiskProfile TO bank_analytics;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
