# Antipode

**Adversarial agent system for generating end-to-end synthetic banking data to test AML AI agent swarms.**

Antipode uses LLM-powered micro-agents built on MDAP (Massively Decomposed Agentic Processes) principles to generate realistic money laundering scenarios alongside benign banking activity. The generated data mirrors what a typical bank would have -- customers, companies, accounts, transactions, news events, compliance signals, alerts, and investigation cases -- with ground truth labels for testing AML detection systems.

## Architecture

Antipode has two layers:

### 1. Adversarial Agent System (`adversarial/`)

LLM-powered agents that generate sophisticated AML scenarios:

- **7 AML Typology Agents**: Structuring, Layering, Integration, Mule Network, Shell Company, Trade-Based, Crypto Mixing
- **Orchestration Agents**: Scenario Planner, Evasion Specialist, Validator
- **Benign Pattern Agents**: Generate realistic normal banking activity and false-positive patterns
- **Memory System**: Shared memory, entity registry, relationship graph, transaction ledger
- **Sophistication Framework**: Configurable detection difficulty levels

Each agent follows MDAP principles:
- Minimal focused scope (one task per agent)
- First-to-ahead-by-k voting for error correction
- Red-flag detection for unreliable LLM responses
- Async execution with agent pools for concurrency

### 2. Data Generation Layer (`data/`)

Deterministic synthetic data generation for baseline banking data:

- **Entities**: Customers and companies with full KYC profiles across 14+ locales
- **Accounts**: Bank accounts with product types, channels, declared purposes
- **Transactions**: Baseline normal activity with configurable volume
- **News & Adverse Media**: Corporate events, regulatory actions, media coverage
- **Signals**: Derived behavioral, network, and entity-level risk signals
- **Alerts**: Rule-based alerts from the signal layer
- **Typologies**: 11 money laundering patterns with ground truth labels

## Supported AML Typologies

| Typology | Agent | Description |
|---|---|---|
| Structuring | `StructuringAgent` | Amounts just below reporting thresholds |
| Layering | `LayeringAgent` | Complex layers to obscure money trail |
| Integration | `IntegrationAgent` | Reintroduce laundered money into legitimate economy |
| Mule Network | `MuleNetworkAgent` | Money mules moving funds through accounts |
| Shell Company | `ShellCompanyAgent` | Shell companies to disguise ownership |
| Trade-Based | `TradeBasedAgent` | Over/under invoicing, phantom shipments |
| Crypto Mixing | `CryptoMixingAgent` | Cryptocurrency mixing to obscure origins |

## Quick Start

```bash
pip install -e ".[dev]"
```

### Generate adversarial scenarios (LLM-powered)

```python
from antipode.adversarial import AdversarialOrchestrator, OrchestratorConfig

config = OrchestratorConfig()
orchestrator = AdversarialOrchestrator(config)

# Generate a money laundering scenario
scenario = await orchestrator.generate_scenario(typology="structuring")
```

### Generate baseline banking data (deterministic)

```python
from antipode.data.generators import AMLDataGenerator

generator = AMLDataGenerator(seed=42)
dataset = generator.generate_full_dataset(
    num_customers=500,
    num_companies=100,
    typology_rate=0.05,
    adverse_media_rate=0.05,
)
```

### Generate mixed dataset (benign + adversarial)

```python
from antipode.adversarial import MixedScenarioOrchestrator

orchestrator = MixedScenarioOrchestrator()
dataset = await orchestrator.generate_mixed_dataset(
    num_benign=100,
    num_suspicious=10,
)
```

## Project Structure

```
src/antipode/
    adversarial/
        agents/
            aml/            # 7 AML typology agents
            base/           # BaseAgent, VotingAgent, AgentPool
            benign/         # Benign pattern generators
            orchestration/  # Scenario planner, evasion, validator
            fraud/          # (placeholder for future)
            insider_trading/
            market_manipulation/
        config/             # Agent and typology configuration
        memory/             # Shared memory system
        orchestrator/       # Workflow orchestration and runner
        sophistication/     # Detection difficulty levels
    data/
        models/             # Data classes (Entity, Transaction, Account, Alert)
        config/             # Region and customer segment configurations
        generators/         # Deterministic synthetic data generation
        signals/            # Signal definitions and computation
        alerts/             # Alert rules and rules engine
        typologies/         # Typology definitions and injection
    graph/                  # Neo4j graph database integration
    tracking/               # MLflow experiment tracking
```

## Configuration

### LLM Providers

Set one of these environment variables:

```bash
GROQ_API_KEY=your_groq_key      # Primary (Groq with Qwen3-32B)
OPENAI_API_KEY=your_openai_key  # Fallback (OpenAI GPT-4o)
```

### MLflow Tracking (optional)

```bash
DATABRICKS_HOST=your_host
DATABRICKS_TOKEN=your_token
MLFLOW_EXPERIMENT_NAME=/your/experiment
```

### Data Generation

- **8 customer segments**: retail, HNW, SMB, corporate, correspondent, PEP, NGO, MSB
- **3 geographic regions**: Americas, EMEA, APAC with country-level risk scoring
- **14+ locales**: Realistic names and addresses per region
- **Reproducible**: Seeded random generation for consistent test datasets

## Requirements

- Python 3.10+
- numpy, pandas, faker, pydantic
- openai (for LLM agent calls via Groq or OpenAI)
- mlflow (for experiment tracking)
- Neo4j (optional, for graph database features)
