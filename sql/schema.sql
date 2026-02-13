-- ============================================================================
-- PostgreSQL Schema for Adversarial AML System
-- Version: 1.0
-- Created: 2026-01-26
-- ============================================================================

-- Drop existing tables (for clean setup)
DROP TABLE IF EXISTS entity_reuse_log CASCADE;
DROP TABLE IF EXISTS relationships CASCADE;
DROP TABLE IF EXISTS transaction_ground_truth CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS account_ground_truth CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS entity_ground_truth CASCADE;
DROP TABLE IF EXISTS entities CASCADE;
DROP TABLE IF EXISTS scenario_metadata CASCADE;
DROP TABLE IF EXISTS scenarios CASCADE;

-- ============================================================================
-- 1. SCENARIOS TABLE (Master)
-- ============================================================================

CREATE TABLE scenarios (
    scenario_id VARCHAR(100) PRIMARY KEY,
    typology VARCHAR(50) NOT NULL,
    total_amount DECIMAL(18, 2),
    complexity INTEGER CHECK (complexity BETWEEN 1 AND 10),
    apply_evasion BOOLEAN DEFAULT TRUE,
    scenario_description TEXT,
    num_entities INTEGER,
    num_accounts INTEGER,
    num_transactions INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active'
);

CREATE INDEX idx_scenarios_typology ON scenarios(typology);
CREATE INDEX idx_scenarios_created_at ON scenarios(created_at);
CREATE INDEX idx_scenarios_status ON scenarios(status);

COMMENT ON TABLE scenarios IS 'Master table for AML money laundering scenarios';
COMMENT ON COLUMN scenarios.scenario_description IS 'User-provided custom scenario description';
COMMENT ON COLUMN scenarios.typology IS 'Money laundering typology: structuring, layering, crypto_mixing, etc.';
COMMENT ON COLUMN scenarios.status IS 'Scenario status: active, completed, archived';

-- ============================================================================
-- 2. SCENARIO METADATA (Ground Truth)
-- ============================================================================

CREATE TABLE scenario_metadata (
    id SERIAL PRIMARY KEY,
    scenario_id VARCHAR(100) UNIQUE REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    plan_steps JSONB,
    evasion_techniques JSONB,
    validation_results JSONB,
    memory_stats JSONB,
    metadata JSONB
);

CREATE INDEX idx_scenario_metadata_scenario ON scenario_metadata(scenario_id);
CREATE INDEX idx_scenario_metadata_plan ON scenario_metadata USING GIN (plan_steps);

COMMENT ON TABLE scenario_metadata IS 'Scenario planning details and ground truth';

-- ============================================================================
-- 3. ENTITIES (Visible Data)
-- ============================================================================

CREATE TABLE entities (
    entity_id VARCHAR(100) PRIMARY KEY,
    scenario_id VARCHAR(100) REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_subtype VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    country VARCHAR(3),
    created_at TIMESTAMP
);

CREATE INDEX idx_entities_scenario ON entities(scenario_id);
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_country ON entities(country);
CREATE INDEX idx_entities_name ON entities(name);

COMMENT ON TABLE entities IS 'Entity data - VISIBLE ONLY (no ground truth)';
COMMENT ON COLUMN entities.entity_type IS 'Realistic entity types: individual, company, LLC, trust, partnership, foundation';

-- ============================================================================
-- 4. ENTITY GROUND TRUTH (Labels - Separated)
-- ============================================================================

CREATE TABLE entity_ground_truth (
    id SERIAL PRIMARY KEY,
    entity_id VARCHAR(100) UNIQUE REFERENCES entities(entity_id) ON DELETE CASCADE,
    is_shell BOOLEAN DEFAULT FALSE,
    is_nominee BOOLEAN DEFAULT FALSE,
    is_suspicious BOOLEAN DEFAULT TRUE,
    risk_score INTEGER CHECK (risk_score BETWEEN 1 AND 10),
    suspicious_indicators JSONB,
    role_in_scenario VARCHAR(100),
    scenarios_used TEXT[]
);

CREATE INDEX idx_entity_gt_entity ON entity_ground_truth(entity_id);
CREATE INDEX idx_entity_gt_suspicious ON entity_ground_truth(is_suspicious);
CREATE INDEX idx_entity_gt_role ON entity_ground_truth(role_in_scenario);
CREATE INDEX idx_entity_gt_indicators ON entity_ground_truth USING GIN (suspicious_indicators);

-- Partial index for suspicious entities only
CREATE INDEX idx_suspicious_entities ON entity_ground_truth(entity_id) WHERE is_suspicious = TRUE;

COMMENT ON TABLE entity_ground_truth IS 'Entity ground truth labels - SEPARATED from visible data';

-- ============================================================================
-- 5. ACCOUNTS (Visible Data)
-- ============================================================================

CREATE TABLE accounts (
    account_id VARCHAR(100) PRIMARY KEY,
    entity_id VARCHAR(100) REFERENCES entities(entity_id) ON DELETE CASCADE,
    scenario_id VARCHAR(100) REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    account_type VARCHAR(50),
    bank VARCHAR(255),
    country VARCHAR(3),
    currency VARCHAR(3) DEFAULT 'USD',
    opened_date DATE
);

CREATE INDEX idx_accounts_entity ON accounts(entity_id);
CREATE INDEX idx_accounts_scenario ON accounts(scenario_id);
CREATE INDEX idx_accounts_bank ON accounts(bank);
CREATE INDEX idx_accounts_country ON accounts(country);

COMMENT ON TABLE accounts IS 'Bank accounts - VISIBLE DATA ONLY';

-- ============================================================================
-- 6. ACCOUNT GROUND TRUTH (Labels)
-- ============================================================================

CREATE TABLE account_ground_truth (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(100) UNIQUE REFERENCES accounts(account_id) ON DELETE CASCADE,
    is_suspicious BOOLEAN DEFAULT TRUE,
    account_purpose VARCHAR(100),
    metadata JSONB
);

CREATE INDEX idx_account_gt_account ON account_ground_truth(account_id);
CREATE INDEX idx_account_gt_suspicious ON account_ground_truth(is_suspicious);

COMMENT ON TABLE account_ground_truth IS 'Account ground truth labels';

-- ============================================================================
-- 7. TRANSACTIONS (Visible Data)
-- ============================================================================

CREATE TABLE transactions (
    transaction_id VARCHAR(100) PRIMARY KEY,
    scenario_id VARCHAR(100) REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    from_account_id VARCHAR(100) REFERENCES accounts(account_id),
    to_account_id VARCHAR(100) REFERENCES accounts(account_id),
    amount DECIMAL(18, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    timestamp TIMESTAMP NOT NULL,
    description TEXT,
    transaction_type VARCHAR(50)
);

CREATE INDEX idx_txn_scenario ON transactions(scenario_id);
CREATE INDEX idx_txn_from_account ON transactions(from_account_id);
CREATE INDEX idx_txn_to_account ON transactions(to_account_id);
CREATE INDEX idx_txn_timestamp ON transactions(timestamp);
CREATE INDEX idx_txn_amount ON transactions(amount);
CREATE INDEX idx_txn_type ON transactions(transaction_type);

-- Partial index for large transactions
CREATE INDEX idx_large_transactions ON transactions(transaction_id) WHERE amount > 10000;

COMMENT ON TABLE transactions IS 'Financial transactions - VISIBLE DATA ONLY';

-- ============================================================================
-- 8. TRANSACTION GROUND TRUTH (Labels)
-- ============================================================================

CREATE TABLE transaction_ground_truth (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) UNIQUE REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    is_suspicious BOOLEAN DEFAULT TRUE,
    suspicion_reason TEXT,
    typology VARCHAR(50),
    step_number INTEGER,
    evasion_techniques JSONB,
    metadata JSONB
);

CREATE INDEX idx_txn_gt_transaction ON transaction_ground_truth(transaction_id);
CREATE INDEX idx_txn_gt_suspicious ON transaction_ground_truth(is_suspicious);
CREATE INDEX idx_txn_gt_typology ON transaction_ground_truth(typology);

COMMENT ON TABLE transaction_ground_truth IS 'Transaction ground truth labels';

-- ============================================================================
-- 9. RELATIONSHIPS (Entity Network)
-- ============================================================================

CREATE TABLE relationships (
    id SERIAL PRIMARY KEY,
    scenario_id VARCHAR(100) REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    from_entity_id VARCHAR(100) REFERENCES entities(entity_id) ON DELETE CASCADE,
    to_entity_id VARCHAR(100) REFERENCES entities(entity_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    strength DECIMAL(3, 2) DEFAULT 1.0,
    metadata JSONB
);

CREATE INDEX idx_rel_scenario ON relationships(scenario_id);
CREATE INDEX idx_rel_from_entity ON relationships(from_entity_id);
CREATE INDEX idx_rel_to_entity ON relationships(to_entity_id);
CREATE INDEX idx_rel_type ON relationships(relationship_type);

COMMENT ON TABLE relationships IS 'Entity relationships for network analysis';

-- ============================================================================
-- 10. ENTITY REUSE LOG (Memory System)
-- ============================================================================

CREATE TABLE entity_reuse_log (
    id SERIAL PRIMARY KEY,
    entity_id VARCHAR(100) REFERENCES entities(entity_id),
    scenario_id VARCHAR(100) REFERENCES scenarios(scenario_id),
    reuse_count INTEGER DEFAULT 1,
    role_in_scenario VARCHAR(100),
    reused_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reuse_entity ON entity_reuse_log(entity_id);
CREATE INDEX idx_reuse_scenario ON entity_reuse_log(scenario_id);
CREATE INDEX idx_reuse_timestamp ON entity_reuse_log(reused_at);

COMMENT ON TABLE entity_reuse_log IS 'Tracks entity reuse across scenarios for memory system';

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_scenarios_updated_at
    BEFORE UPDATE ON scenarios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Complete scenario with visible data only (for AML system)
CREATE OR REPLACE VIEW scenario_visible_data AS
SELECT
    s.scenario_id,
    s.typology,
    s.total_amount,
    s.complexity,
    s.created_at,
    json_agg(DISTINCT jsonb_build_object(
        'entity_id', e.entity_id,
        'entity_type', e.entity_type,
        'name', e.name,
        'country', e.country
    )) FILTER (WHERE e.entity_id IS NOT NULL) as entities,
    json_agg(DISTINCT jsonb_build_object(
        'account_id', a.account_id,
        'entity_id', a.entity_id,
        'bank', a.bank,
        'country', a.country
    )) FILTER (WHERE a.account_id IS NOT NULL) as accounts,
    json_agg(DISTINCT jsonb_build_object(
        'transaction_id', t.transaction_id,
        'from_account_id', t.from_account_id,
        'to_account_id', t.to_account_id,
        'amount', t.amount,
        'timestamp', t.timestamp
    )) FILTER (WHERE t.transaction_id IS NOT NULL) as transactions
FROM scenarios s
LEFT JOIN entities e ON s.scenario_id = e.scenario_id
LEFT JOIN accounts a ON s.scenario_id = a.scenario_id
LEFT JOIN transactions t ON s.scenario_id = t.scenario_id
GROUP BY s.scenario_id;

-- View: Entity reuse statistics
CREATE OR REPLACE VIEW entity_reuse_stats AS
SELECT
    e.entity_id,
    e.name,
    e.entity_type,
    egt.is_shell,
    egt.role_in_scenario,
    COUNT(DISTINCT erl.scenario_id) as scenarios_used_count,
    array_agg(DISTINCT erl.scenario_id) as scenario_ids
FROM entities e
LEFT JOIN entity_ground_truth egt ON e.entity_id = egt.entity_id
LEFT JOIN entity_reuse_log erl ON e.entity_id = erl.entity_id
GROUP BY e.entity_id, e.name, e.entity_type, egt.is_shell, egt.role_in_scenario;

-- ============================================================================
-- GRANT PERMISSIONS (Example - adjust for your roles)
-- ============================================================================

-- Create application user role
-- CREATE ROLE aml_app_user WITH LOGIN PASSWORD 'your_secure_password';

-- Grant visible data access only (for AML system)
-- GRANT SELECT ON entities, accounts, transactions, relationships TO aml_app_user;
-- GRANT INSERT, UPDATE, DELETE ON entities, accounts, transactions, relationships TO aml_app_user;

-- Grant sequence access for inserts
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO aml_app_user;

-- Admin role with full access (for testing/evaluation)
-- CREATE ROLE aml_admin WITH LOGIN PASSWORD 'your_admin_password';
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aml_admin;

-- ============================================================================
-- SAMPLE QUERIES
-- ============================================================================

/*
-- Get complete scenario (visible data)
SELECT * FROM scenario_visible_data WHERE scenario_id = 'SCN_123';

-- Find reusable shell companies
SELECT * FROM entity_reuse_stats
WHERE is_shell = TRUE AND scenarios_used_count <= 5
ORDER BY scenarios_used_count ASC
LIMIT 10;

-- Detect structuring pattern
SELECT
    a.account_id,
    e.name as account_holder,
    COUNT(*) as transaction_count,
    SUM(t.amount) as total_amount,
    AVG(t.amount) as avg_amount
FROM transactions t
JOIN accounts a ON t.from_account_id = a.account_id
JOIN entities e ON a.entity_id = e.entity_id
WHERE t.amount BETWEEN 7000 AND 9999
    AND t.timestamp >= NOW() - INTERVAL '30 days'
GROUP BY a.account_id, e.name
HAVING COUNT(*) >= 3;
*/
