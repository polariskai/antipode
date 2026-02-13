# AML Test Data Generation Agent System
## Comprehensive Design Document

---

## 1. Executive Summary

This document outlines a multi-agent system architecture designed to generate comprehensive, realistic test data for Anti-Money Laundering (AML) scenarios. The synthetic data produced will be used to train and evaluate AML alert analysis agents, enabling robust testing without exposing sensitive customer information.

**Key Objectives:**
- Generate realistic financial transaction data simulating both legitimate and suspicious activity patterns
- Create diverse AML scenarios covering all major typologies (structuring, layering, integration, etc.)
- Produce labeled datasets suitable for supervised machine learning training
- Enable comprehensive evaluation of alert analysis systems across edge cases and corner scenarios

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR AGENT                                   │
│                    (Workflow Control & Coordination)                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   ENTITY         │    │   SCENARIO       │    │   TRANSACTION    │
│   GENERATOR      │    │   PLANNER        │    │   GENERATOR      │
│   AGENT          │    │   AGENT          │    │   AGENT          │
└──────────────────┘    └──────────────────┘    └──────────────────┘
           │                        │                        │
           ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   RELATIONSHIP   │    │   BEHAVIORAL     │    │   ALERT          │
│   MODELER        │    │   PATTERN        │    │   LABELER        │
│   AGENT          │    │   AGENT          │    │   AGENT          │
└──────────────────┘    └──────────────────┘    └──────────────────┘
           │                        │                        │
           └────────────────────────┼────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         QUALITY ASSURANCE AGENT                              │
│              (Validation, Consistency Checking, Statistical Analysis)        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OUTPUT MANAGER AGENT                                 │
│                  (Data Formatting, Export, Documentation)                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent Specifications

### 3.1 Orchestrator Agent

**Purpose:** Central coordination and workflow management

**Responsibilities:**
- Receives generation requests with parameters (volume, scenario mix, time range)
- Decomposes requests into subtasks for specialized agents
- Manages execution order and dependencies between agents
- Handles error recovery and retry logic
- Tracks generation progress and provides status updates
- Ensures global constraints are satisfied (e.g., no duplicate IDs)

**Input Parameters:**
```json
{
  "generation_request": {
    "total_customers": 10000,
    "total_accounts": 25000,
    "total_transactions": 5000000,
    "time_range": {
      "start": "2022-01-01",
      "end": "2024-12-31"
    },
    "scenario_distribution": {
      "legitimate": 0.85,
      "structuring": 0.03,
      "layering": 0.03,
      "shell_company": 0.02,
      "trade_based": 0.02,
      "funnel_account": 0.02,
      "rapid_movement": 0.015,
      "round_tripping": 0.015
    },
    "geographic_distribution": {
      "domestic": 0.70,
      "international_low_risk": 0.20,
      "international_high_risk": 0.10
    },
    "customer_segments": {
      "retail": 0.60,
      "small_business": 0.25,
      "corporate": 0.10,
      "high_net_worth": 0.05
    }
  }
}
```

**Output:** Coordinated execution plan and final dataset assembly

---

### 3.2 Entity Generator Agent

**Purpose:** Create realistic customer and business entity profiles

**Responsibilities:**
- Generate individual customer profiles (demographics, employment, income)
- Create business entity profiles (industry, size, registration details)
- Assign risk ratings based on configurable criteria
- Generate identification documents and registration numbers
- Create beneficial ownership structures for businesses

**Entity Schema - Individual:**
```json
{
  "entity_id": "ENT-IND-00001",
  "entity_type": "individual",
  "profile": {
    "first_name": "string",
    "last_name": "string",
    "date_of_birth": "date",
    "nationality": "ISO-3166-1",
    "residence_country": "ISO-3166-1",
    "occupation": "string",
    "employer": "string",
    "annual_income": "decimal",
    "source_of_wealth": "string",
    "pep_status": "boolean",
    "pep_details": "object|null"
  },
  "identification": [
    {
      "type": "passport|drivers_license|national_id",
      "number": "string",
      "issuing_country": "ISO-3166-1",
      "expiry_date": "date"
    }
  ],
  "contact": {
    "address": "object",
    "phone": "string",
    "email": "string"
  },
  "risk_assessment": {
    "inherent_risk_score": "integer (1-100)",
    "risk_factors": ["string"],
    "last_review_date": "date"
  },
  "kyc_status": "verified|pending|enhanced_due_diligence",
  "onboarding_date": "date",
  "metadata": {
    "is_synthetic": true,
    "generation_timestamp": "datetime",
    "scenario_tags": ["string"]
  }
}
```

**Entity Schema - Business:**
```json
{
  "entity_id": "ENT-BUS-00001",
  "entity_type": "business",
  "profile": {
    "legal_name": "string",
    "trade_name": "string|null",
    "entity_subtype": "corporation|llc|partnership|sole_proprietor",
    "registration_number": "string",
    "registration_country": "ISO-3166-1",
    "registration_date": "date",
    "industry_code": "NAICS|SIC",
    "industry_description": "string",
    "annual_revenue": "decimal",
    "employee_count": "integer",
    "business_description": "string"
  },
  "beneficial_owners": [
    {
      "entity_id": "string",
      "ownership_percentage": "decimal",
      "control_type": "ownership|voting|other"
    }
  ],
  "authorized_signatories": ["entity_id"],
  "registered_address": "object",
  "operating_addresses": ["object"],
  "risk_assessment": {
    "inherent_risk_score": "integer (1-100)",
    "risk_factors": ["string"],
    "industry_risk": "low|medium|high",
    "geographic_risk": "low|medium|high"
  },
  "shell_company_indicators": {
    "is_shell": "boolean",
    "indicators": ["string"]
  },
  "metadata": {
    "is_synthetic": true,
    "generation_timestamp": "datetime",
    "scenario_tags": ["string"]
  }
}
```

---

### 3.3 Scenario Planner Agent

**Purpose:** Design and orchestrate specific AML scenarios

**Responsibilities:**
- Select and configure AML typologies based on distribution requirements
- Design multi-party schemes with appropriate complexity
- Define temporal patterns and trigger conditions
- Create scenario narratives for documentation
- Coordinate with other agents to ensure scenario coherence

**Supported AML Typologies:**

| Category | Typology | Description |
|----------|----------|-------------|
| **Structuring** | Smurfing | Multiple small deposits below reporting threshold |
| | Threshold Avoidance | Transactions consistently just below $10K |
| | Multiple Location Deposits | Same-day deposits across branches |
| **Layering** | Rapid Movement | Quick transfer through multiple accounts |
| | Round-Tripping | Funds return to origin through complex path |
| | Shell Company Networks | Transfers between related shell entities |
| **Integration** | Real Estate | Property purchases with suspicious funds |
| | Trade-Based | Over/under invoicing in trade transactions |
| | Investment Layering | Securities purchases to legitimize funds |
| **Other** | Funnel Accounts | Many-to-one or one-to-many patterns |
| | Third-Party Transfers | Unexpected third-party involvement |
| | Geographic Anomalies | Transactions with high-risk jurisdictions |

**Scenario Definition Schema:**
```json
{
  "scenario_id": "SCN-STRUCT-001",
  "typology": "structuring_smurfing",
  "complexity": "simple|moderate|complex",
  "participants": {
    "primary_actor": "entity_id",
    "co-conspirators": ["entity_id"],
    "unwitting_participants": ["entity_id"],
    "shell_companies": ["entity_id"]
  },
  "narrative": "string - human readable description",
  "phases": [
    {
      "phase_name": "placement",
      "duration_days": 30,
      "transaction_patterns": ["pattern_id"],
      "expected_alerts": ["alert_type"]
    }
  ],
  "total_illicit_amount": "decimal",
  "detection_difficulty": "easy|medium|hard",
  "red_flags": ["string"],
  "ground_truth_labels": {
    "is_suspicious": true,
    "sar_required": true,
    "typology_tags": ["string"]
  }
}
```

---

### 3.4 Relationship Modeler Agent

**Purpose:** Create realistic networks of relationships between entities

**Responsibilities:**
- Model family and household relationships
- Create business ownership and control structures
- Generate professional/employment relationships
- Model banking relationships (joint accounts, authorized users)
- Create suspicious relationship networks for ML scenarios
- Ensure relationship consistency across the dataset

**Relationship Types:**
```json
{
  "relationship_types": {
    "familial": ["spouse", "parent", "child", "sibling", "extended_family"],
    "business": ["owner", "director", "officer", "employee", "partner", "shareholder"],
    "financial": ["co-account_holder", "authorized_signer", "beneficiary", "guarantor"],
    "professional": ["attorney", "accountant", "financial_advisor", "trustee"],
    "suspicious": ["nominee", "front_person", "money_mule", "straw_buyer"]
  }
}
```

**Relationship Schema:**
```json
{
  "relationship_id": "REL-00001",
  "entity_1": "entity_id",
  "entity_2": "entity_id",
  "relationship_type": "string",
  "relationship_subtype": "string|null",
  "direction": "unidirectional|bidirectional",
  "start_date": "date",
  "end_date": "date|null",
  "attributes": {
    "ownership_percentage": "decimal|null",
    "role_description": "string|null"
  },
  "is_declared": "boolean",
  "discovery_source": "kyc|transaction_analysis|external",
  "suspicion_indicators": ["string"],
  "metadata": {
    "scenario_id": "string|null"
  }
}
```

---

### 3.5 Transaction Generator Agent

**Purpose:** Generate realistic financial transaction data

**Responsibilities:**
- Generate transaction streams matching behavioral profiles
- Apply scenario-specific patterns (structuring, layering, etc.)
- Ensure temporal consistency and realistic timing
- Generate appropriate transaction metadata
- Model payment channels and instrument types

**Transaction Schema:**
```json
{
  "transaction_id": "TXN-00000001",
  "timestamp": "datetime",
  "transaction_type": "string",
  "transaction_subtype": "string",
  "channel": "branch|atm|online|mobile|wire|ach",
  "originator": {
    "entity_id": "string",
    "account_id": "string",
    "account_type": "checking|savings|money_market|brokerage"
  },
  "beneficiary": {
    "entity_id": "string|null",
    "account_id": "string|null",
    "name": "string",
    "institution": "string|null",
    "country": "ISO-3166-1"
  },
  "amount": {
    "value": "decimal",
    "currency": "ISO-4217"
  },
  "converted_amount": {
    "value": "decimal",
    "currency": "USD",
    "exchange_rate": "decimal"
  },
  "description": "string",
  "reference_number": "string",
  "related_transactions": ["transaction_id"],
  "location": {
    "branch_id": "string|null",
    "city": "string",
    "state": "string|null",
    "country": "ISO-3166-1",
    "ip_address": "string|null"
  },
  "flags": {
    "is_cash": "boolean",
    "is_international": "boolean",
    "high_risk_country": "boolean",
    "round_amount": "boolean",
    "just_below_threshold": "boolean"
  },
  "ground_truth": {
    "is_suspicious": "boolean",
    "scenario_id": "string|null",
    "typology": "string|null",
    "phase": "placement|layering|integration|null"
  }
}
```

**Transaction Types Supported:**

| Category | Types |
|----------|-------|
| **Deposits** | Cash deposit, Check deposit, Wire incoming, ACH credit, Mobile deposit |
| **Withdrawals** | Cash withdrawal, ATM withdrawal, Wire outgoing, ACH debit |
| **Transfers** | Internal transfer, External transfer, Book transfer |
| **Payments** | Bill pay, P2P payment, Merchant payment |
| **Trade Finance** | Letter of credit, Documentary collection, Trade payment |
| **Securities** | Buy, Sell, Dividend, Interest |

---

### 3.6 Behavioral Pattern Agent

**Purpose:** Generate realistic behavioral profiles and patterns

**Responsibilities:**
- Define baseline behavioral profiles per customer segment
- Model seasonal and cyclical patterns
- Generate anomaly patterns for suspicious scenarios
- Create peer group comparisons
- Model behavioral drift over time

**Behavioral Profile Schema:**
```json
{
  "profile_id": "BEH-00001",
  "entity_id": "string",
  "baseline_period": {
    "start": "date",
    "end": "date"
  },
  "transaction_patterns": {
    "avg_monthly_transactions": "integer",
    "std_dev_transactions": "decimal",
    "avg_transaction_amount": "decimal",
    "std_dev_amount": "decimal",
    "typical_transaction_types": [
      {"type": "string", "frequency": "decimal"}
    ],
    "typical_channels": [
      {"channel": "string", "frequency": "decimal"}
    ],
    "typical_days": ["monday", "tuesday", ...],
    "typical_hours": {"start": 9, "end": 17}
  },
  "cash_patterns": {
    "cash_ratio": "decimal",
    "avg_cash_amount": "decimal",
    "cash_frequency": "decimal"
  },
  "geographic_patterns": {
    "primary_locations": ["string"],
    "international_frequency": "decimal",
    "high_risk_country_frequency": "decimal"
  },
  "counterparty_patterns": {
    "unique_counterparties_monthly": "integer",
    "repeat_counterparty_ratio": "decimal",
    "new_counterparty_rate": "decimal"
  },
  "velocity_limits": {
    "max_daily_transactions": "integer",
    "max_daily_amount": "decimal",
    "max_weekly_amount": "decimal"
  },
  "peer_group": "string",
  "expected_variance": "decimal"
}
```

---

### 3.7 Alert Labeler Agent

**Purpose:** Generate ground truth labels and expected alert outcomes

**Responsibilities:**
- Apply rule-based detection logic to flag expected alerts
- Calculate alert scores and priorities
- Generate SAR decision labels
- Create investigation narratives
- Document reasoning for training data

**Alert Schema:**
```json
{
  "alert_id": "ALT-00000001",
  "alert_type": "string",
  "alert_subtype": "string",
  "detection_rule": "string",
  "trigger_timestamp": "datetime",
  "subject_entity": "entity_id",
  "subject_accounts": ["account_id"],
  "triggering_transactions": ["transaction_id"],
  "lookback_period": {
    "start": "datetime",
    "end": "datetime"
  },
  "alert_details": {
    "rule_threshold": "decimal",
    "actual_value": "decimal",
    "peer_group_average": "decimal",
    "standard_deviations": "decimal"
  },
  "aggregated_metrics": {
    "total_amount": "decimal",
    "transaction_count": "integer",
    "unique_counterparties": "integer",
    "cash_percentage": "decimal"
  },
  "risk_indicators": [
    {
      "indicator": "string",
      "severity": "low|medium|high",
      "description": "string"
    }
  ],
  "related_alerts": ["alert_id"],
  "ground_truth": {
    "is_true_positive": "boolean",
    "disposition": "sar_filed|closed_no_action|escalated|closed_with_action",
    "actual_typology": "string|null",
    "scenario_id": "string|null",
    "investigation_notes": "string",
    "decision_rationale": "string"
  },
  "difficulty_factors": {
    "detection_difficulty": "easy|medium|hard",
    "obfuscation_techniques": ["string"],
    "legitimate_explanation_plausibility": "low|medium|high"
  }
}
```

**Alert Types:**

| Category | Alert Types |
|----------|-------------|
| **Threshold-Based** | CTR Filing, Large Cash Transaction, High Value Wire |
| **Structuring** | Potential Structuring, Threshold Avoidance Pattern |
| **Velocity** | Unusual Activity Spike, Rapid Fund Movement |
| **Behavioral** | Out-of-Pattern Activity, New Behavior Detection |
| **Network** | Related Party Transaction, Shell Company Pattern |
| **Geographic** | High-Risk Country Transaction, Unusual Geographic Pattern |
| **Profile** | Profile Mismatch, Source of Funds Concern |

---

### 3.8 Quality Assurance Agent

**Purpose:** Validate data quality and statistical properties

**Responsibilities:**
- Validate referential integrity across all entities
- Check statistical distributions match requirements
- Verify temporal consistency
- Detect and resolve logical inconsistencies
- Generate quality metrics and reports

**Validation Checks:**

```json
{
  "validation_suite": {
    "referential_integrity": [
      "all_transaction_entities_exist",
      "all_relationship_entities_exist",
      "all_account_owners_exist",
      "all_beneficial_owners_exist"
    ],
    "temporal_consistency": [
      "transactions_within_account_lifecycle",
      "relationships_temporally_valid",
      "entity_ages_valid",
      "onboarding_before_first_transaction"
    ],
    "statistical_validation": [
      "scenario_distribution_matches_request",
      "geographic_distribution_matches_request",
      "customer_segment_distribution_matches_request",
      "alert_rate_within_expected_range"
    ],
    "logical_consistency": [
      "income_supports_transaction_volume",
      "business_revenue_supports_activity",
      "transaction_amounts_within_limits",
      "no_self_transactions"
    ],
    "data_quality": [
      "no_null_required_fields",
      "valid_iso_codes",
      "valid_date_formats",
      "unique_identifiers"
    ]
  }
}
```

**Quality Metrics Report:**
```json
{
  "quality_report": {
    "generation_id": "string",
    "timestamp": "datetime",
    "summary": {
      "total_entities": "integer",
      "total_transactions": "integer",
      "total_alerts": "integer",
      "validation_pass_rate": "decimal"
    },
    "distribution_accuracy": {
      "scenario_distribution_error": "decimal",
      "geographic_distribution_error": "decimal",
      "segment_distribution_error": "decimal"
    },
    "statistical_properties": {
      "transaction_amount_distribution": {
        "mean": "decimal",
        "median": "decimal",
        "std_dev": "decimal",
        "skewness": "decimal"
      },
      "alert_rate": "decimal",
      "true_positive_rate": "decimal",
      "false_positive_rate": "decimal"
    },
    "issues_found": [
      {
        "category": "string",
        "severity": "warning|error",
        "count": "integer",
        "description": "string",
        "resolution": "string"
      }
    ]
  }
}
```

---

### 3.9 Output Manager Agent

**Purpose:** Format and export generated data

**Responsibilities:**
- Export data in multiple formats (JSON, CSV, Parquet, SQL)
- Generate data dictionaries and documentation
- Create train/test/validation splits
- Package data with metadata
- Generate sample queries and access patterns

**Export Formats:**

| Format | Use Case |
|--------|----------|
| JSON/JSONL | API integration, flexible schema |
| CSV | Spreadsheet analysis, simple imports |
| Parquet | Big data processing, columnar analytics |
| SQL Scripts | Database seeding, relational systems |
| Avro | Streaming systems, schema evolution |

**Output Package Structure:**
```
aml_test_data_v1.0/
├── README.md
├── DATA_DICTIONARY.md
├── SCENARIO_DOCUMENTATION.md
├── metadata/
│   ├── generation_config.json
│   ├── quality_report.json
│   └── statistics_summary.json
├── entities/
│   ├── individuals.parquet
│   ├── businesses.parquet
│   └── relationships.parquet
├── accounts/
│   └── accounts.parquet
├── transactions/
│   ├── transactions_2022.parquet
│   ├── transactions_2023.parquet
│   └── transactions_2024.parquet
├── alerts/
│   ├── alerts.parquet
│   └── alert_transactions.parquet
├── scenarios/
│   └── scenario_definitions.json
├── splits/
│   ├── train_entity_ids.txt
│   ├── validation_entity_ids.txt
│   └── test_entity_ids.txt
└── samples/
    ├── sample_queries.sql
    └── sample_analysis.ipynb
```

---

## 4. Data Generation Workflow

### 4.1 End-to-End Process

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 1: INITIALIZATION                                                      │
│ ─────────────────────────────────────────────────────────────────────────── │
│ 1. Orchestrator receives generation request                                  │
│ 2. Validate parameters and calculate resource requirements                   │
│ 3. Initialize random seeds for reproducibility                               │
│ 4. Create generation session with unique ID                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 2: ENTITY GENERATION                                                   │
│ ─────────────────────────────────────────────────────────────────────────── │
│ 1. Entity Generator creates customer and business profiles                   │
│ 2. Assign segment classifications and risk ratings                           │
│ 3. Relationship Modeler creates entity networks                              │
│ 4. Create accounts for each entity                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 3: SCENARIO PLANNING                                                   │
│ ─────────────────────────────────────────────────────────────────────────── │
│ 1. Scenario Planner selects entities for suspicious scenarios                │
│ 2. Design scenario timelines and phases                                      │
│ 3. Configure transaction patterns for each scenario                          │
│ 4. Create shell company networks where needed                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 4: BEHAVIORAL PROFILING                                                │
│ ─────────────────────────────────────────────────────────────────────────── │
│ 1. Behavioral Pattern Agent creates baseline profiles                        │
│ 2. Define expected transaction patterns per entity                           │
│ 3. Configure anomaly patterns for suspicious entities                        │
│ 4. Set velocity and volume parameters                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 5: TRANSACTION GENERATION                                              │
│ ─────────────────────────────────────────────────────────────────────────── │
│ 1. Generate legitimate transaction streams (85% of volume)                   │
│ 2. Inject scenario-specific suspicious patterns (15% of volume)              │
│ 3. Apply temporal distribution and realistic timing                          │
│ 4. Generate transaction metadata and references                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 6: ALERT GENERATION                                                    │
│ ─────────────────────────────────────────────────────────────────────────── │
│ 1. Alert Labeler applies detection rules to transactions                     │
│ 2. Generate alerts with appropriate metadata                                 │
│ 3. Create ground truth labels (TP/FP classifications)                        │
│ 4. Generate investigation narratives and decision rationale                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 7: QUALITY ASSURANCE                                                   │
│ ─────────────────────────────────────────────────────────────────────────── │
│ 1. QA Agent validates referential integrity                                  │
│ 2. Verify statistical distributions                                          │
│ 3. Check temporal and logical consistency                                    │
│ 4. Generate quality metrics report                                           │
│ 5. Resolve any identified issues                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 8: OUTPUT GENERATION                                                   │
│ ─────────────────────────────────────────────────────────────────────────── │
│ 1. Output Manager formats data in requested formats                          │
│ 2. Create train/validation/test splits                                       │
│ 3. Generate documentation and data dictionaries                              │
│ 4. Package and deliver final dataset                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Detailed Scenario Specifications

### 5.1 Structuring (Smurfing) Scenario

**Description:** Multiple deposits below the $10,000 CTR threshold to avoid reporting requirements.

**Pattern Configuration:**
```json
{
  "scenario_type": "structuring_smurfing",
  "parameters": {
    "deposit_range": {"min": 2000, "max": 9500},
    "deposits_per_day": {"min": 2, "max": 5},
    "total_target_amount": 50000,
    "duration_days": 14,
    "channel_mix": {
      "branch": 0.6,
      "atm": 0.3,
      "mobile": 0.1
    },
    "location_variation": true,
    "time_spacing_hours": {"min": 2, "max": 8}
  },
  "red_flags": [
    "Multiple cash deposits just below $10,000",
    "Deposits at multiple branches same day",
    "Round or near-round amounts",
    "Inconsistent with stated income"
  ],
  "expected_alerts": [
    "STRUCTURING_PATTERN",
    "UNUSUAL_CASH_ACTIVITY",
    "MULTIPLE_BRANCH_ACTIVITY"
  ]
}
```

### 5.2 Layering Scenario

**Description:** Rapid movement of funds through multiple accounts to obscure origin.

**Pattern Configuration:**
```json
{
  "scenario_type": "layering_rapid_movement",
  "parameters": {
    "initial_amount": 500000,
    "number_of_layers": 5,
    "accounts_per_layer": 3,
    "time_between_layers_hours": {"min": 4, "max": 48},
    "split_ratios": [0.4, 0.35, 0.25],
    "recombination_at_layer": 4,
    "jurisdictions_involved": ["US", "UK", "SG", "CH"],
    "intermediary_types": ["shell_company", "trust", "nominee"]
  },
  "red_flags": [
    "Rapid fund movement through multiple accounts",
    "Minimal business rationale for transfers",
    "Complex ownership structures",
    "International wire patterns"
  ],
  "expected_alerts": [
    "RAPID_MOVEMENT",
    "SHELL_COMPANY_ACTIVITY",
    "COMPLEX_FUND_FLOW"
  ]
}
```

### 5.3 Trade-Based Money Laundering

**Description:** Over/under invoicing of goods to move value across borders.

**Pattern Configuration:**
```json
{
  "scenario_type": "trade_based_ml",
  "parameters": {
    "trade_type": "import",
    "commodity": "electronics",
    "fair_market_value": 100000,
    "invoiced_value": 250000,
    "overinvoice_ratio": 2.5,
    "trade_partner_country": "high_risk_jurisdiction",
    "payment_method": "wire_transfer",
    "documentation_quality": "poor",
    "shipment_frequency": "monthly"
  },
  "red_flags": [
    "Invoice values inconsistent with market prices",
    "Trade with high-risk jurisdictions",
    "Inconsistent shipping documentation",
    "Unusual payment terms"
  ],
  "expected_alerts": [
    "TRADE_PRICE_ANOMALY",
    "HIGH_RISK_COUNTRY_TRADE",
    "DOCUMENTATION_DISCREPANCY"
  ]
}
```

### 5.4 Funnel Account Scenario

**Description:** Multiple sources depositing into single account (many-to-one).

**Pattern Configuration:**
```json
{
  "scenario_type": "funnel_account",
  "parameters": {
    "funnel_direction": "many_to_one",
    "source_count": 15,
    "collection_account": "account_id",
    "deposit_frequency": "daily",
    "amount_per_source": {"min": 500, "max": 2000},
    "source_types": ["individuals", "cash"],
    "aggregation_period_days": 7,
    "withdrawal_pattern": "bulk_wire_out",
    "withdrawal_destination": "foreign_account"
  },
  "red_flags": [
    "Multiple unrelated depositors",
    "Rapid aggregation and withdrawal",
    "Cash-intensive deposits",
    "Bulk outgoing transfers"
  ],
  "expected_alerts": [
    "FUNNEL_ACCOUNT_PATTERN",
    "AGGREGATION_ACTIVITY",
    "UNUSUAL_DEPOSIT_SOURCES"
  ]
}
```

### 5.5 Round-Tripping Scenario

**Description:** Funds leave and return to same entity through complex paths.

**Pattern Configuration:**
```json
{
  "scenario_type": "round_tripping",
  "parameters": {
    "principal_amount": 1000000,
    "outbound_path_length": 4,
    "return_path_length": 3,
    "jurisdictions": ["US", "BVI", "CY", "LU"],
    "intermediary_entities": ["shell_1", "shell_2", "trust_1"],
    "disguise_method": "loan_repayment",
    "time_to_complete_days": 45,
    "amount_retained": 0.95
  },
  "red_flags": [
    "Circular fund flow patterns",
    "Offshore intermediaries",
    "Loans without economic substance",
    "Related party transactions"
  ],
  "expected_alerts": [
    "CIRCULAR_TRANSACTION_PATTERN",
    "RELATED_PARTY_TRANSFERS",
    "SUSPICIOUS_LOAN_ACTIVITY"
  ]
}
```

---

## 6. Implementation Considerations

### 6.1 Technology Stack Recommendations

| Component | Recommended Technologies |
|-----------|-------------------------|
| **Agent Framework** | LangChain, AutoGen, CrewAI, or custom orchestration |
| **LLM Backend** | Claude API for reasoning, GPT-4 for alternatives |
| **Data Generation** | Faker (base data), custom generators for financial patterns |
| **Data Storage** | PostgreSQL (relational), MongoDB (documents), DuckDB (analytics) |
| **Data Processing** | Pandas, Polars, Apache Spark for large-scale |
| **Validation** | Great Expectations, Pandera for data quality |
| **Export** | PyArrow (Parquet), SQLAlchemy (SQL) |

### 6.2 Scalability Considerations

**Horizontal Scaling:**
- Partition entity generation by segment
- Parallelize transaction generation by time period
- Distribute scenario execution across workers

**Resource Estimates:**

| Dataset Size | Entities | Transactions | Est. Generation Time | Storage |
|--------------|----------|--------------|---------------------|---------|
| Small | 1,000 | 100,000 | 5-10 minutes | ~500 MB |
| Medium | 10,000 | 1,000,000 | 30-60 minutes | ~5 GB |
| Large | 100,000 | 10,000,000 | 4-8 hours | ~50 GB |
| Enterprise | 1,000,000 | 100,000,000 | 24-48 hours | ~500 GB |

### 6.3 Reproducibility

**Seed Management:**
```python
{
  "generation_seeds": {
    "master_seed": 42,
    "entity_seed": 1001,
    "transaction_seed": 2001,
    "scenario_seed": 3001,
    "noise_seed": 4001
  },
  "version_info": {
    "generator_version": "1.2.0",
    "schema_version": "2.0",
    "generation_timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### 6.4 Privacy and Compliance

**Data Isolation:**
- All generated data is purely synthetic
- No real PII is used or referenced
- Entity names generated using Faker with appropriate locales
- Addresses, phone numbers, and emails are all fictional

**Audit Trail:**
- All generation parameters logged
- Scenario assignments documented
- Quality validation results preserved
- Version control for all configurations

---

## 7. Agent Communication Protocol

### 7.1 Message Format

```json
{
  "message_id": "uuid",
  "timestamp": "datetime",
  "sender": "agent_name",
  "recipient": "agent_name|broadcast",
  "message_type": "request|response|notification|error",
  "correlation_id": "uuid (for request-response pairs)",
  "payload": {
    "task_type": "string",
    "parameters": {},
    "data": {},
    "status": "pending|in_progress|completed|failed"
  },
  "context": {
    "session_id": "string",
    "generation_id": "string",
    "phase": "string"
  }
}
```

### 7.2 Coordination Patterns

**Sequential Dependency:**
```
Orchestrator → Entity Generator → Relationship Modeler → Scenario Planner
```

**Parallel Execution:**
```
Scenario Planner ─┬─→ Transaction Generator (Legitimate)
                  └─→ Transaction Generator (Suspicious)
```

**Feedback Loop:**
```
QA Agent ←──────────────→ All Generators (for corrections)
```

---

## 8. Evaluation Metrics for Generated Data

### 8.1 Data Quality Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Referential Integrity | 100% | All foreign keys resolve |
| Temporal Consistency | 100% | No anachronistic data |
| Distribution Accuracy | ±5% | Match requested distributions |
| Uniqueness | 100% | No duplicate primary keys |
| Completeness | >99% | Minimal null values in required fields |

### 8.2 Realism Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Transaction Amount Distribution | Benford's Law compliance | First-digit distribution matches real data |
| Temporal Patterns | Chi-square test p>0.05 | Day/hour distributions match expected |
| Network Properties | Scale-free characteristics | Relationship networks exhibit realistic topology |
| Behavioral Consistency | >95% | Entity behavior matches assigned profiles |

### 8.3 ML Training Utility Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Class Balance | Per specification | Suspicious vs legitimate ratio |
| Scenario Coverage | 100% | All requested typologies represented |
| Difficulty Distribution | Even spread | Easy/medium/hard cases balanced |
| Feature Completeness | >95% | All features populated for ML consumption |

---

## 9. Sample Output Examples

### 9.1 Sample Entity (Individual)

```json
{
  "entity_id": "ENT-IND-00042",
  "entity_type": "individual",
  "profile": {
    "first_name": "Michael",
    "last_name": "Chen",
    "date_of_birth": "1978-03-15",
    "nationality": "US",
    "residence_country": "US",
    "occupation": "Software Engineer",
    "employer": "TechCorp Industries",
    "annual_income": 145000,
    "source_of_wealth": "employment",
    "pep_status": false
  },
  "risk_assessment": {
    "inherent_risk_score": 22,
    "risk_factors": [],
    "last_review_date": "2023-01-15"
  },
  "kyc_status": "verified",
  "onboarding_date": "2019-06-20",
  "metadata": {
    "is_synthetic": true,
    "scenario_tags": ["legitimate"]
  }
}
```

### 9.2 Sample Transaction (Suspicious)

```json
{
  "transaction_id": "TXN-00523847",
  "timestamp": "2024-03-15T14:23:17Z",
  "transaction_type": "deposit",
  "transaction_subtype": "cash_deposit",
  "channel": "branch",
  "originator": {
    "entity_id": "ENT-IND-00089",
    "account_id": "ACC-00089-CHK",
    "account_type": "checking"
  },
  "amount": {
    "value": 9400.00,
    "currency": "USD"
  },
  "description": "Cash deposit",
  "location": {
    "branch_id": "BR-NYC-042",
    "city": "New York",
    "state": "NY",
    "country": "US"
  },
  "flags": {
    "is_cash": true,
    "round_amount": false,
    "just_below_threshold": true
  },
  "ground_truth": {
    "is_suspicious": true,
    "scenario_id": "SCN-STRUCT-003",
    "typology": "structuring",
    "phase": "placement"
  }
}
```

### 9.3 Sample Alert

```json
{
  "alert_id": "ALT-00001523",
  "alert_type": "STRUCTURING_PATTERN",
  "detection_rule": "CASH_BELOW_CTR_MULTIPLE",
  "trigger_timestamp": "2024-03-15T18:00:00Z",
  "subject_entity": "ENT-IND-00089",
  "triggering_transactions": [
    "TXN-00523845",
    "TXN-00523847",
    "TXN-00523851",
    "TXN-00523856"
  ],
  "alert_details": {
    "rule_threshold": 3,
    "actual_value": 4,
    "total_amount": 36800,
    "time_window_hours": 72
  },
  "risk_indicators": [
    {
      "indicator": "Multiple cash deposits below $10K",
      "severity": "high"
    },
    {
      "indicator": "Deposits at different branches",
      "severity": "medium"
    }
  ],
  "ground_truth": {
    "is_true_positive": true,
    "disposition": "sar_filed",
    "actual_typology": "structuring",
    "scenario_id": "SCN-STRUCT-003",
    "investigation_notes": "Customer made 4 cash deposits totaling $36,800 over 3 days across multiple branches. Each deposit just below CTR threshold. Activity inconsistent with stated occupation and income.",
    "decision_rationale": "Clear structuring pattern with no legitimate business explanation. Customer profile does not support cash-intensive activity. Recommend SAR filing."
  }
}
```

---

## 10. Appendix: Alert Type Catalog

| Alert Code | Category | Description | Typical FP Rate |
|------------|----------|-------------|-----------------|
| CTR_FILING | Threshold | Cash transaction ≥$10,000 | 0% (regulatory) |
| STRUCTURING_PATTERN | Structuring | Multiple deposits below threshold | 40-60% |
| THRESHOLD_AVOIDANCE | Structuring | Transactions consistently $9,000-$9,999 | 30-50% |
| RAPID_MOVEMENT | Velocity | Funds moved through account in <24 hours | 50-70% |
| UNUSUAL_WIRE_PATTERN | Geographic | Wire to/from high-risk country | 60-80% |
| SHELL_COMPANY_ACTIVITY | Network | Transactions with identified shell entities | 20-40% |
| FUNNEL_ACCOUNT | Pattern | Many-to-one or one-to-many pattern | 40-60% |
| PROFILE_MISMATCH | Behavioral | Activity inconsistent with customer profile | 50-70% |
| DORMANT_REACTIVATION | Behavioral | Sudden activity after long dormancy | 60-80% |
| ROUND_DOLLAR_PATTERN | Pattern | Unusual frequency of round amounts | 70-85% |
| RELATED_PARTY_UNUSUAL | Network | Suspicious related party transactions | 40-60% |
| TRADE_ANOMALY | Trade | Trade values outside market norms | 30-50% |

---

*Document Version: 1.0*
*Generated for AML Test Data Agent System Design*
