# PostgreSQL Implementation Summary

## What Was Implemented

A complete PostgreSQL integration for storing and querying adversarial AML scenario data on AWS RDS.

## Files Created

### 1. Schema & Documentation
- **`docs/POSTGRES_SCHEMA_DESIGN.md`**: Comprehensive schema design with 10 tables, indexes, views, and query patterns
- **`docs/POSTGRES_QUICKSTART.md`**: Step-by-step guide for setting up and using PostgreSQL
- **`docs/POSTGRES_IMPLEMENTATION_SUMMARY.md`**: This file

### 2. SQL Scripts
- **`sql/schema.sql`**: Complete DDL script with:
  - 10 tables (scenarios, entities, accounts, transactions, relationships, ground truth)
  - Indexes for performance (B-tree, GIN for JSONB)
  - Triggers for auto-updating timestamps
  - Views for common queries
  - Comments and documentation

### 3. Python Interface
- **`src/antipode/data/loaders/postgres_loader.py`**: Main PostgreSQL loader class with:
  - Connection pooling (SQLAlchemy)
  - Batch inserts for performance
  - Ground truth separation
  - Entity reuse tracking
  - Transaction support
  - ~600 lines of production-ready code

- **`src/antipode/data/loaders/__init__.py`**: Module exports

### 4. Configuration
- **`config/postgres.yaml`**: Configuration file with:
  - Connection settings (host, port, database, credentials)
  - Connection pooling parameters
  - SSL settings for AWS RDS
  - Environment-specific overrides (dev, staging, prod)
  - Batch insert settings
  - Retry logic

### 5. Examples
- **`examples/postgres_integration_example.py`**: Complete integration examples:
  - Generate and save scenarios
  - Retrieve visible data (AML system view)
  - Retrieve ground truth (evaluation view)
  - Find reusable entities
  - Database statistics
  - Pattern detection with SQL
  - Batch generation

### 6. Dependencies
- **`requirements.txt`**: Updated with PostgreSQL dependencies:
  - sqlalchemy>=2.0.0
  - psycopg2-binary>=2.9.0

## Database Schema Overview

### Core Tables

1. **scenarios** - Master table for scenario metadata
2. **scenario_metadata** - Ground truth: plans, evasion techniques
3. **entities** - Visible data: companies, individuals
4. **entity_ground_truth** - Labels: is_shell, is_suspicious, role
5. **accounts** - Visible data: bank accounts
6. **account_ground_truth** - Labels: account purpose
7. **transactions** - Visible data: financial transactions
8. **transaction_ground_truth** - Labels: suspicion reasons, typology
9. **relationships** - Entity network connections
10. **entity_reuse_log** - Memory system tracking

### Key Features

- **Ground Truth Separation**: Visible data in main tables, labels in separate `_ground_truth` tables
- **Cascading Deletes**: Delete scenario → automatically delete all related data
- **JSONB Columns**: Flexible metadata storage with GIN indexes for fast queries
- **Foreign Keys**: Maintain referential integrity
- **Timestamps**: Auto-updated timestamps for scenarios

## PostgreSQLLoader API

### Core Methods

```python
# Initialize
loader = PostgreSQLLoader(environment="development")

# Save scenario
scenario_id = loader.save_scenario(scenario_dict, include_ground_truth=True)

# Get scenario (visible data only)
scenario = loader.get_scenario(scenario_id, include_ground_truth=False)

# Get scenario with ground truth
scenario_full = loader.get_scenario(scenario_id, include_ground_truth=True)

# Find reusable entities
entities = loader.find_reusable_entities(max_scenarios=5, entity_types=['LLC'])

# Get statistics
stats = loader.get_statistics()

# Delete scenario
loader.delete_scenario(scenario_id)

# Close connections
loader.close()
```

### Transaction Support

```python
with loader.session_scope() as session:
    # All operations in this block are part of single transaction
    session.execute(text("INSERT INTO ..."))
    session.execute(text("UPDATE ..."))
    # Auto-commit on success, auto-rollback on error
```

## AWS RDS Setup

### Prerequisites
1. AWS account
2. RDS PostgreSQL 14+ instance
3. Security group allowing port 5432
4. Environment variables set:
   ```bash
   export POSTGRES_HOST="your-instance.region.rds.amazonaws.com"
   export POSTGRES_PASSWORD="your_password"
   ```

### Quick Setup
```bash
# 1. Create RDS instance (via AWS Console or CLI)
aws rds create-db-instance --db-instance-identifier aml-db ...

# 2. Create database and schema
psql -h your-host.rds.amazonaws.com -U admin -d postgres
CREATE DATABASE aml_adversarial;
\c aml_adversarial
\i sql/schema.sql

# 3. Test connection
python examples/postgres_integration_example.py
```

## Performance Considerations

### Indexes
- **B-tree indexes** on all foreign keys and commonly filtered columns
- **GIN indexes** on JSONB columns for fast JSON queries
- **Partial indexes** for common filters (e.g., suspicious entities only)

### Connection Pooling
- Default pool size: 10 connections
- Max overflow: 20 connections
- Pool timeout: 30 seconds
- Automatic connection recycling: 1 hour

### Batch Inserts
- Uses `ON CONFLICT` for upserts
- Batches multiple rows in single INSERT statement
- Option to use PostgreSQL COPY for bulk loads

### Query Optimization
```sql
-- Use views for common queries
SELECT * FROM scenario_visible_data WHERE scenario_id = 'SCN_123';

-- Use prepared statements (SQLAlchemy handles this)
-- Use EXPLAIN ANALYZE to optimize slow queries
```

## Security

### Ground Truth Separation
- **Visible tables**: entities, accounts, transactions (what AML system sees)
- **Ground truth tables**: entity_ground_truth, transaction_ground_truth (labels)
- **Separate access control**: Different roles can access different tables

### Example Role Setup
```sql
-- Read-only role for AML system (visible data only)
CREATE ROLE aml_readonly;
GRANT SELECT ON entities, accounts, transactions, relationships TO aml_readonly;

-- Admin role with ground truth access
CREATE ROLE aml_admin;
GRANT ALL ON ALL TABLES IN SCHEMA public TO aml_admin;
```

### AWS RDS Security
- SSL/TLS encryption in transit (enabled by default)
- Encryption at rest (enable in RDS console)
- VPC security groups (restrict access to application servers)
- IAM database authentication (optional)

## Integration with Existing System

### Option 1: Automatic Save
```python
# In orchestrator.py
class AdversarialOrchestrator:
    def __init__(self, use_postgres=True):
        self.postgres_loader = PostgreSQLLoader() if use_postgres else None

    async def generate_scenario(self, ...):
        scenario = ... # existing code

        # Auto-save to PostgreSQL
        if self.postgres_loader:
            self.postgres_loader.save_scenario(scenario.to_dict())

        return scenario
```

### Option 2: Manual Save
```python
# User code
orchestrator = AdversarialOrchestrator()
loader = PostgreSQLLoader()

scenario = await orchestrator.generate_scenario(...)
loader.save_scenario(scenario.to_dict())
```

### Option 3: Batch Processing
```python
# Generate multiple scenarios
scenarios = []
for i in range(10):
    scenario = await orchestrator.generate_scenario(...)
    scenarios.append(scenario)

# Batch save to PostgreSQL
loader = PostgreSQLLoader()
for scenario in scenarios:
    loader.save_scenario(scenario.to_dict())
```

## Query Examples

### 1. Get All Scenarios by Typology
```python
with loader.session_scope() as session:
    result = session.execute(text("""
        SELECT * FROM scenarios WHERE typology = :typology
    """), {'typology': 'structuring'})
```

### 2. Find Shell Companies
```python
with loader.session_scope() as session:
    result = session.execute(text("""
        SELECT e.*, egt.is_shell, egt.role_in_scenario
        FROM entities e
        JOIN entity_ground_truth egt ON e.entity_id = egt.entity_id
        WHERE egt.is_shell = TRUE
    """))
```

### 3. Detect Structuring Pattern
```python
with loader.session_scope() as session:
    result = session.execute(text("""
        SELECT
            a.account_id,
            COUNT(*) as txn_count,
            SUM(t.amount) as total
        FROM transactions t
        JOIN accounts a ON t.from_account_id = a.account_id
        WHERE t.amount BETWEEN 7000 AND 9999
        GROUP BY a.account_id
        HAVING COUNT(*) >= 3
    """))
```

### 4. Entity Network Analysis
```python
with loader.session_scope() as session:
    # Find all entities connected to ENT_123 within 2 hops
    result = session.execute(text("""
        WITH RECURSIVE network AS (
            SELECT from_entity_id, to_entity_id, 1 as depth
            FROM relationships
            WHERE from_entity_id = :entity_id
            UNION ALL
            SELECT r.from_entity_id, r.to_entity_id, n.depth + 1
            FROM relationships r
            JOIN network n ON r.from_entity_id = n.to_entity_id
            WHERE n.depth < 2
        )
        SELECT DISTINCT * FROM network
    """), {'entity_id': 'ENT_123'})
```

## Testing

### Unit Tests (To Be Created)
```python
# tests/test_postgres_loader.py
def test_save_scenario():
    loader = PostgreSQLLoader(environment="test")
    scenario = {...}
    scenario_id = loader.save_scenario(scenario)
    assert scenario_id is not None

def test_ground_truth_separation():
    loader = PostgreSQLLoader(environment="test")
    scenario = loader.get_scenario('SCN_123', include_ground_truth=False)
    assert '_ground_truth' not in scenario['entities'][0]
```

### Integration Tests
```bash
# Run example script
python examples/postgres_integration_example.py
```

## Cost Estimation (AWS RDS)

### Development
- Instance: db.t3.micro
- Storage: 20 GB gp3
- **Cost**: ~$15/month

### Production
- Instance: db.t3.medium
- Storage: 100 GB gp3
- Multi-AZ: Enabled
- **Cost**: ~$100-150/month

### Optimization
- Use Reserved Instances (up to 60% savings)
- Stop instances when not in use (dev/test)
- Use read replicas for analytics (separate from production writes)

## Next Steps

1. **Set up AWS RDS instance** (see POSTGRES_QUICKSTART.md)
2. **Run schema.sql** to create tables
3. **Test connection** with example script
4. **Integrate with orchestrator** (optional auto-save)
5. **Create dashboard** for querying scenarios (optional)
6. **Set up monitoring** (CloudWatch metrics)

## Troubleshooting

### Common Issues

**Connection timeout:**
- Check security group rules
- Verify VPC configuration
- Check environment variables

**SSL errors:**
```yaml
# In postgres.yaml
ssl_mode: "require"  # or "verify-full" for stricter validation
```

**Slow queries:**
```sql
-- Check if indexes are being used
EXPLAIN ANALYZE SELECT ...;

-- Add missing indexes
CREATE INDEX idx_custom ON table(column);
```

**Out of connections:**
```yaml
# In postgres.yaml, increase pool size
pool_size: 20
max_overflow: 40
```

## Support

- Schema docs: `docs/POSTGRES_SCHEMA_DESIGN.md`
- Quick start: `docs/POSTGRES_QUICKSTART.md`
- API reference: `src/antipode/data/loaders/postgres_loader.py`
- Examples: `examples/postgres_integration_example.py`

## Summary

You now have a complete PostgreSQL integration for the adversarial AML system:

✅ Comprehensive schema with 10 normalized tables
✅ Ground truth separation (visible data vs labels)
✅ Production-ready Python interface with connection pooling
✅ Batch inserts for performance
✅ Entity reuse tracking for memory system
✅ AWS RDS configuration and setup guide
✅ Complete examples and documentation

**Ready to deploy to AWS RDS PostgreSQL!**
