"""
Bank Schema PostgreSQL Loader

Provides interface for loading adversarial AML scenario data into the banking schema.
Maps generated entities, accounts, and transactions to the comprehensive banking data model.
"""

import os
import json
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

import yaml
from loguru import logger

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import QueuePool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logger.warning("SQLAlchemy not installed. Install with: pip install sqlalchemy psycopg2-binary")


class BankSchemaLoader:
    """
    Loader for banking schema on AWS RDS PostgreSQL.

    Maps adversarial AML scenario data to the comprehensive banking schema:
    - Entities -> Customer, CustomerPerson, CustomerCompany
    - Accounts -> Account, AccountOwnership
    - Transactions -> Transaction, Counterparty
    - Relationships -> CustomerRelationship
    - Ground Truth -> _is_suspicious, _typology, _scenario_id columns
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        environment: str = "development"
    ):
        """
        Initialize the bank schema loader.

        Args:
            config_path: Path to config file. Defaults to config/bank_postgres.yaml
            environment: Environment to use (development, staging, production)
        """
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("SQLAlchemy is required. Install with: pip install sqlalchemy psycopg2-binary")

        self.environment = environment
        self.config = self._load_config(config_path)
        self.engine = self._create_engine()
        self.Session = sessionmaker(bind=self.engine)

        # Track generated IDs for relationships
        self._customer_map: Dict[str, str] = {}  # entity_id -> customer_id
        self._account_map: Dict[str, str] = {}   # account_id -> account_id

        logger.info(f"BankSchemaLoader initialized for environment: {environment}")

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if config_path is None:
            # Find config relative to project root
            project_root = Path(__file__).parents[4]
            config_path = project_root / "config" / "bank_postgres.yaml"

        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Merge default with environment-specific settings
        default_config = config.get('default', {})
        env_config = config.get('environments', {}).get(self.environment, {})

        merged = {**default_config, **env_config}

        # Resolve environment variables in password
        password = merged.get('password', '')
        if password.startswith('${') and password.endswith('}'):
            env_var = password[2:-1]
            merged['password'] = os.environ.get(env_var, '')
            if not merged['password']:
                logger.warning(f"Environment variable {env_var} not set. Set it or update config with actual password.")

        return merged

    def _create_engine(self):
        """Create SQLAlchemy engine with connection pooling."""
        # Build connection URL
        host = self.config.get('host', 'localhost')
        port = self.config.get('port', 5432)
        database = self.config.get('database', 'antipode')
        username = self.config.get('username', 'postgres')
        password = self.config.get('password', '')
        ssl_mode = self.config.get('ssl_mode', 'require')

        # PostgreSQL connection URL
        url = f"postgresql://{username}:{password}@{host}:{port}/{database}"

        # SSL args for AWS RDS
        connect_args = {}
        if ssl_mode and ssl_mode != 'disable':
            connect_args['sslmode'] = ssl_mode
            ssl_root_cert = self.config.get('ssl_root_cert')
            if ssl_root_cert:
                connect_args['sslrootcert'] = ssl_root_cert

        # Create engine with connection pooling
        engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=self.config.get('pool_size', 10),
            max_overflow=self.config.get('max_overflow', 20),
            pool_timeout=self.config.get('pool_timeout', 30),
            pool_recycle=self.config.get('pool_recycle', 3600),
            connect_args=connect_args,
            echo=self.config.get('logging', {}).get('log_queries', False)
        )

        return engine

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.session_scope() as session:
                result = session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def execute_schema(self, schema_path: Optional[str] = None) -> bool:
        """
        Execute the bank schema DDL to create tables.

        Args:
            schema_path: Path to schema SQL file. Defaults to sql/bank_schema.sql

        Returns:
            True if successful, False otherwise
        """
        if schema_path is None:
            project_root = Path(__file__).parents[4]
            schema_path = project_root / "sql" / "bank_schema.sql"

        schema_path = Path(schema_path)

        if not schema_path.exists():
            logger.error(f"Schema file not found: {schema_path}")
            return False

        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        try:
            with self.session_scope() as session:
                # Execute schema DDL
                # Split by statement and execute each
                statements = schema_sql.split(';')
                for stmt in statements:
                    stmt = stmt.strip()
                    if stmt and not stmt.startswith('--'):
                        try:
                            session.execute(text(stmt))
                        except Exception as e:
                            # Some statements may fail if objects already exist
                            logger.debug(f"Statement skipped (may already exist): {e}")

                logger.info("Bank schema executed successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to execute schema: {e}")
            return False

    def save_scenario(
        self,
        scenario: Dict[str, Any],
        include_ground_truth: bool = True
    ) -> str:
        """
        Save a complete scenario to the banking schema.

        Args:
            scenario: Dictionary containing entities, accounts, transactions, etc.
            include_ground_truth: Whether to populate ground truth columns

        Returns:
            Scenario ID
        """
        scenario_id = scenario.get('scenario_id', str(uuid.uuid4()))

        logger.info(f"Saving scenario {scenario_id} to bank schema")

        with self.session_scope() as session:
            # Reset ID maps for this scenario
            self._customer_map = {}
            self._account_map = {}

            # 1. Insert entities as customers
            entities = scenario.get('entities', [])
            for entity in entities:
                self._insert_customer(session, entity, scenario_id, include_ground_truth)

            # 2. Insert accounts
            accounts = scenario.get('accounts', [])
            for account in accounts:
                self._insert_account(session, account, scenario_id, include_ground_truth)

            # 3. Insert transactions
            transactions = scenario.get('transactions', [])
            for txn in transactions:
                self._insert_transaction(session, txn, scenario_id, include_ground_truth)

            # 4. Insert relationships
            relationships = scenario.get('relationships', [])
            for rel in relationships:
                self._insert_relationship(session, rel, scenario_id)

            logger.info(f"Saved scenario {scenario_id}: {len(entities)} customers, "
                       f"{len(accounts)} accounts, {len(transactions)} transactions")

        return scenario_id

    def _generate_customer_id(self) -> str:
        """Generate a customer ID in the expected format."""
        return f"C{datetime.now().strftime('%y%m%d')}{uuid.uuid4().hex[:8].upper()}"

    def _insert_customer(
        self,
        session,
        entity: Dict[str, Any],
        scenario_id: str,
        include_ground_truth: bool
    ):
        """Insert an entity as a Customer record."""
        entity_id = entity.get('entity_id', entity.get('id', str(uuid.uuid4())))
        entity_type = entity.get('entity_type', entity.get('type', 'PERSON')).upper()

        # Generate customer_id
        customer_id = self._generate_customer_id()
        self._customer_map[entity_id] = customer_id

        # Determine customer type
        is_company = entity_type in ['COMPANY', 'LLC', 'CORPORATION', 'SHELL_COMPANY', 'BUSINESS']
        customer_type = 'COMPANY' if is_company else 'PERSON'

        # Map risk rating
        risk_rating = entity.get('risk_rating', 'MEDIUM').upper()
        if risk_rating not in ['LOW', 'MEDIUM', 'HIGH', 'PROHIBITED']:
            risk_rating = 'MEDIUM'

        # Map segment
        segment = 'SME' if is_company else 'RETAIL'
        if entity.get('is_high_net_worth') or entity.get('total_assets', 0) > 1000000:
            segment = 'CORPORATE' if is_company else 'PRIVATE_BANKING'

        # Base customer insert
        customer_sql = text("""
            INSERT INTO Customer (
                customer_id, customer_type, onboarding_date, status, risk_rating, segment,
                kyc_refresh_date, pep_flag, sanctions_flag, adverse_media_flag,
                _is_suspicious, _scenario_id
            ) VALUES (
                %(customer_id)s, %(customer_type)s::customer_type_enum, %(onboarding_date)s,
                'ACTIVE'::customer_status_enum, %(risk_rating)s::risk_rating_enum,
                %(segment)s::customer_segment_enum,
                %(kyc_refresh_date)s, %(pep_flag)s, %(sanctions_flag)s, %(adverse_media_flag)s,
                %(is_suspicious)s, %(scenario_id)s
            )
            ON CONFLICT (customer_id) DO NOTHING
        """)

        onboarding_date = entity.get('created_date', date.today() - timedelta(days=365))
        if isinstance(onboarding_date, str):
            onboarding_date = datetime.fromisoformat(onboarding_date).date()

        session.execute(customer_sql, {
            'customer_id': customer_id,
            'customer_type': customer_type,
            'onboarding_date': onboarding_date,
            'risk_rating': risk_rating,
            'segment': segment,
            'kyc_refresh_date': onboarding_date + timedelta(days=365),
            'pep_flag': entity.get('is_pep', False),
            'sanctions_flag': entity.get('is_sanctioned', False),
            'adverse_media_flag': entity.get('has_adverse_media', False),
            'is_suspicious': entity.get('is_suspicious', False) if include_ground_truth else None,
            'scenario_id': scenario_id if include_ground_truth else None
        })

        # Insert type-specific record
        if is_company:
            self._insert_company(session, entity, customer_id)
        else:
            self._insert_person(session, entity, customer_id)

        # Insert address if available
        if entity.get('address') or entity.get('country'):
            self._insert_address(session, entity, customer_id)

    def _insert_person(self, session, entity: Dict[str, Any], customer_id: str):
        """Insert CustomerPerson record."""
        name = entity.get('name', 'Unknown Person')
        name_parts = name.split(' ', 2)
        first_name = name_parts[0] if len(name_parts) > 0 else 'Unknown'
        last_name = name_parts[-1] if len(name_parts) > 1 else 'Unknown'
        middle_name = name_parts[1] if len(name_parts) > 2 else None

        person_sql = text("""
            INSERT INTO CustomerPerson (
                customer_id, first_name, middle_name, last_name,
                date_of_birth, nationality, occupation, employer
            ) VALUES (
                %(customer_id)s, %(first_name)s, %(middle_name)s, %(last_name)s,
                %(dob)s, %(nationality)s, %(occupation)s, %(employer)s
            )
            ON CONFLICT (customer_id) DO NOTHING
        """)

        session.execute(person_sql, {
            'customer_id': customer_id,
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'dob': entity.get('date_of_birth'),
            'nationality': entity.get('nationality', entity.get('country')),
            'occupation': entity.get('occupation'),
            'employer': entity.get('employer')
        })

    def _insert_company(self, session, entity: Dict[str, Any], customer_id: str):
        """Insert CustomerCompany record."""
        company_sql = text("""
            INSERT INTO CustomerCompany (
                customer_id, legal_name, trade_name, registration_number,
                incorporation_date, incorporation_country, legal_form,
                industry_code, industry_description, employee_count, annual_revenue
            ) VALUES (
                %(customer_id)s, %(legal_name)s, %(trade_name)s, %(registration_number)s,
                %(incorporation_date)s, %(incorporation_country)s, %(legal_form)s::legal_form_enum,
                %(industry_code)s, %(industry_description)s, %(employee_count)s, %(annual_revenue)s
            )
            ON CONFLICT (customer_id) DO NOTHING
        """)

        # Map entity type to legal form
        entity_type = entity.get('entity_type', 'LLC').upper()
        legal_form_map = {
            'LLC': 'LLC',
            'CORPORATION': 'CORPORATION',
            'COMPANY': 'LLC',
            'SHELL_COMPANY': 'LLC',
            'PARTNERSHIP': 'PARTNERSHIP',
            'SOLE_PROPRIETORSHIP': 'SOLE_PROPRIETORSHIP',
            'TRUST': 'TRUST',
            'FOUNDATION': 'FOUNDATION',
            'NON_PROFIT': 'NON_PROFIT'
        }
        legal_form = legal_form_map.get(entity_type, 'LLC')

        session.execute(company_sql, {
            'customer_id': customer_id,
            'legal_name': entity.get('name', 'Unknown Company'),
            'trade_name': entity.get('trade_name'),
            'registration_number': entity.get('registration_number', entity.get('entity_id')),
            'incorporation_date': entity.get('incorporation_date'),
            'incorporation_country': entity.get('country', entity.get('jurisdiction')),
            'legal_form': legal_form,
            'industry_code': entity.get('industry_code'),
            'industry_description': entity.get('industry', entity.get('business_type')),
            'employee_count': entity.get('employee_count'),
            'annual_revenue': entity.get('annual_revenue')
        })

        # Insert company officers if available
        officers = entity.get('officers', entity.get('beneficial_owners', []))
        for officer in officers:
            self._insert_company_officer(session, officer, customer_id)

    def _insert_company_officer(self, session, officer: Dict[str, Any], company_customer_id: str):
        """Insert CompanyOfficer record."""
        officer_sql = text("""
            INSERT INTO CompanyOfficer (
                officer_id, company_customer_id, officer_type, full_name,
                ownership_pct, appointment_date, is_beneficial_owner
            ) VALUES (
                %(officer_id)s, %(company_customer_id)s, %(officer_type)s::officer_type_enum,
                %(full_name)s, %(ownership_pct)s, %(appointment_date)s, %(is_beneficial_owner)s
            )
            ON CONFLICT (officer_id) DO NOTHING
        """)

        officer_type = officer.get('role', 'DIRECTOR').upper()
        if officer_type not in ['DIRECTOR', 'SHAREHOLDER', 'UBO', 'SECRETARY', 'CEO', 'CFO', 'AUTHORIZED_SIGNATORY']:
            officer_type = 'DIRECTOR'

        session.execute(officer_sql, {
            'officer_id': officer.get('id', str(uuid.uuid4())),
            'company_customer_id': company_customer_id,
            'officer_type': officer_type,
            'full_name': officer.get('name', 'Unknown Officer'),
            'ownership_pct': officer.get('ownership_percentage'),
            'appointment_date': officer.get('appointment_date'),
            'is_beneficial_owner': officer.get('is_beneficial_owner', officer_type == 'UBO')
        })

    def _insert_address(self, session, entity: Dict[str, Any], customer_id: str):
        """Insert CustomerAddress record."""
        address_sql = text("""
            INSERT INTO CustomerAddress (
                address_id, customer_id, address_type, line1, line2,
                city, state_province, postal_code, country, is_primary
            ) VALUES (
                %(address_id)s, %(customer_id)s, %(address_type)s::address_type_enum,
                %(line1)s, %(line2)s, %(city)s, %(state_province)s, %(postal_code)s, %(country)s, TRUE
            )
            ON CONFLICT (address_id) DO NOTHING
        """)

        address = entity.get('address', {})
        if isinstance(address, str):
            address = {'line1': address}

        session.execute(address_sql, {
            'address_id': str(uuid.uuid4()),
            'customer_id': customer_id,
            'address_type': 'RESIDENTIAL' if entity.get('entity_type', 'PERSON').upper() == 'PERSON' else 'REGISTERED',
            'line1': address.get('line1', address.get('street', entity.get('address', 'Unknown'))),
            'line2': address.get('line2'),
            'city': address.get('city', entity.get('city')),
            'state_province': address.get('state', entity.get('state')),
            'postal_code': address.get('postal_code', entity.get('zip')),
            'country': address.get('country', entity.get('country', 'US'))
        })

    def _generate_account_id(self) -> str:
        """Generate an account ID in the expected format."""
        return f"A{datetime.now().strftime('%y%m%d')}{uuid.uuid4().hex[:10].upper()}"

    def _insert_account(
        self,
        session,
        account: Dict[str, Any],
        scenario_id: str,
        include_ground_truth: bool
    ):
        """Insert an Account record."""
        original_account_id = account.get('account_id', account.get('id', str(uuid.uuid4())))

        # Generate new account ID or use existing
        account_id = self._generate_account_id()
        self._account_map[original_account_id] = account_id

        # Get customer ID from entity mapping
        entity_id = account.get('entity_id', account.get('owner_id'))
        customer_id = self._customer_map.get(entity_id)

        if not customer_id:
            logger.warning(f"No customer found for account {original_account_id}, entity {entity_id}")
            return

        # Map account type
        account_type = account.get('account_type', 'CHECKING').upper()
        type_map = {
            'CHECKING': 'CHECKING',
            'SAVINGS': 'SAVINGS',
            'MONEY_MARKET': 'MONEY_MARKET',
            'CD': 'CD',
            'LOAN': 'LOAN',
            'MORTGAGE': 'MORTGAGE',
            'CREDIT_CARD': 'CREDIT_CARD',
            'BROKERAGE': 'BROKERAGE',
            'BUSINESS': 'CHECKING',
            'PERSONAL': 'CHECKING'
        }
        account_type = type_map.get(account_type, 'CHECKING')

        account_sql = text("""
            INSERT INTO Account (
                account_id, account_type, currency, open_date, status,
                branch_id, current_balance, available_balance,
                _is_suspicious, _scenario_id
            ) VALUES (
                %(account_id)s, %(account_type)s::account_type_enum, %(currency)s,
                %(open_date)s, 'ACTIVE'::account_status_enum,
                %(branch_id)s, %(current_balance)s, %(available_balance)s,
                %(is_suspicious)s, %(scenario_id)s
            )
            ON CONFLICT (account_id) DO NOTHING
        """)

        open_date = account.get('open_date', date.today() - timedelta(days=180))
        if isinstance(open_date, str):
            open_date = datetime.fromisoformat(open_date).date()

        session.execute(account_sql, {
            'account_id': account_id,
            'account_type': account_type,
            'currency': account.get('currency', 'USD'),
            'open_date': open_date,
            'branch_id': account.get('branch_id', 'BR001'),
            'current_balance': account.get('balance', account.get('current_balance', 0)),
            'available_balance': account.get('available_balance', account.get('balance', 0)),
            'is_suspicious': account.get('is_suspicious', False) if include_ground_truth else None,
            'scenario_id': scenario_id if include_ground_truth else None
        })

        # Insert AccountOwnership
        ownership_sql = text("""
            INSERT INTO AccountOwnership (
                ownership_id, account_id, customer_id, ownership_type, ownership_pct
            ) VALUES (
                %(ownership_id)s, %(account_id)s, %(customer_id)s,
                %(ownership_type)s::ownership_type_enum, %(ownership_pct)s
            )
            ON CONFLICT (ownership_id) DO NOTHING
        """)

        session.execute(ownership_sql, {
            'ownership_id': str(uuid.uuid4()),
            'account_id': account_id,
            'customer_id': customer_id,
            'ownership_type': 'PRIMARY',
            'ownership_pct': Decimal('100.00')
        })

    def _insert_transaction(
        self,
        session,
        txn: Dict[str, Any],
        scenario_id: str,
        include_ground_truth: bool
    ):
        """Insert a Transaction record."""
        txn_id = txn.get('txn_id', txn.get('transaction_id', str(uuid.uuid4())))

        # Get mapped account IDs
        from_account = txn.get('from_account_id', txn.get('source_account'))
        to_account = txn.get('to_account_id', txn.get('destination_account'))

        # Map to new account IDs
        account_id = self._account_map.get(from_account)
        counterparty_account_id = self._account_map.get(to_account)

        if not account_id:
            # Try using to_account as the primary
            account_id = self._account_map.get(to_account)
            counterparty_account_id = self._account_map.get(from_account)
            direction = 'CREDIT'
        else:
            direction = 'DEBIT'

        if not account_id:
            logger.warning(f"No account mapping found for transaction {txn_id}")
            return

        # Map transaction type
        txn_type = txn.get('txn_type', txn.get('type', 'WIRE')).upper()
        type_map = {
            'WIRE': 'WIRE',
            'ACH': 'ACH',
            'CASH_DEPOSIT': 'CASH_DEPOSIT',
            'CASH_WITHDRAWAL': 'CASH_WITHDRAWAL',
            'CHECK_DEPOSIT': 'CHECK_DEPOSIT',
            'CHECK_ISSUED': 'CHECK_ISSUED',
            'INTERNAL_TRANSFER': 'INTERNAL_TRANSFER',
            'CARD_PURCHASE': 'CARD_PURCHASE',
            'ATM': 'ATM',
            'FEE': 'FEE',
            'INTEREST': 'INTEREST',
            'TRANSFER': 'WIRE',
            'DEPOSIT': 'CASH_DEPOSIT',
            'WITHDRAWAL': 'CASH_WITHDRAWAL'
        }
        txn_type = type_map.get(txn_type, 'WIRE')

        # Parse timestamp
        txn_timestamp = txn.get('timestamp', txn.get('date', datetime.now()))
        if isinstance(txn_timestamp, str):
            txn_timestamp = datetime.fromisoformat(txn_timestamp.replace('Z', '+00%(00)s'))
        elif isinstance(txn_timestamp, date) and not isinstance(txn_timestamp, datetime):
            txn_timestamp = datetime.combine(txn_timestamp, datetime.min.time())

        txn_sql = text("""
            INSERT INTO Transaction (
                txn_id, account_id, direction, txn_type, amount, currency,
                txn_timestamp, value_date, channel, description, reference,
                counterparty_account_id, counterparty_name, counterparty_bank_code,
                counterparty_country, originator_name, beneficiary_name,
                _is_suspicious, _typology, _scenario_id
            ) VALUES (
                %(txn_id)s, %(account_id)s, %(direction)s::txn_direction_enum,
                %(txn_type)s::txn_type_enum, %(amount)s, %(currency)s,
                %(txn_timestamp)s, %(value_date)s, %(channel)s::channel_enum, %(description)s, %(reference)s,
                %(counterparty_account_id)s, %(counterparty_name)s, %(counterparty_bank_code)s,
                %(counterparty_country)s, %(originator_name)s, %(beneficiary_name)s,
                %(is_suspicious)s, %(typology)s, %(scenario_id)s
            )
            ON CONFLICT (txn_id) DO NOTHING
        """)

        # Map channel
        channel = txn.get('channel', 'ONLINE').upper()
        if channel not in ['BRANCH', 'ONLINE', 'MOBILE', 'ATM', 'PHONE', 'API']:
            channel = 'ONLINE'

        session.execute(txn_sql, {
            'txn_id': txn_id,
            'account_id': account_id,
            'direction': direction,
            'txn_type': txn_type,
            'amount': Decimal(str(txn.get('amount', 0))),
            'currency': txn.get('currency', 'USD'),
            'txn_timestamp': txn_timestamp,
            'value_date': txn_timestamp.date() if isinstance(txn_timestamp, datetime) else txn_timestamp,
            'channel': channel,
            'description': txn.get('description', txn.get('memo')),
            'reference': txn.get('reference', txn_id),
            'counterparty_account_id': counterparty_account_id,
            'counterparty_name': txn.get('counterparty_name', txn.get('to_entity_name')),
            'counterparty_bank_code': txn.get('counterparty_bank_code'),
            'counterparty_country': txn.get('counterparty_country'),
            'originator_name': txn.get('originator_name', txn.get('from_entity_name')),
            'beneficiary_name': txn.get('beneficiary_name', txn.get('to_entity_name')),
            'is_suspicious': txn.get('is_suspicious', False) if include_ground_truth else None,
            'typology': txn.get('typology', txn.get('suspicious_typology')) if include_ground_truth else None,
            'scenario_id': scenario_id if include_ground_truth else None
        })

    def _insert_relationship(
        self,
        session,
        relationship: Dict[str, Any],
        scenario_id: str
    ):
        """Insert a CustomerRelationship record."""
        from_entity = relationship.get('from_entity_id', relationship.get('source'))
        to_entity = relationship.get('to_entity_id', relationship.get('target'))

        from_customer = self._customer_map.get(from_entity)
        to_customer = self._customer_map.get(to_entity)

        if not from_customer or not to_customer:
            logger.warning(f"Missing customer mapping for relationship: {from_entity} -> {to_entity}")
            return

        # Map relationship type
        rel_type = relationship.get('relationship_type', relationship.get('type', 'BUSINESS_PARTNER')).upper()
        type_map = {
            'BUSINESS_PARTNER': 'BUSINESS_PARTNER',
            'FAMILY': 'FAMILY',
            'EMPLOYER': 'EMPLOYER',
            'BENEFICIAL_OWNER': 'BENEFICIAL_OWNER',
            'AUTHORIZED_SIGNER': 'AUTHORIZED_SIGNER',
            'GUARANTOR': 'GUARANTOR',
            'CONTROLS': 'BENEFICIAL_OWNER',
            'OWNS': 'BENEFICIAL_OWNER',
            'WORKS_FOR': 'EMPLOYER',
            'RELATED_TO': 'FAMILY'
        }
        rel_type = type_map.get(rel_type, 'BUSINESS_PARTNER')

        rel_sql = text("""
            INSERT INTO CustomerRelationship (
                relationship_id, from_customer_id, to_customer_id,
                relationship_type, start_date, verified
            ) VALUES (
                %(relationship_id)s, %(from_customer_id)s, %(to_customer_id)s,
                %(relationship_type)s::relationship_type_enum, %(start_date)s, %(verified)s
            )
            ON CONFLICT (relationship_id) DO NOTHING
        """)

        session.execute(rel_sql, {
            'relationship_id': relationship.get('id', str(uuid.uuid4())),
            'from_customer_id': from_customer,
            'to_customer_id': to_customer,
            'relationship_type': rel_type,
            'start_date': relationship.get('start_date', date.today()),
            'verified': relationship.get('verified', True)
        })

    def get_scenario_data(
        self,
        scenario_id: str,
        include_ground_truth: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieve scenario data from the bank schema.

        Args:
            scenario_id: The scenario ID to retrieve
            include_ground_truth: Whether to include ground truth columns

        Returns:
            Dictionary with customers, accounts, transactions
        """
        result = {
            'scenario_id': scenario_id,
            'customers': [],
            'accounts': [],
            'transactions': []
        }

        with self.session_scope() as session:
            # Get customers
            gt_cols = ", _is_suspicious, _scenario_id" if include_ground_truth else ""
            customers_sql = text(f"""
                SELECT c.*, cp.first_name, cp.last_name, cp.nationality,
                       cc.legal_name, cc.industry_description {gt_cols}
                FROM Customer c
                LEFT JOIN CustomerPerson cp ON c.customer_id = cp.customer_id
                LEFT JOIN CustomerCompany cc ON c.customer_id = cc.customer_id
                WHERE c._scenario_id = %(scenario_id)s
            """)

            customers = session.execute(customers_sql, {'scenario_id': scenario_id}).mappings().all()
            result['customers'] = [dict(c) for c in customers]

            # Get accounts
            gt_cols = ", _is_suspicious, _scenario_id" if include_ground_truth else ""
            accounts_sql = text(f"""
                SELECT a.*, ao.customer_id, ao.ownership_type {gt_cols}
                FROM Account a
                JOIN AccountOwnership ao ON a.account_id = ao.account_id
                WHERE a._scenario_id = %(scenario_id)s
            """)

            accounts = session.execute(accounts_sql, {'scenario_id': scenario_id}).mappings().all()
            result['accounts'] = [dict(a) for a in accounts]

            # Get transactions
            gt_cols = ", _is_suspicious, _typology, _scenario_id" if include_ground_truth else ""
            txns_sql = text(f"""
                SELECT * {gt_cols}
                FROM Transaction
                WHERE _scenario_id = %(scenario_id)s
            """)

            txns = session.execute(txns_sql, {'scenario_id': scenario_id}).mappings().all()
            result['transactions'] = [dict(t) for t in txns]

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats = {}

        with self.session_scope() as session:
            # Count tables
            tables = ['Customer', 'Account', 'Transaction', 'CustomerRelationship']

            for table in tables:
                try:
                    result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    stats[f'total_{table.lower()}s'] = result.scalar()
                except Exception as e:
                    stats[f'total_{table.lower()}s'] = f"Error: {e}"

            # Count scenarios
            try:
                result = session.execute(text(
                    "SELECT COUNT(DISTINCT _scenario_id) FROM Customer WHERE _scenario_id IS NOT NULL"
                ))
                stats['total_scenarios'] = result.scalar()
            except Exception:
                stats['total_scenarios'] = 0

        return stats

    def delete_scenario(self, scenario_id: str) -> bool:
        """
        Delete all data for a scenario.

        Args:
            scenario_id: The scenario ID to delete

        Returns:
            True if successful
        """
        with self.session_scope() as session:
            # Delete in order (due to foreign keys)
            tables = [
                'Transaction',
                'AccountOwnership',
                'Account',
                'CustomerRelationship',
                'CompanyOfficer',
                'CustomerAddress',
                'CustomerIdentifier',
                'CustomerPerson',
                'CustomerCompany',
                'Customer'
            ]

            for table in tables:
                try:
                    session.execute(text(f"""
                        DELETE FROM {table} WHERE _scenario_id = %(scenario_id)s
                    """), {'scenario_id': scenario_id})
                except Exception as e:
                    # Some tables may not have _scenario_id column
                    logger.debug(f"Skipped {table}: {e}")

            logger.info(f"Deleted scenario: {scenario_id}")
            return True

    def close(self):
        """Close database connections."""
        self.engine.dispose()
        logger.info("BankSchemaLoader connections closed")


def test_connection():
    """Test the database connection."""
    try:
        loader = BankSchemaLoader(environment="development")

        if loader.test_connection():
            print("[SUCCESS] Connected to AWS RDS PostgreSQL")

            stats = loader.get_statistics()
            print("\nDatabase Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        else:
            print("[FAILED] Could not connect to database")
            print("Check your configuration in config/bank_postgres.yaml")
            print("Ensure BANK_POSTGRES_PASSWORD environment variable is set")

        loader.close()

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_connection()
