"""
PostgreSQL Loader for Adversarial AML Data

Provides an abstraction layer for storing and querying scenarios,
entities, accounts, transactions, and ground truth labels in PostgreSQL.

Usage:
    loader = PostgreSQLLoader()
    loader.save_scenario(scenario)
    data = loader.get_scenario('SCN_123', include_ground_truth=False)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

import yaml
from loguru import logger
from sqlalchemy import (
    create_engine, text, MetaData, Table, Column, String,
    Integer, Numeric, Boolean, DateTime, TIMESTAMP, Text, ARRAY, JSON
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.exc import SQLAlchemyError, IntegrityError


class PostgreSQLLoader:
    """
    PostgreSQL loader for adversarial AML scenario data.

    Handles:
    - Connection management with pooling
    - Scenario CRUD operations
    - Entity, account, transaction storage
    - Ground truth separation
    - Batch inserts for performance
    - Entity reuse tracking
    """

    def __init__(self, config_path: Optional[str] = None, environment: str = "development"):
        """
        Initialize PostgreSQL loader.

        Args:
            config_path: Path to postgres.yaml config file
            environment: Environment name (development, staging, production)
        """
        self.environment = environment
        self.config = self._load_config(config_path)
        self.engine = self._create_engine()
        self.Session = sessionmaker(bind=self.engine)
        self.metadata = MetaData()

        logger.info(f"PostgreSQL loader initialized (env: {environment})")

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load and merge configuration"""
        if config_path is None:
            # Default path
            config_path = Path(__file__).parents[4] / "config" / "postgres.yaml"

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Merge environment-specific config
        base_config = config['postgres']
        env_config = config.get('environments', {}).get(self.environment, {})
        merged_config = {**base_config, **env_config}

        # Replace environment variables
        merged_config = self._replace_env_vars(merged_config)

        return merged_config

    def _replace_env_vars(self, config: Dict) -> Dict:
        """Replace ${VAR} placeholders with environment variables"""
        import re

        def replace_value(value):
            if isinstance(value, str):
                # Match ${VAR} or ${VAR:-default}
                pattern = r'\$\{([^:}]+)(?::-(.*?))?\}'
                matches = re.findall(pattern, value)
                for var_name, default in matches:
                    env_value = os.getenv(var_name, default)
                    value = value.replace(f"${{{var_name}}}", env_value)
                    if default:
                        value = value.replace(f"${{{var_name}:-{default}}}", env_value)
                return value
            elif isinstance(value, dict):
                return {k: replace_value(v) for k, v in value.items()}
            return value

        return replace_value(config)

    def _create_engine(self):
        """Create SQLAlchemy engine with connection pooling"""
        # Build connection string
        conn_str = (
            f"postgresql://{self.config['user']}:{self.config['password']}"
            f"@{self.config['host']}:{self.config['port']}/{self.config['database']}"
        )

        # SSL settings for AWS RDS
        connect_args = {}
        if self.config.get('ssl_mode'):
            connect_args['sslmode'] = self.config['ssl_mode']

        # Create engine with pooling
        engine = create_engine(
            conn_str,
            poolclass=QueuePool,
            pool_size=self.config.get('pool_size', 10),
            max_overflow=self.config.get('max_overflow', 20),
            pool_timeout=self.config.get('pool_timeout', 30),
            pool_recycle=self.config.get('pool_recycle', 3600),
            echo=self.config.get('echo', False),
            echo_pool=self.config.get('echo_pool', False),
            connect_args=connect_args
        )

        logger.info(f"SQLAlchemy engine created: {self.config['host']}/{self.config['database']}")
        return engine

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope for database operations"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    # =========================================================================
    # SCENARIO OPERATIONS
    # =========================================================================

    def save_scenario(
        self,
        scenario: Dict[str, Any],
        include_ground_truth: bool = True
    ) -> str:
        """
        Save complete scenario to PostgreSQL.

        Args:
            scenario: GeneratedScenario dict with entities, accounts, transactions
            include_ground_truth: Whether to save ground truth labels

        Returns:
            scenario_id
        """
        with self.session_scope() as session:
            scenario_id = scenario['scenario_id']

            # 1. Insert scenario metadata
            self._insert_scenario_metadata(session, scenario)

            # 2. Insert entities
            entity_ids = self._insert_entities(session, scenario['entities'], scenario_id)

            # 3. Insert accounts
            account_ids = self._insert_accounts(session, scenario['accounts'], scenario_id)

            # 4. Insert transactions
            txn_ids = self._insert_transactions(session, scenario['transactions'], scenario_id)

            # 5. Insert relationships
            self._insert_relationships(session, scenario.get('relationships', []), scenario_id)

            # 6. Insert ground truth (if requested)
            if include_ground_truth and 'ground_truth' in scenario:
                self._insert_ground_truth(session, scenario, scenario_id)

            logger.info(
                f"Saved scenario {scenario_id}: "
                f"{len(entity_ids)} entities, "
                f"{len(account_ids)} accounts, "
                f"{len(txn_ids)} transactions"
            )

            return scenario_id

    def _insert_scenario_metadata(self, session: Session, scenario: Dict):
        """Insert into scenarios and scenario_metadata tables"""
        ground_truth = scenario.get('ground_truth', {})
        scenario_plan = ground_truth.get('scenario_plan', {})

        # Scenarios table
        scenario_data = {
            'scenario_id': scenario['scenario_id'],
            'typology': scenario.get('typology', 'unknown'),
            'total_amount': sum(t['amount'] for t in scenario.get('transactions', [])),
            'complexity': scenario_plan.get('complexity', 5),
            'apply_evasion': scenario.get('metadata', {}).get('apply_evasion', True),
            'scenario_description': scenario.get('metadata', {}).get('scenario_description'),
            'num_entities': len(scenario.get('entities', [])),
            'num_accounts': len(scenario.get('accounts', [])),
            'num_transactions': len(scenario.get('transactions', [])),
            'status': 'active'
        }

        session.execute(
            text("""
                INSERT INTO scenarios
                (scenario_id, typology, total_amount, complexity, apply_evasion,
                 scenario_description, num_entities, num_accounts, num_transactions, status)
                VALUES
                (:scenario_id, :typology, :total_amount, :complexity, :apply_evasion,
                 :scenario_description, :num_entities, :num_accounts, :num_transactions, :status)
                ON CONFLICT (scenario_id) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP
            """),
            scenario_data
        )

        # Scenario metadata table
        metadata_data = {
            'scenario_id': scenario['scenario_id'],
            'plan_steps': json.dumps(scenario_plan.get('steps', [])),
            'evasion_techniques': json.dumps(scenario_plan.get('evasion_techniques', [])),
            'validation_results': json.dumps(scenario.get('validation', {})),
            'memory_stats': json.dumps(scenario.get('memory_stats', {})),
            'metadata': json.dumps(scenario.get('metadata', {}))
        }

        session.execute(
            text("""
                INSERT INTO scenario_metadata
                (scenario_id, plan_steps, evasion_techniques, validation_results, memory_stats, metadata)
                VALUES
                (:scenario_id, :plan_steps::jsonb, :evasion_techniques::jsonb,
                 :validation_results::jsonb, :memory_stats::jsonb, :metadata::jsonb)
                ON CONFLICT (scenario_id) DO UPDATE SET
                    plan_steps = EXCLUDED.plan_steps,
                    evasion_techniques = EXCLUDED.evasion_techniques,
                    validation_results = EXCLUDED.validation_results,
                    memory_stats = EXCLUDED.memory_stats,
                    metadata = EXCLUDED.metadata
            """),
            metadata_data
        )

    def _insert_entities(self, session: Session, entities: List[Dict], scenario_id: str) -> List[str]:
        """Batch insert entities (visible data only)"""
        if not entities:
            return []

        entity_records = []
        for entity in entities:
            record = {
                'entity_id': entity['entity_id'],
                'scenario_id': scenario_id,
                'entity_type': entity.get('entity_type', 'individual'),
                'entity_subtype': entity.get('entity_subtype'),
                'name': entity.get('name', 'Unknown'),
                'country': entity.get('country', 'USA'),
                'created_at': entity.get('created_at', datetime.now().isoformat())
            }
            entity_records.append(record)

        # Batch insert using PostgreSQL ON CONFLICT
        if entity_records:
            session.execute(
                text("""
                    INSERT INTO entities
                    (entity_id, scenario_id, entity_type, entity_subtype, name, country, created_at)
                    VALUES
                    (:entity_id, :scenario_id, :entity_type, :entity_subtype, :name, :country, :created_at)
                    ON CONFLICT (entity_id) DO NOTHING
                """),
                entity_records
            )

        return [e['entity_id'] for e in entity_records]

    def _insert_accounts(self, session: Session, accounts: List[Dict], scenario_id: str) -> List[str]:
        """Batch insert accounts"""
        if not accounts:
            return []

        account_records = []
        for account in accounts:
            record = {
                'account_id': account['account_id'],
                'entity_id': account.get('entity_id'),
                'scenario_id': scenario_id,
                'account_type': account.get('account_type', 'checking'),
                'bank': account.get('bank', 'Unknown Bank'),
                'country': account.get('country', 'USA'),
                'currency': account.get('currency', 'USD'),
                'opened_date': account.get('opened_date', datetime.now().date())
            }
            account_records.append(record)

        if account_records:
            session.execute(
                text("""
                    INSERT INTO accounts
                    (account_id, entity_id, scenario_id, account_type, bank, country, currency, opened_date)
                    VALUES
                    (:account_id, :entity_id, :scenario_id, :account_type, :bank, :country, :currency, :opened_date)
                    ON CONFLICT (account_id) DO NOTHING
                """),
                account_records
            )

        return [a['account_id'] for a in account_records]

    def _insert_transactions(self, session: Session, transactions: List[Dict], scenario_id: str) -> List[str]:
        """Batch insert transactions"""
        if not transactions:
            return []

        txn_records = []
        for txn in transactions:
            record = {
                'transaction_id': txn['transaction_id'],
                'scenario_id': scenario_id,
                'from_account_id': txn.get('from_account_id'),
                'to_account_id': txn.get('to_account_id'),
                'amount': txn.get('amount', 0),
                'currency': txn.get('currency', 'USD'),
                'timestamp': txn.get('timestamp', datetime.now().isoformat()),
                'description': txn.get('description', ''),
                'transaction_type': txn.get('transaction_type', 'wire')
            }
            txn_records.append(record)

        if txn_records:
            session.execute(
                text("""
                    INSERT INTO transactions
                    (transaction_id, scenario_id, from_account_id, to_account_id,
                     amount, currency, timestamp, description, transaction_type)
                    VALUES
                    (:transaction_id, :scenario_id, :from_account_id, :to_account_id,
                     :amount, :currency, :timestamp, :description, :transaction_type)
                    ON CONFLICT (transaction_id) DO NOTHING
                """),
                txn_records
            )

        return [t['transaction_id'] for t in txn_records]

    def _insert_relationships(self, session: Session, relationships: List[Dict], scenario_id: str):
        """Insert entity relationships"""
        if not relationships:
            return

        rel_records = []
        for rel in relationships:
            record = {
                'scenario_id': scenario_id,
                'from_entity_id': rel.get('from_entity_id'),
                'to_entity_id': rel.get('to_entity_id'),
                'relationship_type': rel.get('relationship_type', 'transacts_with'),
                'strength': rel.get('strength', 1.0),
                'metadata': json.dumps(rel.get('metadata', {}))
            }
            rel_records.append(record)

        if rel_records:
            session.execute(
                text("""
                    INSERT INTO relationships
                    (scenario_id, from_entity_id, to_entity_id, relationship_type, strength, metadata)
                    VALUES
                    (:scenario_id, :from_entity_id, :to_entity_id, :relationship_type, :strength, :metadata::jsonb)
                """),
                rel_records
            )

    def _insert_ground_truth(self, session: Session, scenario: Dict, scenario_id: str):
        """Insert ground truth labels for entities, accounts, transactions"""
        # Entity ground truth
        for entity in scenario.get('entities', []):
            if '_ground_truth' in entity:
                gt = entity['_ground_truth']
                session.execute(
                    text("""
                        INSERT INTO entity_ground_truth
                        (entity_id, is_shell, is_nominee, is_suspicious, risk_score,
                         suspicious_indicators, role_in_scenario, scenarios_used)
                        VALUES
                        (:entity_id, :is_shell, :is_nominee, :is_suspicious, :risk_score,
                         :suspicious_indicators::jsonb, :role_in_scenario, :scenarios_used)
                        ON CONFLICT (entity_id) DO UPDATE SET
                            is_suspicious = EXCLUDED.is_suspicious,
                            role_in_scenario = EXCLUDED.role_in_scenario
                    """),
                    {
                        'entity_id': entity['entity_id'],
                        'is_shell': gt.get('is_shell', False),
                        'is_nominee': gt.get('is_nominee', False),
                        'is_suspicious': gt.get('is_suspicious', True),
                        'risk_score': gt.get('risk_score', 5),
                        'suspicious_indicators': json.dumps(gt.get('suspicious_indicators', [])),
                        'role_in_scenario': gt.get('role_in_scenario'),
                        'scenarios_used': gt.get('scenarios_used', [scenario_id])
                    }
                )

        # Transaction ground truth
        for txn in scenario.get('transactions', []):
            if '_ground_truth' in txn:
                gt = txn['_ground_truth']
                session.execute(
                    text("""
                        INSERT INTO transaction_ground_truth
                        (transaction_id, is_suspicious, suspicion_reason, typology,
                         step_number, evasion_techniques, metadata)
                        VALUES
                        (:transaction_id, :is_suspicious, :suspicion_reason, :typology,
                         :step_number, :evasion_techniques::jsonb, :metadata::jsonb)
                        ON CONFLICT (transaction_id) DO NOTHING
                    """),
                    {
                        'transaction_id': txn['transaction_id'],
                        'is_suspicious': gt.get('is_suspicious', True),
                        'suspicion_reason': gt.get('suspicion_reason', ''),
                        'typology': gt.get('typology'),
                        'step_number': gt.get('step_number'),
                        'evasion_techniques': json.dumps(gt.get('evasion_techniques', [])),
                        'metadata': json.dumps(gt.get('metadata', {}))
                    }
                )

    # =========================================================================
    # QUERY OPERATIONS
    # =========================================================================

    def get_scenario(
        self,
        scenario_id: str,
        include_ground_truth: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve scenario from PostgreSQL.

        Args:
            scenario_id: Scenario identifier
            include_ground_truth: Whether to include ground truth labels

        Returns:
            Scenario dict with entities, accounts, transactions
        """
        with self.session_scope() as session:
            # Get scenario metadata
            result = session.execute(
                text("SELECT * FROM scenarios WHERE scenario_id = :scenario_id"),
                {'scenario_id': scenario_id}
            ).fetchone()

            if not result:
                logger.warning(f"Scenario {scenario_id} not found")
                return None

            scenario_dict = dict(result._mapping)

            # Get entities
            entities = session.execute(
                text("SELECT * FROM entities WHERE scenario_id = :scenario_id"),
                {'scenario_id': scenario_id}
            ).fetchall()
            scenario_dict['entities'] = [dict(e._mapping) for e in entities]

            # Get accounts
            accounts = session.execute(
                text("SELECT * FROM accounts WHERE scenario_id = :scenario_id"),
                {'scenario_id': scenario_id}
            ).fetchall()
            scenario_dict['accounts'] = [dict(a._mapping) for a in accounts]

            # Get transactions
            transactions = session.execute(
                text("SELECT * FROM transactions WHERE scenario_id = :scenario_id"),
                {'scenario_id': scenario_id}
            ).fetchall()
            scenario_dict['transactions'] = [dict(t._mapping) for t in transactions]

            # Get relationships
            relationships = session.execute(
                text("SELECT * FROM relationships WHERE scenario_id = :scenario_id"),
                {'scenario_id': scenario_id}
            ).fetchall()
            scenario_dict['relationships'] = [dict(r._mapping) for r in relationships]

            # Get ground truth if requested
            if include_ground_truth:
                scenario_dict['ground_truth'] = self._get_ground_truth(session, scenario_id)

            return scenario_dict

    def _get_ground_truth(self, session: Session, scenario_id: str) -> Dict[str, Any]:
        """Retrieve ground truth labels for a scenario"""
        # Scenario metadata
        metadata = session.execute(
            text("SELECT * FROM scenario_metadata WHERE scenario_id = :scenario_id"),
            {'scenario_id': scenario_id}
        ).fetchone()

        ground_truth = {}
        if metadata:
            ground_truth['scenario_plan'] = {
                'steps': json.loads(metadata.plan_steps) if metadata.plan_steps else [],
                'evasion_techniques': json.loads(metadata.evasion_techniques) if metadata.evasion_techniques else []
            }

        return ground_truth

    def find_reusable_entities(
        self,
        max_scenarios: int = 5,
        entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find entities suitable for reuse.

        Args:
            max_scenarios: Maximum number of scenarios entity was used in
            entity_types: Filter by entity types (e.g., ['company', 'LLC'])

        Returns:
            List of reusable entity dicts
        """
        with self.session_scope() as session:
            query = """
                SELECT * FROM entity_reuse_stats
                WHERE scenarios_used_count <= :max_scenarios
            """

            params = {'max_scenarios': max_scenarios}

            if entity_types:
                query += " AND entity_type = ANY(:entity_types)"
                params['entity_types'] = entity_types

            query += " ORDER BY scenarios_used_count ASC LIMIT 10"

            results = session.execute(text(query), params).fetchall()
            return [dict(r._mapping) for r in results]

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self.session_scope() as session:
            stats = {}

            # Count scenarios
            stats['total_scenarios'] = session.execute(
                text("SELECT COUNT(*) FROM scenarios")
            ).scalar()

            # Count entities
            stats['total_entities'] = session.execute(
                text("SELECT COUNT(*) FROM entities")
            ).scalar()

            # Entity reuse rate
            reuse_result = session.execute(
                text("SELECT COUNT(*) FROM entity_reuse_log")
            ).scalar()
            stats['total_reuses'] = reuse_result
            stats['reuse_rate'] = reuse_result / max(1, stats['total_entities'])

            # Transaction count
            stats['total_transactions'] = session.execute(
                text("SELECT COUNT(*) FROM transactions")
            ).scalar()

            return stats

    # =========================================================================
    # UTILITY OPERATIONS
    # =========================================================================

    def delete_scenario(self, scenario_id: str):
        """Delete scenario and all related data (CASCADE)"""
        with self.session_scope() as session:
            session.execute(
                text("DELETE FROM scenarios WHERE scenario_id = :scenario_id"),
                {'scenario_id': scenario_id}
            )
            logger.info(f"Deleted scenario {scenario_id}")

    def clear_all_data(self):
        """DANGEROUS: Clear all data from all tables"""
        with self.session_scope() as session:
            tables = [
                'entity_reuse_log', 'relationships', 'transaction_ground_truth',
                'transactions', 'account_ground_truth', 'accounts',
                'entity_ground_truth', 'entities', 'scenario_metadata', 'scenarios'
            ]
            for table in tables:
                session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            logger.warning("All data cleared from database")

    def close(self):
        """Close database connections"""
        self.engine.dispose()
        logger.info("PostgreSQL connections closed")
