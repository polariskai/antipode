"""
Comprehensive PostgreSQL loader for bank schema
Populates ALL tables with enriched adversarial agent data
"""

import psycopg2
import os
import logging
from typing import List, Dict, Any
from datetime import date, datetime
from dotenv import load_dotenv
import uuid

from src.antipode.data.loaders.alert_generator import AlertGenerator

load_dotenv()

logger = logging.getLogger(__name__)


class EnrichedBankLoader:
    """Load enriched scenario data into ALL bank schema tables"""

    def __init__(self):
        self.host = os.environ.get('BANK_DB_HOST', '${POSTGRES_HOST:-your-rds-instance.region.rds.amazonaws.com}')
        self.port = int(os.environ.get('BANK_DB_PORT', '5432'))
        self.database = os.environ.get('BANK_DB_NAME', 'postgres')
        self.user = os.environ.get('BANK_DB_USER', 'postgres')
        self.password = os.environ.get('BANK_POSTGRES_PASSWORD')

        if not self.password:
            raise ValueError("BANK_POSTGRES_PASSWORD environment variable not set")

    def load_scenario(self, scenario: Dict[str, Any]) -> Dict[str, int]:
        """Load complete scenario and return counts"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                sslmode='require'
            )
            cursor = conn.cursor()

            scenario_id = scenario.get('scenario_id', 'unknown')
            logger.info(f"Loading enriched scenario {scenario_id}")

            counts = {}

            # 1. Load Customers with full details
            entities = scenario.get('entities', [])
            try:
                cursor.execute("SAVEPOINT sp_customers")
                counts['customers'] = self._load_customers(cursor, entities, scenario_id)
                cursor.execute("RELEASE SAVEPOINT sp_customers")
            except Exception as e:
                logger.warning(f"Failed to load customers: {e}")
                cursor.execute("ROLLBACK TO SAVEPOINT sp_customers")
                counts['customers'] = 0

            try:
                cursor.execute("SAVEPOINT sp_addresses")
                counts['addresses'] = self._load_addresses(cursor, entities, scenario_id)
                cursor.execute("RELEASE SAVEPOINT sp_addresses")
            except Exception as e:
                logger.warning(f"Failed to load addresses: {e}")
                cursor.execute("ROLLBACK TO SAVEPOINT sp_addresses")
                counts['addresses'] = 0

            try:
                cursor.execute("SAVEPOINT sp_identifiers")
                counts['identifiers'] = self._load_identifiers(cursor, entities, scenario_id)
                cursor.execute("RELEASE SAVEPOINT sp_identifiers")
            except Exception as e:
                logger.warning(f"Failed to load identifiers: {e}")
                cursor.execute("ROLLBACK TO SAVEPOINT sp_identifiers")
                counts['identifiers'] = 0

            # 2. Load Accounts with ownership
            accounts = scenario.get('accounts', [])
            try:
                cursor.execute("SAVEPOINT sp_accounts")
                counts['accounts'] = self._load_accounts(cursor, accounts, scenario_id)
                cursor.execute("RELEASE SAVEPOINT sp_accounts")
            except Exception as e:
                logger.warning(f"Failed to load accounts: {e}")
                cursor.execute("ROLLBACK TO SAVEPOINT sp_accounts")
                counts['accounts'] = 0

            try:
                cursor.execute("SAVEPOINT sp_ownerships")
                counts['ownerships'] = self._load_account_ownership(cursor, accounts, scenario_id)
                cursor.execute("RELEASE SAVEPOINT sp_ownerships")
            except Exception as e:
                logger.warning(f"Failed to load ownerships: {e}")
                cursor.execute("ROLLBACK TO SAVEPOINT sp_ownerships")
                counts['ownerships'] = 0

            # 3. Load Transactions with counterparties
            transactions = scenario.get('transactions', [])
            try:
                cursor.execute("SAVEPOINT sp_counterparties")
                counts['counterparties'] = self._load_counterparties(cursor, transactions, scenario_id)
                cursor.execute("RELEASE SAVEPOINT sp_counterparties")
            except Exception as e:
                logger.warning(f"Failed to load counterparties: {e}")
                cursor.execute("ROLLBACK TO SAVEPOINT sp_counterparties")
                counts['counterparties'] = 0

            try:
                cursor.execute("SAVEPOINT sp_transactions")
                counts['transactions'] = self._load_transactions(cursor, transactions, scenario_id)
                cursor.execute("RELEASE SAVEPOINT sp_transactions")
            except Exception as e:
                logger.warning(f"Failed to load transactions: {e}")
                cursor.execute("ROLLBACK TO SAVEPOINT sp_transactions")
                counts['transactions'] = 0

            # 4. Load Relationships
            relationships = scenario.get('relationships', [])
            try:
                cursor.execute("SAVEPOINT sp_relationships")
                counts['relationships'] = self._load_relationships(cursor, relationships, scenario_id)
                cursor.execute("RELEASE SAVEPOINT sp_relationships")
            except Exception as e:
                logger.warning(f"Failed to load relationships: {e}")
                cursor.execute("ROLLBACK TO SAVEPOINT sp_relationships")
                counts['relationships'] = 0

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Loaded scenario {scenario_id}: {counts}")
            return counts

        except Exception as e:
            logger.error(f"Failed to load scenario: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                try:
                    cursor.close()
                    conn.close()
                except:
                    pass

    def _load_customers(self, cursor, entities: List[Dict], scenario_id: str) -> int:
        """Load Customer + CustomerPerson/CustomerCompany with ALL enriched fields"""
        count = 0

        for entity in entities:
            try:
                customer_id = entity.get('customer_id', f"C{datetime.now().strftime('%y%m%d')}{uuid.uuid4().hex[:8].upper()}")
                customer_type = entity.get('customer_type', 'PERSON').upper()

                # Insert Customer base table
                cursor.execute("""
                    INSERT INTO Customer (
                        customer_id, customer_type, onboarding_date, status,
                        risk_rating, segment, relationship_manager_id,
                        kyc_date, next_review_date, source_system
                    ) VALUES (%s, %s::customer_type_enum, %s, %s::customer_status_enum,
                        %s::risk_rating_enum, %s::customer_segment_enum, %s, %s, %s, %s)
                    ON CONFLICT (customer_id) DO NOTHING
                """, (
                    customer_id,
                    customer_type,
                    entity.get('onboarding_date', date.today()),
                    entity.get('status', 'ACTIVE'),
                    entity.get('risk_rating', 'MEDIUM'),
                    entity.get('segment', 'RETAIL'),
                    entity.get('relationship_manager_id'),
                    entity.get('kyc_date', date.today()),
                    entity.get('next_review_date'),
                    'ADVERSARIAL_GENERATOR'
                ))

                # Insert CustomerPerson if individual
                person_details = entity.get('person_details')
                if person_details and customer_type == 'PERSON':
                    first_name = person_details.get('first_name', 'Unknown')
                    last_name = person_details.get('last_name', 'Unknown')
                    full_name = person_details.get('full_name', f"{first_name} {last_name}".strip())

                    cursor.execute("""
                        INSERT INTO CustomerPerson (
                            customer_id, title, first_name, middle_name, last_name, full_name,
                            date_of_birth, nationality, country_of_residence, country_of_birth,
                            gender, occupation, employer, industry, annual_income, source_of_wealth,
                            is_pep, pep_type, pep_status, pep_position, pep_country,
                            tax_residency, fatca_status, crs_status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                 %s, %s::pep_type_enum, %s::pep_status_enum, %s, %s, %s,
                                 %s::fatca_status_enum, %s::crs_status_enum)
                        ON CONFLICT (customer_id) DO NOTHING
                    """, (
                        customer_id,
                        person_details.get('title'),
                        first_name,
                        person_details.get('middle_name'),
                        last_name,
                        full_name,
                        person_details.get('date_of_birth', date(1980, 1, 1)),
                        person_details.get('nationality', entity.get('country', 'US')),
                        person_details.get('country_of_residence', entity.get('country', 'US')),
                        person_details.get('country_of_birth', entity.get('country', 'US')),
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
                        person_details.get('tax_residency', entity.get('country', 'US')),
                        person_details.get('fatca_status', 'US_PERSON'),
                        person_details.get('crs_status', 'NON_REPORTABLE')
                    ))

                # Insert CustomerCompany if company
                company_details = entity.get('company_details')
                if company_details and customer_type == 'COMPANY':
                    cursor.execute("""
                        INSERT INTO CustomerCompany (
                            customer_id, legal_name, trading_name, company_type, legal_form,
                            registration_number, registration_country, registration_date,
                            tax_id, lei, industry_code, industry_description,
                            operational_countries, employee_count, annual_revenue,
                            website, status, is_regulated
                        ) VALUES (%s, %s, %s, %s::company_type_enum, %s, %s, %s, %s, %s, %s,
                                 %s, %s, %s, %s, %s, %s, %s::company_status_enum, %s)
                        ON CONFLICT (customer_id) DO NOTHING
                    """, (
                        customer_id,
                        company_details.get('legal_name', entity.get('name', 'Unknown Corp')),
                        company_details.get('trading_name'),
                        company_details.get('company_type', 'PRIVATE'),
                        company_details.get('legal_form'),
                        company_details.get('registration_number'),
                        company_details.get('registration_country', entity.get('country', 'US')),
                        company_details.get('registration_date'),
                        company_details.get('tax_id'),
                        company_details.get('lei'),
                        company_details.get('industry_code'),
                        company_details.get('industry_description'),
                        company_details.get('operational_countries'),
                        company_details.get('employee_count'),
                        company_details.get('annual_revenue'),
                        company_details.get('website'),
                        company_details.get('status', 'ACTIVE'),
                        company_details.get('is_regulated', False)
                    ))

                count += 1

            except Exception as e:
                logger.warning(f"Failed to load customer {entity.get('customer_id')}: {e}")
                continue

        return count

    def _load_addresses(self, cursor, entities: List[Dict], scenario_id: str) -> int:
        """Load CustomerAddress records"""
        count = 0

        for entity in entities:
            try:
                customer_id = entity.get('customer_id')
                address = entity.get('address')

                if address and customer_id:
                    cursor.execute("""
                        INSERT INTO CustomerAddress (
                            customer_id, address_type, address_line_1, address_line_2,
                            city, state_province, postal_code, country
                        ) VALUES (%s, %s::address_type_enum, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (customer_id, address_type) DO NOTHING
                    """, (
                        customer_id,
                        address.get('address_type', 'RESIDENTIAL'),
                        address.get('line1', address.get('address_line1', '123 Main St')),
                        address.get('line2', address.get('address_line2')),
                        address.get('city', 'New York'),
                        address.get('state_province', address.get('state', 'NY')),
                        address.get('postal_code', address.get('zip_code', '10001')),
                        address.get('country', entity.get('country', 'US'))
                    ))
                    count += 1

            except Exception as e:
                logger.warning(f"Failed to load address: {e}")
                continue

        return count

    def _load_identifiers(self, cursor, entities: List[Dict], scenario_id: str) -> int:
        """Load CustomerIdentifier records"""
        count = 0

        for entity in entities:
            try:
                customer_id = entity.get('customer_id')
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
                        identifier.get('id_type', 'PASSPORT'),
                        identifier.get('id_number'),
                        identifier.get('issuing_country', entity.get('country', 'US')),
                        identifier.get('issue_date'),
                        identifier.get('expiry_date'),
                        identifier.get('is_primary', False),
                        identifier.get('verified', False)
                    ))
                    count += 1

            except Exception as e:
                logger.warning(f"Failed to load identifier: {e}")
                continue

        return count

    def _load_accounts(self, cursor, accounts: List[Dict], scenario_id: str) -> int:
        """Load Account records with ALL enriched fields"""
        count = 0

        for account in accounts:
            try:
                account_id = account.get('account_id', f"ACCT_{uuid.uuid4().hex[:12]}")

                cursor.execute("""
                    INSERT INTO Account (
                        account_id, account_number, product_type, product_name,
                        currency, country, branch_code, branch_name,
                        open_date, close_date, status, purpose,
                        declared_monthly_turnover, declared_source_of_funds,
                        is_joint, is_high_risk, kyc_date, next_review_date,
                        source_system
                    ) VALUES (%s, %s, %s::product_type_enum, %s, %s, %s, %s, %s, %s, %s,
                             %s::account_status_enum, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (account_id) DO NOTHING
                """, (
                    account_id,
                    account.get('account_number', account_id),
                    account.get('product_type', 'CHECKING'),
                    account.get('product_name', 'Personal Checking'),
                    account.get('currency', 'USD'),
                    account.get('country', 'US'),
                    account.get('branch_code'),
                    account.get('branch_name'),
                    account.get('open_date', date.today()),
                    account.get('close_date'),
                    account.get('status', 'ACTIVE'),
                    account.get('purpose'),
                    account.get('declared_monthly_turnover'),
                    account.get('declared_source_of_funds'),
                    account.get('is_joint', False),
                    account.get('is_high_risk', False),
                    account.get('kyc_date', date.today()),
                    account.get('next_review_date'),
                    'ADVERSARIAL_GENERATOR'
                ))

                count += 1

            except Exception as e:
                logger.warning(f"Failed to load account {account.get('account_id')}: {e}")
                continue

        return count

    def _load_account_ownership(self, cursor, accounts: List[Dict], scenario_id: str) -> int:
        """Load AccountOwnership records"""
        count = 0

        for account in accounts:
            try:
                account_id = account.get('account_id')
                # Use customer_id from account dict, fallback to entity_id if needed
                customer_id = account.get('customer_id') or account.get('entity_id')
                ownership = account.get('ownership', {})

                if account_id and customer_id:
                    ownership_id = f"OWN_{uuid.uuid4().hex[:12]}"

                    cursor.execute("""
                        INSERT INTO AccountOwnership (
                            ownership_id, account_id, customer_id, ownership_type,
                            ownership_percentage, signing_authority, daily_limit,
                            effective_from, effective_to, is_active
                        ) VALUES (%s, %s, %s, %s::ownership_type_enum, %s,
                                 %s::signing_authority_enum, %s, %s, %s, %s)
                        ON CONFLICT (ownership_id) DO NOTHING
                    """, (
                        ownership_id,
                        account_id,
                        customer_id,
                        ownership.get('ownership_type', 'PRIMARY'),
                        ownership.get('ownership_pct', ownership.get('ownership_percentage', 100.0)),
                        ownership.get('signing_authority', 'SOLE'),
                        ownership.get('daily_limit'),
                        ownership.get('effective_from', date.today()),
                        ownership.get('effective_to'),
                        ownership.get('is_active', True)
                    ))
                    count += 1

            except Exception as e:
                logger.warning(f"Failed to load ownership: {e}")
                continue

        return count

    def _load_counterparties(self, cursor, transactions: List[Dict], scenario_id: str) -> int:
        """Extract and load unique Counterparty records from transactions"""
        count = 0
        seen_counterparties = set()

        for txn in transactions:
            try:
                # Extract counterparty info from transaction
                cp_name = txn.get('counterparty_name', txn.get('counterparty_name_raw'))
                cp_account = txn.get('counterparty_account', txn.get('counterparty_account_number'))
                cp_bank_code = txn.get('counterparty_bank_code')
                cp_country = txn.get('counterparty_country')

                if cp_name and cp_name not in seen_counterparties:
                    counterparty_id = f"CP_{uuid.uuid4().hex[:12]}"

                    cursor.execute("""
                        INSERT INTO Counterparty (
                            counterparty_id, name, type, account_number,
                            bank_code, bank_name, country, first_seen_date,
                            source_system
                        ) VALUES (%s, %s, %s::counterparty_type_enum, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        counterparty_id,
                        cp_name,
                        'UNKNOWN',  # Can be enhanced based on context
                        cp_account,
                        cp_bank_code,
                        txn.get('counterparty_bank_name'),
                        cp_country,
                        date.today(),
                        'ADVERSARIAL_GENERATOR'
                    ))

                    seen_counterparties.add(cp_name)
                    count += 1

            except Exception as e:
                logger.warning(f"Failed to load counterparty: {e}")
                continue

        return count

    def _load_transactions(self, cursor, transactions: List[Dict], scenario_id: str) -> int:
        """Load Transaction records with ALL enriched fields"""
        count = 0

        for txn in transactions:
            try:
                txn_id = txn.get('txn_id', f"TXN_{uuid.uuid4().hex[:12]}")

                cursor.execute("""
                    INSERT INTO Transaction (
                        txn_id, txn_ref, timestamp, value_date, posting_date,
                        account_id, direction, amount, currency, amount_usd, exchange_rate,
                        txn_type, channel,
                        counterparty_account_number, counterparty_name_raw,
                        counterparty_bank_code, counterparty_bank_name, counterparty_country,
                        originator_name, originator_address, originator_account, originator_country,
                        beneficiary_name, beneficiary_address, beneficiary_account, beneficiary_country,
                        purpose_code, purpose_description, reference, end_to_end_id,
                        source_system, _is_suspicious, _typology, _scenario_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::txn_direction_enum, %s, %s, %s, %s,
                             %s::txn_type_enum, %s::txn_channel_enum,
                             %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                             %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (txn_id) DO NOTHING
                """, (
                    txn_id,
                    txn.get('txn_ref'),
                    txn.get('timestamp', datetime.now()),
                    txn.get('value_date', date.today()),
                    txn.get('posting_date', date.today()),
                    txn.get('from_account_id', txn.get('account_id')),
                    txn.get('direction', 'DEBIT'),
                    txn.get('amount'),
                    txn.get('currency', 'USD'),
                    txn.get('amount_usd', txn.get('amount')),
                    txn.get('exchange_rate', 1.0),
                    txn.get('bank_txn_type', txn.get('txn_type', 'WIRE')),
                    txn.get('channel', 'ONLINE'),
                    txn.get('counterparty_account', txn.get('counterparty_account_number')),
                    txn.get('counterparty_name', txn.get('counterparty_name_raw')),
                    txn.get('counterparty_bank_code'),
                    txn.get('counterparty_bank_name'),
                    txn.get('counterparty_country'),
                    txn.get('originator_name'),
                    txn.get('originator_address'),
                    txn.get('originator_account'),
                    txn.get('originator_country'),
                    txn.get('beneficiary_name'),
                    txn.get('beneficiary_address'),
                    txn.get('beneficiary_account'),
                    txn.get('beneficiary_country'),
                    txn.get('purpose_code'),
                    txn.get('purpose_description'),
                    txn.get('reference'),
                    txn.get('end_to_end_id'),
                    'ADVERSARIAL_GENERATOR',
                    txn.get('_ground_truth', {}).get('is_suspicious', txn.get('is_suspicious')),
                    txn.get('_ground_truth', {}).get('typology', txn.get('typology')),
                    scenario_id
                ))

                count += 1

            except Exception as e:
                logger.warning(f"Failed to load transaction {txn.get('txn_id')}: {e}")
                continue

        return count

    def _load_relationships(self, cursor, relationships: List[Dict], scenario_id: str) -> int:
        """Load CustomerRelationship records"""
        count = 0

        for rel in relationships:
            try:
                relationship_id = f"REL_{uuid.uuid4().hex[:12]}"

                cursor.execute("""
                    INSERT INTO CustomerRelationship (
                        relationship_id, from_customer_id, to_customer_id,
                        relationship_type, effective_from, effective_to,
                        verified, verification_date, notes
                    ) VALUES (%s, %s, %s, %s::relationship_type_enum, %s, %s, %s, %s, %s)
                    ON CONFLICT (relationship_id) DO NOTHING
                """, (
                    relationship_id,
                    rel.get('from_customer_id', rel.get('from_entity_id')),
                    rel.get('to_customer_id', rel.get('to_entity_id')),
                    rel.get('relationship_type', 'BUSINESS_PARTNER'),
                    rel.get('effective_from', date.today()),
                    rel.get('effective_to'),
                    rel.get('verified', False),
                    rel.get('verification_date'),
                    rel.get('notes')
                ))

                count += 1

            except Exception as e:
                logger.warning(f"Failed to load relationship: {e}")
                continue

        return count

    def _load_alerts(
        self, cursor, alerts: List[Dict],
        alert_transactions: List[Dict], scenario_id: str
    ) -> Dict[str, int]:
        """Load Alert and AlertTransaction records"""
        alert_count = 0
        txn_count = 0

        # Load Alerts
        for alert in alerts:
            try:
                cursor.execute("""
                    INSERT INTO Alert (
                        alert_id, account_id, customer_id, alert_type,
                        risk_level, score, status, assigned_to,
                        created_at, due_date, closed_at, disposition_reason,
                        narrative, sar_filed, sar_filing_date, scenario_id
                    ) VALUES (%s, %s, %s, %s, %s::severity_enum, %s, %s::alert_status_enum,
                             %s, %s, %s, %s, %s::disposition_reason_enum, %s, %s, %s, %s)
                    ON CONFLICT (alert_id) DO NOTHING
                """, (
                    alert.get('alert_id'),
                    alert.get('account_id'),
                    alert.get('customer_id'),
                    alert.get('alert_type'),
                    alert.get('risk_level', 'MEDIUM'),
                    alert.get('score'),
                    alert.get('status', 'NEW'),
                    alert.get('assigned_to'),
                    alert.get('created_at', datetime.now()),
                    alert.get('due_date'),
                    alert.get('closed_at'),
                    alert.get('disposition_reason'),
                    alert.get('narrative'),
                    alert.get('sar_filed', False),
                    alert.get('sar_filing_date'),
                    scenario_id
                ))
                alert_count += 1

            except Exception as e:
                logger.warning(f"Failed to load alert {alert.get('alert_id')}: {e}")
                continue

        # Load AlertTransaction links
        for alert_txn in alert_transactions:
            try:
                cursor.execute("""
                    INSERT INTO AlertTransaction (
                        alert_txn_id, alert_id, txn_id, role, added_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (alert_txn_id) DO NOTHING
                """, (
                    alert_txn.get('alert_txn_id'),
                    alert_txn.get('alert_id'),
                    alert_txn.get('txn_id'),
                    alert_txn.get('role', 'TRIGGER'),
                    alert_txn.get('added_at', datetime.now())
                ))
                txn_count += 1

            except Exception as e:
                logger.warning(f"Failed to load alert-transaction link: {e}")
                continue

        return {'alerts': alert_count, 'alert_transactions': txn_count}

    def load_scenario_alerts(self, scenario: Dict[str, Any]) -> Dict[str, int]:
        """Load alerts from a complete scenario (called after scenario is fully generated)"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                sslmode='require'
            )
            cursor = conn.cursor()

            scenario_id = scenario.get('scenario_id', 'unknown')
            logger.info(f"Loading alerts for scenario {scenario_id}")

            # Generate alerts from complete scenario
            alerts, alert_transactions = AlertGenerator.generate_alerts_from_scenario(scenario)

            logger.info(f"Generated {len(alerts)} alerts and {len(alert_transactions)} alert-transaction links")

            # Load alerts
            alert_counts = self._load_alerts(cursor, alerts, alert_transactions, scenario_id)

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Loaded alerts: {alert_counts}")
            return alert_counts

        except Exception as e:
            logger.error(f"Failed to load scenario alerts: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                try:
                    cursor.close()
                    conn.close()
                except:
                    pass
