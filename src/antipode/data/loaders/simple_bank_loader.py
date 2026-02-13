"""
Simple, robust PostgreSQL loader for bank schema
Uses direct inserts without complex transaction handling
"""

import psycopg2
import os
import logging
from typing import List, Dict, Any
from datetime import date, datetime
from dotenv import load_dotenv
import uuid

load_dotenv()

logger = logging.getLogger(__name__)


class SimpleBankLoader:
    """Simple direct loader for bank schema"""

    def __init__(self):
        self.host = os.environ.get('BANK_DB_HOST', '${POSTGRES_HOST:-your-rds-instance.region.rds.amazonaws.com}')
        self.port = int(os.environ.get('BANK_DB_PORT', '5432'))
        self.database = os.environ.get('BANK_DB_NAME', 'postgres')
        self.user = os.environ.get('BANK_DB_USER', 'postgres')
        self.password = os.environ.get('BANK_POSTGRES_PASSWORD')

        if not self.password:
            raise ValueError("BANK_POSTGRES_PASSWORD environment variable not set")

    def load_scenario(self, scenario: Dict[str, Any]) -> int:
        """Load scenario and return total records loaded"""
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
            logger.info(f"Loading scenario {scenario_id}")

            total = 0

            # Load customers
            for entity in scenario.get('entities', []):
                try:
                    self._insert_customer(cursor, entity, scenario_id)
                    total += 1
                except Exception as e:
                    logger.warning(f"Customer error: {e}")

            # Load accounts
            for account in scenario.get('accounts', []):
                try:
                    self._insert_account(cursor, account, scenario_id)
                    total += 1
                except Exception as e:
                    logger.warning(f"Account error: {e}")

            # Load transactions
            for txn in scenario.get('transactions', []):
                try:
                    self._insert_transaction(cursor, txn, scenario_id)
                    total += 1
                except Exception as e:
                    logger.warning(f"Transaction error: {e}")

            conn.commit()
            logger.info(f"Loaded {total} records")
            return total

        except Exception as e:
            logger.error(f"Load failed: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()

    def _insert_customer(self, cursor, entity: Dict, scenario_id: str):
        """Insert customer with minimal required fields"""
        customer_id = entity.get('customer_id', f"C{uuid.uuid4().hex[:12].upper()}")
        customer_type = entity.get('customer_type', 'PERSON').upper()
        onboarding_date = entity.get('onboarding_date', date.today())
        risk_rating = entity.get('risk_rating', 'MEDIUM').upper()
        segment = entity.get('segment', 'RETAIL').upper()

        # Insert into Customer table
        cursor.execute("""
            INSERT INTO Customer (
                customer_id, customer_type, onboarding_date, status, risk_rating, segment, source_system
            ) VALUES (%s, %s::customer_type_enum, %s, 'ACTIVE'::customer_status_enum,
                %s::risk_rating_enum, %s::customer_segment_enum, 'ADVERSARIAL_GENERATOR')
            ON CONFLICT (customer_id) DO NOTHING
        """, (customer_id, customer_type, onboarding_date, risk_rating, segment))

        # Insert person details if individual
        person_details = entity.get('person_details')
        if person_details and customer_type == 'PERSON':
            first_name = person_details.get('first_name', 'Unknown')
            last_name = person_details.get('last_name', 'Unknown')
            full_name = f"{first_name} {last_name}".strip()

            cursor.execute("""
                INSERT INTO CustomerPerson (
                    customer_id, first_name, last_name, full_name,
                    date_of_birth, nationality, country_of_residence
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (customer_id) DO NOTHING
            """, (
                customer_id, first_name, last_name, full_name,
                person_details.get('date_of_birth'),
                person_details.get('nationality', 'US'),
                person_details.get('country_of_residence', entity.get('country', 'US'))
            ))

    def _insert_account(self, cursor, account: Dict, scenario_id: str):
        """Insert account with minimal required fields"""
        account_id = account.get('account_id', f"ACCT_{uuid.uuid4().hex[:12]}")

        cursor.execute("""
            INSERT INTO Account (
                account_id, account_number, product_type, currency, country,
                open_date, status
            ) VALUES (%s, %s, %s::product_type_enum, %s, %s, %s, 'ACTIVE'::account_status_enum)
            ON CONFLICT (account_id) DO NOTHING
        """, (
            account_id,
            account.get('account_number'),
            account.get('product_type', 'CHECKING'),
            account.get('currency', 'USD'),
            account.get('country', 'US'),
            account.get('open_date', date.today())
        ))

    def _insert_transaction(self, cursor, txn: Dict, scenario_id: str):
        """Insert transaction with minimal required fields"""
        txn_id = txn.get('txn_id', f"TXN_{uuid.uuid4().hex[:12]}")

        cursor.execute("""
            INSERT INTO Transaction (
                txn_id, timestamp, account_id, amount, currency, amount_usd,
                direction, txn_type, channel, value_date, posting_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s::txn_direction_enum,
                %s::txn_type_enum, %s::txn_channel_enum, %s, %s)
            ON CONFLICT (txn_id) DO NOTHING
        """, (
            txn_id,
            txn.get('timestamp', datetime.now()),
            txn.get('from_account_id'),
            txn.get('amount'),
            txn.get('currency', 'USD'),
            txn.get('amount_usd', txn.get('amount')),
            txn.get('direction', 'DEBIT'),
            txn.get('bank_txn_type', 'WIRE'),
            txn.get('channel', 'ONLINE'),
            txn.get('value_date', date.today()),
            txn.get('posting_date', date.today())
        ))
