# PostgreSQL Quick Start Guide

## Prerequisites

1. **AWS RDS PostgreSQL Instance**
   - PostgreSQL 14+ recommended
   - Public accessibility enabled (for development) or VPC peering configured
   - Security group allowing inbound traffic on port 5432

2. **Python Dependencies**
   ```bash
   pip install sqlalchemy psycopg2-binary pyyaml loguru
   ```

## Step 1: Create RDS Instance (AWS Console)

```bash
# Using AWS CLI (alternative)
aws rds create-db-instance \
    --db-instance-identifier aml-adversarial-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 14.7 \
    --master-username admin \
    --master-user-password YourSecurePassword123! \
    --allocated-storage 20 \
    --storage-type gp3 \
    --vpc-security-group-ids sg-xxxxx \
    --publicly-accessible \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "Mon:04:00-Mon:05:00"
```

**Get endpoint after creation:**
```bash
aws rds describe-db-instances \
    --db-instance-identifier aml-adversarial-db \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text
```

## Step 2: Set Environment Variables

```bash
# Linux/Mac
export POSTGRES_HOST="aml-adversarial-db.xxxxx.us-east-1.rds.amazonaws.com"
export POSTGRES_PASSWORD="YourSecurePassword123!"

# Windows (PowerShell)
$env:POSTGRES_HOST="aml-adversarial-db.xxxxx.us-east-1.rds.amazonaws.com"
$env:POSTGRES_PASSWORD="YourSecurePassword123!"

# Windows (CMD)
set POSTGRES_HOST=aml-adversarial-db.xxxxx.us-east-1.rds.amazonaws.com
set POSTGRES_PASSWORD=YourSecurePassword123!
```

## Step 3: Initialize Database Schema

```bash
# Connect to PostgreSQL using psql
psql -h aml-adversarial-db.xxxxx.us-east-1.rds.amazonaws.com \
     -U admin \
     -d postgres

# Create database
CREATE DATABASE aml_adversarial;

# Connect to new database
\c aml_adversarial

# Run schema script
\i sql/schema.sql

# Verify tables created
\dt

# Exit
\q
```

**Alternative: Using Python**
```python
from sqlalchemy import create_engine, text

# Connect to default 'postgres' database
engine = create_engine(
    "postgresql://admin:YourPassword@your-host.rds.amazonaws.com:5432/postgres"
)

# Create database
with engine.connect() as conn:
    conn.execute(text("CREATE DATABASE aml_adversarial"))
    conn.commit()

# Connect to new database and run schema
engine = create_engine(
    "postgresql://admin:YourPassword@your-host.rds.amazonaws.com:5432/aml_adversarial"
)

with open('sql/schema.sql', 'r') as f:
    schema_sql = f.read()

with engine.connect() as conn:
    conn.execute(text(schema_sql))
    conn.commit()
```

## Step 4: Update Configuration

Edit `config/postgres.yaml`:

```yaml
postgres:
  host: "${POSTGRES_HOST}"  # Uses environment variable
  port: 5432
  database: "aml_adversarial"
  user: "admin"  # Or create dedicated user
  password: "${POSTGRES_PASSWORD}"  # Uses environment variable

  # Connection pool
  pool_size: 10
  max_overflow: 20

  # SSL (required for AWS RDS)
  ssl_mode: "require"
```

## Step 5: Test Connection

```python
from src.antipode.data.loaders import PostgreSQLLoader

# Initialize loader
loader = PostgreSQLLoader(environment="development")

# Test connection
stats = loader.get_statistics()
print(f"Database stats: {stats}")
# Output: {'total_scenarios': 0, 'total_entities': 0, ...}

loader.close()
```

## Step 6: Save Your First Scenario

```python
import asyncio
from src.antipode.adversarial.orchestrator import AdversarialOrchestrator
from src.antipode.data.loaders import PostgreSQLLoader

async def main():
    # Generate scenario
    orchestrator = AdversarialOrchestrator()
    scenario = await orchestrator.generate_scenario(
        typology="structuring",
        total_amount=50000,
        complexity=5
    )

    # Save to PostgreSQL
    loader = PostgreSQLLoader(environment="development")

    # Convert GeneratedScenario to dict
    scenario_dict = {
        'scenario_id': scenario.scenario_id,
        'typology': scenario.typology,
        'entities': scenario.entities,
        'accounts': scenario.accounts,
        'transactions': scenario.transactions,
        'relationships': scenario.relationships,
        'ground_truth': scenario.ground_truth,
        'metadata': {
            'apply_evasion': True,
            'scenario_description': None
        }
    }

    scenario_id = loader.save_scenario(scenario_dict, include_ground_truth=True)
    print(f"Saved scenario: {scenario_id}")

    # Retrieve it back
    retrieved = loader.get_scenario(scenario_id, include_ground_truth=False)
    print(f"Retrieved {len(retrieved['transactions'])} transactions")

    loader.close()

asyncio.run(main())
```

## Step 7: Query Scenarios

### Get visible data only (for AML system)
```python
from src.antipode.data.loaders import PostgreSQLLoader

loader = PostgreSQLLoader()

# Get scenario without ground truth (what AML system sees)
scenario = loader.get_scenario('SCN_xyz123', include_ground_truth=False)

print(f"Entities: {len(scenario['entities'])}")
print(f"Transactions: {len(scenario['transactions'])}")
# No ground truth labels visible!
```

### Get ground truth (for evaluation)
```python
# Get scenario with ground truth (for testing)
scenario_with_labels = loader.get_scenario('SCN_xyz123', include_ground_truth=True)

for txn in scenario_with_labels['transactions']:
    # Access ground truth if available
    if 'ground_truth' in scenario_with_labels:
        print(f"Transaction {txn['transaction_id']} is suspicious")
```

### Find reusable entities
```python
# Find shell companies that can be reused
reusable = loader.find_reusable_entities(
    max_scenarios=5,
    entity_types=['company', 'LLC']
)

for entity in reusable:
    print(f"{entity['name']} (used in {entity['scenarios_used_count']} scenarios)")
```

### Raw SQL queries
```python
from sqlalchemy import text

with loader.session_scope() as session:
    # Detect structuring pattern
    result = session.execute(text("""
        SELECT
            a.account_id,
            COUNT(*) as txn_count,
            SUM(t.amount) as total_amount
        FROM transactions t
        JOIN accounts a ON t.from_account_id = a.account_id
        WHERE t.amount BETWEEN 7000 AND 9999
        GROUP BY a.account_id
        HAVING COUNT(*) >= 3
    """))

    for row in result:
        print(f"Account {row.account_id}: {row.txn_count} suspicious txns")
```

## Step 8: Integration with Orchestrator

Update orchestrator to save directly to PostgreSQL:

```python
# In orchestrator.py
class AdversarialOrchestrator:
    def __init__(self, use_postgres=False):
        self.use_postgres = use_postgres
        if use_postgres:
            self.postgres_loader = PostgreSQLLoader()

    async def generate_scenario(self, ...):
        # ... existing code ...

        # Save to PostgreSQL if enabled
        if self.use_postgres:
            scenario_dict = self._convert_to_dict(scenario)
            self.postgres_loader.save_scenario(scenario_dict)

        return scenario
```

## Troubleshooting

### Connection Issues

**Error**: `could not connect to server`
```python
# Check security group allows inbound on port 5432
# Check VPC configuration
# Verify host/password in environment variables
```

**Error**: `SSL connection required`
```python
# Update config:
postgres:
  ssl_mode: "require"
```

### Performance Issues

**Slow inserts:**
```python
# Use batch inserts (already implemented in loader)
# Or use COPY for very large datasets
loader._use_copy_for_bulk_insert()
```

**Slow queries:**
```sql
-- Check indexes are being used
EXPLAIN ANALYZE SELECT * FROM transactions WHERE scenario_id = 'SCN_123';

-- Add indexes if needed
CREATE INDEX IF NOT EXISTS idx_custom ON table(column);
```

### Data Integrity

**Orphaned records:**
```sql
-- Find entities without scenarios (should not happen due to CASCADE)
SELECT e.* FROM entities e
LEFT JOIN scenarios s ON e.scenario_id = s.scenario_id
WHERE s.scenario_id IS NULL;
```

## Best Practices

1. **Use connection pooling** (already configured in loader)
2. **Separate read/write operations** for scaling
3. **Regular backups** (AWS RDS automated backups enabled)
4. **Monitor with CloudWatch**:
   - CPU utilization
   - Database connections
   - Read/Write IOPS
5. **Use read replicas** for analytics queries
6. **Partition large tables** (transactions by date if needed)

## AWS RDS Management

### Monitoring
```bash
# Check connection count
aws cloudwatch get-metric-statistics \
    --namespace AWS/RDS \
    --metric-name DatabaseConnections \
    --dimensions Name=DBInstanceIdentifier,Value=aml-adversarial-db \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Average
```

### Scaling
```bash
# Modify instance class
aws rds modify-db-instance \
    --db-instance-identifier aml-adversarial-db \
    --db-instance-class db.t3.medium \
    --apply-immediately
```

### Backup & Restore
```bash
# Create manual snapshot
aws rds create-db-snapshot \
    --db-snapshot-identifier aml-backup-20240126 \
    --db-instance-identifier aml-adversarial-db

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier aml-adversarial-db-restored \
    --db-snapshot-identifier aml-backup-20240126
```

## Cost Optimization

1. **Use appropriate instance size**:
   - Development: `db.t3.micro` (~$15/month)
   - Production: `db.t3.small` or `db.t3.medium`

2. **Enable storage autoscaling**
3. **Use gp3 storage** (cheaper than gp2)
4. **Stop instances** when not in use (dev/test)
5. **Use Reserved Instances** for production (up to 60% savings)

## Next Steps

- [Schema Design Documentation](POSTGRES_SCHEMA_DESIGN.md)
- [Loader API Reference](../src/antipode/data/loaders/postgres_loader.py)
- [Integration Example](../examples/postgres_integration_example.py)
