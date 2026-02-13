"""
Direct PostgreSQL loader for bank schema using psycopg2
Bypasses SQLAlchemy complexity for cleaner SQL execution
"""

import psycopg2
from psycopg2.extras import execute_values
import os
import logging
from typing import List, Dict, Any
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DirectBankLoader:
    """Load enriched scenario data directly into PostgreSQL bank schema"""

    def __init__(self):
        """Initialize database connection parameters"""
        self.host = os.environ.get('BANK_DB_HOST', '${POSTGRES_HOST:-your-rds-instance.region.rds.amazonaws.com}')
        self.port = int(os.environ.get('BANK_DB_PORT', '5432'))
        self.database = os.environ.get('BANK_DB_NAME', 'postgres')
        self.user = os.environ.get('BANK_DB_USER', 'postgres')
        self.password = os.environ.get('BANK_POSTGRES_PASSWORD')

        if not self.password:
            raise ValueError("BANK_POSTGRES_PASSWORD environment variable not set")

    def load_scenario(self, scenario: Dict[str, Any]) -> bool:
        """Load a complete scenario into the database"""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                sslmode='require'
            )
            conn.autocommit = False  # Explicit transaction control
            cursor = conn.cursor()

            scenario_id = scenario.get('scenario_id', 'unknown')
            logger.info(f"Loading scenario {scenario_id} into PostgreSQL")

            # Load entities as customers
            entities = scenario.get('entities', [])
            customer_count = self._load_customers(cursor, entities, scenario_id, conn)

            # Load accounts
            accounts = scenario.get('accounts', [])
            account_count = self._load_accounts(cursor, accounts, scenario_id, conn)

            # Load transactions
            transactions = scenario.get('transactions', [])
            txn_count = self._load_transactions(cursor, transactions, scenario_id, conn)

            # Load relationships
            relationships = scenario.get('relationships', [])
            rel_count = self._load_relationships(cursor, relationships, scenario_id, conn)

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(
                f"Loaded scenario {scenario_id}: {customer_count} customers, "
                f"{account_count} accounts, {txn_count} transactions, {rel_count} relationships"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to load scenario: {e}")
            if conn:
                conn.rollback()
            raise

    def _load_customers(self, cursor, entities: List[Dict], scenario_id: str, conn=None) -> int:
        """Load entities as Customer records"""
        count = 0

        for entity in entities:
            savepoint = f"sp_{count}"
            try:
                if conn:
                    cursor.execute(f"SAVEPOINT {savepoint}")
                customer_id = entity.get('customer_id') or self._generate_customer_id()
                customer_type = entity.get('customer_type', 'PERSON').upper()
                onboarding_date = entity.get('onboarding_date', date.today())
                risk_rating = entity.get('risk_rating', 'MEDIUM').upper()
                segment = entity.get('segment', 'RETAIL').upper()

                # Insert Customer
                cursor.execute("""
                    INSERT INTO Customer (
                        customer_id, customer_type, onboarding_date, status, risk_rating, segment,
                        relationship_manager_id, kyc_date, next_review_date, source_system
                    ) VALUES (%s, %s::customer_type_enum, %s, 'ACTIVE'::customer_status_enum,
                        %s::risk_rating_enum, %s::customer_segment_enum, %s, %s, %s, %s)
                    ON CONFLICT (customer_id) DO NOTHING
                """, (
                    customer_id, customer_type, onboarding_date,
                    risk_rating, segment,
                    entity.get('relationship_manager_id'),
                    entity.get('kyc_date', onboarding_date),
                    entity.get('next_review_date'),
                    'ADVERSARIAL_GENERATOR'
                ))

                # Insert PersonCustomer if individual
                person_details = entity.get('person_details')
                if person_details and customer_type == 'PERSON':
                    first_name = person_details.get('first_name', 'Unknown')
                    last_name = person_details.get('last_name', 'Unknown')
                    full_name = f"{first_name} {last_name}".strip()

                    cursor.execute("""
                        INSERT INTO CustomerPerson (
                            customer_id, title, first_name, middle_name, last_name, full_name,
                            date_of_birth, nationality, country_of_residence, country_of_birth,
                            gender, occupation, employer, industry, annual_income, source_of_wealth,
                            is_pep, pep_type, pep_status, pep_position, pep_country,
                            tax_residency, fatca_status, crs_status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                 %s, %s::pep_type_enum, %s::pep_status_enum, %s, %s, %s, %s::fatca_status_enum, %s::crs_status_enum)
                        ON CONFLICT (customer_id) DO NOTHING
                    """, (
                        customer_id,
                        None,  # title
                        first_name,
                        person_details.get('middle_name'),
                        last_name,
                        full_name,
                        person_details.get('date_of_birth'),
                        person_details.get('nationality', 'US'),
                        person_details.get('country_of_residence', entity.get('country', 'US')),
                        person_details.get('country_of_birth'),
                        person_details.get('gender'),
                        person_details.get('occupation'),
                        person_details.get('employer'),
                        person_details.get('industry'),
                        person_details.get('annual_income'),
                        person_details.get('source_of_wealth'),
                        person_details.get('is_pep', False),
                        person_details.get('pep_type', 'NONE'),
                        person_details.get('pep_status', 'NOT_PEP'),
                        person_details.get('pep_position'),
                        person_details.get('pep_country'),
                        person_details.get('tax_residency'),
                        person_details.get('fatca_status', 'US_PERSON'),
                        person_details.get('crs_status', 'NONREPORTABLE')
                    ))

                # Insert CompanyCustomer if company
                company_details = entity.get('company_details')
                if company_details and customer_type == 'COMPANY':
                    cursor.execute("""
                        INSERT INTO CustomerCompany (
                            customer_id, legal_name, trade_name, registration_number,
                            incorporation_date, incorporation_country, legal_form,
                            industry_code, industry_description, employee_count, annual_revenue
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (customer_id) DO NOTHING
                    """, (
                        customer_id,
                        company_details.get('legal_name'),
                        company_details.get('trade_name'),
                        company_details.get('registration_number'),
                        company_details.get('incorporation_date'),
                        company_details.get('incorporation_country'),
                        company_details.get('company_type', 'PRIVATE'),
                        company_details.get('industry_code'),
                        company_details.get('industry_description'),
                        company_details.get('employee_count'),
                        company_details.get('annual_revenue')
                    ))

                # Insert Address
                address = entity.get('address')
                if address:
                    cursor.execute("""
                        INSERT INTO CustomerAddress (
                            customer_id, address_type, address_line1, address_line2,
                            city, state_or_province, postal_code, country
                        ) VALUES (%s, %s::address_type_enum, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (customer_id, address_type) DO NOTHING
                    """, (
                        customer_id,
                        address.get('address_type', 'RESIDENTIAL'),
                        address.get('line1'),
                        address.get('line2'),
                        address.get('city'),
                        address.get('state_province'),
                        address.get('postal_code'),
                        address.get('country')
                    ))

                # Insert Identifiers
                identifiers = entity.get('identifiers', [])
                for identifier in identifiers:
                    cursor.execute("""
                        INSERT INTO CustomerIdentifier (
                            customer_id, id_type, id_number, issuing_country,
                            issue_date, expiry_date, is_primary, verified
                        ) VALUES (%s, %s::id_type_enum, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (customer_id, id_type) DO NOTHING
                    """, (
                        customer_id,
                        identifier.get('id_type'),
                        identifier.get('id_number'),
                        identifier.get('issuing_country'),
                        identifier.get('issue_date'),
                        identifier.get('expiry_date'),
                        identifier.get('is_primary', False),
                        identifier.get('verified', False)
                    ))

                count += 1

            except Exception as e:
                logger.warning(f"Failed to load entity: {e}")
                continue

        return count

    def _load_accounts(self, cursor, accounts: List[Dict], scenario_id: str) -> int:
        """Load Account records"""
        count = 0

        for account in accounts:
            try:
                account_id = account.get('account_id') or self._generate_account_id()

                cursor.execute("""
                    INSERT INTO Account (
                        account_id, account_number, product_type, product_name,
                        currency, country, branch_code, branch_name, open_date, close_date,
                        status, purpose, declared_monthly_turnover, declared_source_of_funds, is_joint
                    ) VALUES (%s, %s, %s::product_type_enum, %s, %s, %s, %s, %s, %s, %s,
                        %s::account_status_enum, %s, %s, %s, %s)
                    ON CONFLICT (account_id) DO NOTHING
                """, (
                    account_id,
                    account.get('account_number'),
                    account.get('product_type', 'CHECKING'),
                    account.get('product_name'),
                    account.get('currency', 'USD'),
                    account.get('country', 'US'),
                    account.get('branch_code'),
                    account.get('branch_name'),
                    account.get('open_date'),
                    account.get('close_date'),
                    account.get('status', 'ACTIVE'),
                    account.get('purpose'),
                    account.get('declared_monthly_turnover'),
                    account.get('declared_source_of_funds'),
                    account.get('is_joint', False)
                ))

                # Insert Ownership
                ownership = account.get('ownership')
                if ownership:
                    cursor.execute("""
                        INSERT INTO AccountOwnership (
                            account_id, customer_id, ownership_type, ownership_pct,
                            signing_authority, daily_limit, is_active
                        ) VALUES (%s, %s, %s::ownership_type_enum, %s, %s::signing_authority_enum, %s, %s)
                        ON CONFLICT (account_id, customer_id) DO NOTHING
                    """, (
                        account_id,
                        account.get('entity_id'),  # Link to customer
                        ownership.get('ownership_type', 'PRIMARY'),
                        ownership.get('ownership_pct', 100.0),
                        ownership.get('signing_authority', 'SOLE'),
                        ownership.get('daily_limit'),
                        ownership.get('is_active', True)
                    ))

                count += 1

            except Exception as e:
                logger.warning(f"Failed to load account: {e}")
                continue

        return count

    def _load_transactions(self, cursor, transactions: List[Dict], scenario_id: str) -> int:
        """Load Transaction records"""
        count = 0

        for txn in transactions:
            try:
                txn_id = txn.get('txn_id') or self._generate_txn_id()

                cursor.execute("""
                    INSERT INTO Transaction (
                        txn_id, txn_ref, timestamp, value_date, posting_date,
                        account_id, direction, amount, currency, amount_usd, exchange_rate,
                        txn_type, channel,
                        counterparty_name_raw, counterparty_account_number, counterparty_bank_code,
                        counterparty_bank_name, counterparty_country,
                        originator_name, originator_country, beneficiary_name, beneficiary_country,
                        end_to_end_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::txn_direction_enum, %s, %s, %s, %s,
                        %s::txn_type_enum, %s::channel_enum, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (txn_id) DO NOTHING
                """, (
                    txn_id,
                    txn.get('txn_ref'),
                    txn.get('timestamp', datetime.now()),
                    txn.get('value_date'),
                    txn.get('posting_date'),
                    txn.get('from_account_id'),
                    txn.get('direction', 'DEBIT'),
                    txn.get('amount'),
                    txn.get('currency', 'USD'),
                    txn.get('amount_usd'),
                    txn.get('exchange_rate', 1.0),
                    txn.get('bank_txn_type', 'WIRE'),
                    txn.get('channel', 'ONLINE'),
                    txn.get('counterparty_name'),
                    txn.get('counterparty_account'),
                    txn.get('counterparty_bank_code'),
                    txn.get('counterparty_bank_name'),
                    txn.get('counterparty_country'),
                    txn.get('originator_name'),
                    txn.get('originator_country'),
                    txn.get('beneficiary_name'),
                    txn.get('beneficiary_country'),
                    txn.get('end_to_end_id')
                ))

                count += 1

            except Exception as e:
                logger.warning(f"Failed to load transaction: {e}")
                continue

        return count

    def _load_relationships(self, cursor, relationships: List[Dict], scenario_id: str) -> int:
        """Load CustomerRelationship records"""
        count = 0

        for rel in relationships:
            try:
                cursor.execute("""
                    INSERT INTO CustomerRelationship (
                        relationship_id, from_customer_id, to_customer_id,
                        relationship_type, effective_from, verified
                    ) VALUES (gen_random_uuid(), %s, %s, %s::relationship_type_enum, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    rel.get('from_customer_id'),
                    rel.get('to_customer_id'),
                    rel.get('relationship_type', 'BENEFICIAL_OWNER'),
                    rel.get('effective_from', date.today()),
                    rel.get('verified', False)
                ))

                count += 1

            except Exception as e:
                logger.warning(f"Failed to load relationship: {e}")
                continue

        return count

    def _generate_customer_id(self) -> str:
        """Generate customer ID"""
        import uuid
        return f"C{datetime.now().strftime('%y%m%d')}{uuid.uuid4().hex[:8].upper()}"

    def _generate_account_id(self) -> str:
        """Generate account ID"""
        import uuid
        return f"ACCT_{uuid.uuid4().hex[:12]}"

    def _generate_txn_id(self) -> str:
        """Generate transaction ID"""
        import uuid
        return f"TXN_{uuid.uuid4().hex[:12]}"
