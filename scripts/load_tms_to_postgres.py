"""
TMS Data Loader - Load TMS pipeline output to AWS Postgres.

Reads a TMS output directory (produced by TMSAlertGenerator) and loads
all data into the bank schema on PostgreSQL. Follows the SAVEPOINT +
ON CONFLICT DO NOTHING pattern from EnrichedBankLoader.

Usage:
    python scripts/load_tms_to_postgres.py --tms-dir data/tms_alerts_v5/TMS_988c80636706
    python scripts/load_tms_to_postgres.py --tms-dir data/tms_alerts_v5/TMS_988c80636706 --drop-existing
"""

import argparse
import json
import os
import sys
import uuid
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import psycopg2
from dotenv import load_dotenv

# Add project root to path so we can import fp_taxonomy
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.antipode.adversarial.tms.fp_taxonomy import FP_CATEGORIES

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ── Enum mapping helpers ──────────────────────────────────────────────────────

TXN_TYPE_MAP = {
    "wire": "WIRE",
    "ach": "ACH",
    "cash_deposit": "CASH_DEPOSIT",
    "cash_withdrawal": "CASH_WITHDRAWAL",
    "check": "CHECK",
    "card": "CARD",
    "internal_transfer": "INTERNAL_TRANSFER",
    "internal": "INTERNAL_TRANSFER",
    "fx": "FX",
    "securities_trade": "SECURITIES_TRADE",
    "loan_payment": "LOAN_PAYMENT",
    "payroll": "PAYROLL",
    "remittance": "REMITTANCE",
}

PRODUCT_TYPE_MAP = {
    "checking": "CHECKING",
    "savings": "SAVINGS",
    "money_market": "MONEY_MARKET",
    "business_checking": "BUSINESS_CHECKING",
    "business_savings": "BUSINESS_SAVINGS",
    "treasury": "TREASURY",
    "brokerage": "BROKERAGE",
    "loan": "LOAN",
    "credit_card": "CREDIT_CARD",
    "nostro": "NOSTRO",
    "vostro": "VOSTRO",
}

RISK_LEVEL_MAP = {
    "low": "LOW",
    "medium": "MEDIUM",
    "high": "HIGH",
    "critical": "CRITICAL",
}

COMPANY_TYPE_MAP = {
    "public": "PUBLIC",
    "private": "PRIVATE",
    "smb": "SMB",
    "corporate": "CORPORATE",
    "ngo": "NGO",
    "msb": "MSB",
    "shell": "SHELL",
    "spv": "SPV",
}


class TMSPostgresLoader:
    """Load TMS pipeline output into PostgreSQL bank schema."""

    def __init__(self):
        self.host = os.environ.get("POSTGRES_HOST")
        self.port = int(os.environ.get("BANK_DB_PORT", "5432"))
        self.database = os.environ.get("BANK_DB_NAME", "postgres")
        self.user = os.environ.get("BANK_DB_USER", "postgres")
        self.password = os.environ.get("BANK_POSTGRES_PASSWORD")

        if not self.password:
            raise ValueError("BANK_POSTGRES_PASSWORD environment variable not set")
        if not self.host:
            raise ValueError("POSTGRES_HOST environment variable not set")

    def _connect(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            sslmode="require",
        )

    def _read_json(self, path: Path) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ── Main entry ────────────────────────────────────────────────────────────

    def load_tms_dataset(self, tms_dir: str, drop_existing: bool = False) -> Dict[str, int]:
        """Load a complete TMS output directory into Postgres."""
        tms_path = Path(tms_dir)
        if not tms_path.exists():
            raise FileNotFoundError(f"TMS directory not found: {tms_dir}")

        # Read all JSON source files
        logger.info(f"Reading TMS data from {tms_path}")
        customers = self._read_json(tms_path / "bank_data" / "customers.json")
        accounts = self._read_json(tms_path / "bank_data" / "accounts.json")
        transactions = self._read_json(tms_path / "bank_data" / "transactions.json")
        signals = self._read_json(tms_path / "bank_data" / "signals.json")
        relationships = self._read_json(tms_path / "bank_data" / "relationships.json")
        alert_queue = self._read_json(tms_path / "alerts" / "alert_queue.json")
        resolutions = self._read_json(tms_path / "ground_truth" / "alert_resolutions.json")
        summary = self._read_json(tms_path / "ground_truth" / "summary.json")

        dataset_id = summary.get("dataset_id", tms_path.name)

        # Build entity_id -> customer_id mapping
        # TMS data uses entity_id (ENT_xxx) in some places and customer_id (C...) in others
        self._eid_to_cid = {}
        for c in customers:
            eid = c.get("entity_id")
            cid = c.get("customer_id", eid)
            if eid:
                self._eid_to_cid[eid] = cid

        logger.info(
            f"Dataset {dataset_id}: {len(customers)} customers, "
            f"{len(accounts)} accounts, {len(transactions)} transactions, "
            f"{len(alert_queue)} alerts"
        )

        conn = None
        try:
            conn = self._connect()
            cursor = conn.cursor()
            counts = {}

            if drop_existing:
                logger.info("Dropping existing TMS data...")
                cursor.execute("DELETE FROM AlertResolution WHERE tms_dataset_id = %s", (dataset_id,))
                cursor.execute("DELETE FROM Alert WHERE tms_dataset_id = %s", (dataset_id,))
                cursor.execute("DELETE FROM TMSDataset WHERE dataset_id = %s", (dataset_id,))
                conn.commit()

            # Load in dependency order
            load_steps = [
                ("tms_dataset", lambda: self._load_dataset_metadata(cursor, summary)),
                ("customers", lambda: self._load_customers(cursor, customers)),
                ("accounts", lambda: self._load_accounts(cursor, accounts, customers)),
                ("counterparties", lambda: self._load_counterparties(cursor, transactions)),
                ("transactions", lambda: self._load_transactions(cursor, transactions)),
                ("relationships", lambda: self._load_relationships(cursor, relationships)),
                ("signals", lambda: self._load_signals(cursor, signals)),
                ("alerts", lambda: self._load_alerts(cursor, alert_queue, dataset_id)),
                ("alert_transactions", lambda: self._load_alert_transactions(cursor, alert_queue)),
                ("alert_resolutions", lambda: self._load_alert_resolutions(cursor, resolutions, dataset_id)),
                ("fp_reference", lambda: self._load_fp_reference_taxonomy(cursor)),
            ]

            for name, loader_fn in load_steps:
                try:
                    cursor.execute(f"SAVEPOINT sp_{name}")
                    counts[name] = loader_fn()
                    cursor.execute(f"RELEASE SAVEPOINT sp_{name}")
                    logger.info(f"  {name}: {counts[name]} rows")
                except Exception as e:
                    logger.warning(f"  {name}: FAILED - {e}")
                    cursor.execute(f"ROLLBACK TO SAVEPOINT sp_{name}")
                    counts[name] = 0

            conn.commit()
            cursor.close()
            conn.close()

            # Print summary
            print("\n" + "=" * 60)
            print(f"TMS Load Summary — {dataset_id}")
            print("=" * 60)
            total = 0
            for name, count in counts.items():
                print(f"  {name:25s} {count:>8,}")
                total += count
            print(f"  {'TOTAL':25s} {total:>8,}")
            print("=" * 60)

            return counts

        except Exception as e:
            logger.error(f"Failed to load TMS dataset: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    # ── TMSDataset ────────────────────────────────────────────────────────────

    def _load_dataset_metadata(self, cursor, summary: Dict) -> int:
        bank_stats = summary.get("bank_data_stats", {})
        cursor.execute(
            """
            INSERT INTO TMSDataset (
                dataset_id, generated_at, total_alerts, true_positives,
                false_positives, fp_rate, target_fp_rate, entity_count,
                account_count, transaction_count, sar_filings,
                avg_investigation_days, risk_distribution,
                alert_type_distribution, disposition_distribution
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (dataset_id) DO NOTHING
            """,
            (
                summary["dataset_id"],
                summary["generated_at"],
                summary.get("total_alerts"),
                summary.get("true_positives"),
                summary.get("false_positives"),
                summary.get("fp_rate"),
                summary.get("target_fp_rate"),
                bank_stats.get("entities"),
                bank_stats.get("accounts"),
                bank_stats.get("transactions"),
                summary.get("sar_filings"),
                summary.get("avg_investigation_days"),
                json.dumps(summary.get("risk_distribution")),
                json.dumps(summary.get("alert_type_distribution")),
                json.dumps(summary.get("disposition_distribution")),
            ),
        )
        return 1

    # ── Customers ─────────────────────────────────────────────────────────────

    def _load_customers(self, cursor, customers: List[Dict]) -> int:
        count = 0
        for c in customers:
            customer_id = c.get("customer_id", c.get("entity_id"))
            customer_type = c.get("customer_type", "PERSON").upper()

            # Insert Customer base
            cursor.execute(
                """
                INSERT INTO Customer (
                    customer_id, customer_type, onboarding_date, status,
                    risk_rating, segment, relationship_manager_id,
                    kyc_date, next_review_date, source_system
                ) VALUES (%s, %s::customer_type_enum, %s, %s::customer_status_enum,
                    %s::risk_rating_enum, %s::customer_segment_enum, %s, %s, %s, %s)
                ON CONFLICT (customer_id) DO NOTHING
                """,
                (
                    customer_id,
                    customer_type,
                    c.get("onboarding_date", str(date.today())),
                    c.get("status", "ACTIVE"),
                    c.get("risk_rating", "MEDIUM"),
                    c.get("segment", "RETAIL"),
                    c.get("relationship_manager_id"),
                    c.get("kyc_date"),
                    c.get("next_review_date"),
                    c.get("source_system", "TMS_GENERATOR"),
                ),
            )

            # CustomerPerson
            pd = c.get("person_details")
            if pd and customer_type == "PERSON":
                first_name = pd.get("first_name", "Unknown")
                last_name = pd.get("last_name", "Unknown")
                cursor.execute(
                    """
                    INSERT INTO CustomerPerson (
                        customer_id, first_name, middle_name, last_name, full_name,
                        date_of_birth, nationality, country_of_residence, country_of_birth,
                        gender, occupation, employer, industry, annual_income, source_of_wealth,
                        is_pep, pep_type, pep_status, pep_position, pep_country,
                        tax_residency, fatca_status, crs_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                             %s::gender_enum, %s, %s, %s, %s, %s,
                             %s, %s::pep_type_enum, %s::pep_status_enum, %s, %s,
                             %s, %s::fatca_status_enum, %s::crs_status_enum)
                    ON CONFLICT (customer_id) DO NOTHING
                    """,
                    (
                        customer_id,
                        first_name,
                        pd.get("middle_name"),
                        last_name,
                        pd.get("full_name", f"{first_name} {last_name}"),
                        pd.get("date_of_birth"),
                        pd.get("nationality", c.get("country")),
                        pd.get("country_of_residence", c.get("country")),
                        pd.get("country_of_birth", c.get("country")),
                        pd.get("gender"),
                        pd.get("occupation"),
                        pd.get("employer"),
                        pd.get("industry"),
                        pd.get("annual_income"),
                        pd.get("source_of_wealth"),
                        pd.get("is_pep", False),
                        pd.get("pep_type", "NONE"),
                        pd.get("pep_status", "NOT_PEP"),
                        pd.get("pep_position"),
                        pd.get("pep_country"),
                        pd.get("tax_residency"),
                        pd.get("fatca_status", "NON_US"),
                        pd.get("crs_status", "NON_REPORTABLE"),
                    ),
                )

            # CustomerCompany
            cd = c.get("company_details")
            if cd and customer_type == "COMPANY":
                company_type = COMPANY_TYPE_MAP.get(
                    cd.get("company_type", "private").lower(), "PRIVATE"
                )
                cursor.execute(
                    """
                    INSERT INTO CustomerCompany (
                        customer_id, legal_name, trading_name, company_type,
                        legal_form, registration_number, registration_country,
                        registration_date, tax_id, lei, industry_code,
                        industry_description, operational_countries, employee_count,
                        annual_revenue, website, status, is_regulated, regulator,
                        license_number, is_listed, stock_exchange, ticker_symbol
                    ) VALUES (%s, %s, %s, %s::company_type_enum, %s, %s, %s, %s, %s,
                             %s, %s, %s, %s, %s, %s, %s, %s::company_status_enum,
                             %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (customer_id) DO NOTHING
                    """,
                    (
                        customer_id,
                        cd.get("legal_name", c.get("name")),
                        cd.get("trading_name"),
                        company_type,
                        cd.get("legal_form"),
                        cd.get("registration_number"),
                        cd.get("registration_country", c.get("country")),
                        cd.get("registration_date"),
                        cd.get("tax_id"),
                        cd.get("lei"),
                        cd.get("industry_code"),
                        cd.get("industry_description"),
                        json.dumps(cd.get("operational_countries")) if cd.get("operational_countries") else None,
                        cd.get("employee_count"),
                        cd.get("annual_revenue"),
                        cd.get("website"),
                        cd.get("status", "ACTIVE"),
                        cd.get("is_regulated", False),
                        cd.get("regulator"),
                        cd.get("license_number"),
                        cd.get("is_listed", False),
                        cd.get("stock_exchange"),
                        cd.get("ticker_symbol"),
                    ),
                )

            # CustomerAddress
            addr = c.get("address")
            if addr:
                addr_id = uuid.uuid4().hex[:20]
                cursor.execute(
                    """
                    INSERT INTO CustomerAddress (
                        address_id, customer_id, address_type,
                        address_line_1, address_line_2,
                        city, state_province, postal_code, country,
                        is_primary, verified_date, effective_from
                    ) VALUES (%s, %s, %s::address_type_enum, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (address_id) DO NOTHING
                    """,
                    (
                        addr_id,
                        customer_id,
                        addr.get("address_type", "RESIDENTIAL"),
                        addr.get("line1", "Unknown"),
                        addr.get("line2"),
                        addr.get("city", "Unknown"),
                        addr.get("state_province"),
                        addr.get("postal_code"),
                        addr.get("country", c.get("country", "US")),
                        addr.get("is_primary", True),
                        addr.get("verified_date"),
                        c.get("onboarding_date", str(date.today())),
                    ),
                )

            # CustomerIdentifier(s)
            for ident in c.get("identifiers", []):
                ident_id = uuid.uuid4().hex[:20]
                cursor.execute(
                    """
                    INSERT INTO CustomerIdentifier (
                        identifier_id, customer_id, id_type, id_number,
                        issuing_country, issue_date, expiry_date,
                        is_primary, verified, verification_date, verification_method
                    ) VALUES (%s, %s, %s::id_type_enum, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (identifier_id) DO NOTHING
                    """,
                    (
                        ident_id,
                        customer_id,
                        ident.get("id_type", "PASSPORT"),
                        ident.get("id_number"),
                        ident.get("issuing_country", c.get("country", "US")),
                        ident.get("issue_date"),
                        ident.get("expiry_date"),
                        ident.get("is_primary", True),
                        ident.get("verified", False),
                        ident.get("verification_date"),
                        ident.get("verification_method"),
                    ),
                )

            count += 1
        return count

    # ── Accounts ──────────────────────────────────────────────────────────────

    def _load_accounts(self, cursor, accounts: List[Dict], customers: List[Dict]) -> int:
        # Build entity_id -> customer_id lookup
        eid_to_cid = {}
        for c in customers:
            eid_to_cid[c.get("entity_id")] = c.get("customer_id", c.get("entity_id"))

        count = 0
        for a in accounts:
            account_id = a["account_id"]
            entity_id = a.get("entity_id")
            customer_id = eid_to_cid.get(entity_id, entity_id)
            product_type = PRODUCT_TYPE_MAP.get(
                a.get("product_type", a.get("account_type", "checking")).lower(), "CHECKING"
            )

            open_date_raw = a.get("open_date") or a.get("opened_at", str(date.today()))
            open_date_str = str(open_date_raw)[:10]

            cursor.execute(
                """
                INSERT INTO Account (
                    account_id, account_number, product_type, product_name,
                    currency, country, branch_code, branch_name,
                    open_date, close_date, status,
                    purpose, declared_monthly_turnover,
                    declared_source_of_funds, is_joint, is_high_risk,
                    kyc_date, next_review_date, source_system
                ) VALUES (%s, %s, %s::product_type_enum, %s, %s, %s, %s, %s,
                         %s, %s, %s::account_status_enum, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (account_id) DO NOTHING
                """,
                (
                    account_id,
                    a.get("account_number", account_id),
                    product_type,
                    a.get("product_name"),
                    a.get("currency", "USD"),
                    a.get("country", "US"),
                    a.get("branch_code"),
                    a.get("branch_name"),
                    open_date_str,
                    a.get("close_date"),
                    a.get("status", "ACTIVE"),
                    a.get("purpose"),
                    a.get("declared_monthly_turnover"),
                    a.get("declared_source_of_funds"),
                    a.get("is_joint", False),
                    a.get("is_high_risk", False),
                    a.get("kyc_date"),
                    a.get("next_review_date"),
                    a.get("source_system", "TMS_GENERATOR"),
                ),
            )

            # AccountOwnership
            own = a.get("ownership")
            if own:
                ownership_id = uuid.uuid4().hex[:20]
                cursor.execute(
                    """
                    INSERT INTO AccountOwnership (
                        ownership_id, account_id, customer_id, ownership_type,
                        ownership_percentage, signing_authority, daily_limit,
                        effective_from, is_active
                    ) VALUES (%s, %s, %s, %s::ownership_type_enum, %s,
                             %s::signing_authority_enum, %s, %s, %s)
                    ON CONFLICT (ownership_id) DO NOTHING
                    """,
                    (
                        ownership_id,
                        account_id,
                        customer_id,
                        own.get("ownership_type", "PRIMARY"),
                        own.get("ownership_pct", 100.0),
                        own.get("signing_authority", "SOLE"),
                        own.get("daily_limit"),
                        open_date_str,
                        own.get("is_active", True),
                    ),
                )

            count += 1
        return count

    # ── Counterparties ────────────────────────────────────────────────────────

    def _load_counterparties(self, cursor, transactions: List[Dict]) -> int:
        """Extract unique external counterparty IDs from transactions."""
        seen = set()
        count = 0
        for t in transactions:
            for field in ("from_account_id", "to_account_id"):
                cpty_id = t.get(field, "")
                if cpty_id and cpty_id.startswith("EXT_") and cpty_id not in seen:
                    seen.add(cpty_id)
                    cpty_type = t.get("counterparty_type", "UNKNOWN")
                    # Map to enum
                    cpty_type_map = {
                        "person": "PERSON",
                        "company": "COMPANY",
                        "bank": "BANK",
                        "government": "GOVERNMENT",
                        "merchant": "COMPANY",
                    }
                    cpty_enum = cpty_type_map.get(cpty_type.lower(), "UNKNOWN")
                    cursor.execute(
                        """
                        INSERT INTO Counterparty (
                            counterparty_id, name, type, country
                        ) VALUES (%s, %s, %s::counterparty_type_enum, %s)
                        ON CONFLICT (counterparty_id) DO NOTHING
                        """,
                        (cpty_id, cpty_id, cpty_enum, None),
                    )
                    count += 1
        return count

    # ── Transactions ──────────────────────────────────────────────────────────

    def _load_transactions(self, cursor, transactions: List[Dict]) -> int:
        count = 0
        for t in transactions:
            txn_id = t["txn_id"]
            txn_type = TXN_TYPE_MAP.get(t.get("txn_type", "wire").lower(), "WIRE")

            # Determine direction based on whether from is internal
            from_acct = t.get("from_account_id", "")
            to_acct = t.get("to_account_id", "")
            is_from_internal = from_acct.startswith("ACCT_")
            is_to_internal = to_acct.startswith("ACCT_")

            # Use internal account as the account_id
            if is_from_internal:
                account_id = from_acct
                direction = "DEBIT"
                counterparty_id = to_acct if to_acct.startswith("EXT_") else None
            elif is_to_internal:
                account_id = to_acct
                direction = "CREDIT"
                counterparty_id = from_acct if from_acct.startswith("EXT_") else None
            else:
                account_id = from_acct
                direction = "DEBIT"
                counterparty_id = to_acct if to_acct.startswith("EXT_") else None

            ts_raw = t.get("timestamp", str(datetime.now()))
            ts_date = str(ts_raw)[:10]  # Extract date portion for value_date/posting_date

            cursor.execute(
                """
                INSERT INTO Transaction (
                    txn_id, account_id, direction, txn_type, amount, currency,
                    counterparty_id, purpose_description, timestamp,
                    value_date, posting_date, source_system
                ) VALUES (%s, %s, %s::txn_direction_enum, %s::txn_type_enum,
                         %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (txn_id) DO NOTHING
                """,
                (
                    txn_id,
                    account_id,
                    direction,
                    txn_type,
                    t.get("amount", 0),
                    t.get("currency", "USD"),
                    counterparty_id,
                    t.get("purpose"),
                    ts_raw,
                    ts_date,
                    ts_date,
                    "TMS_GENERATOR",
                ),
            )
            count += 1
        return count

    # ── Relationships ─────────────────────────────────────────────────────────

    def _load_relationships(self, cursor, relationships: List[Dict]) -> int:
        count = 0
        for r in relationships:
            rel_id = r.get("relationship_id", uuid.uuid4().hex[:20])
            # Map entity IDs -> customer IDs
            from_id = self._eid_to_cid.get(r.get("from_entity_id"), r.get("from_entity_id"))
            to_id = self._eid_to_cid.get(r.get("to_entity_id"), r.get("to_entity_id"))
            rel_type = r.get("bank_relationship_type", "BUSINESS_PARTNER")

            cursor.execute(
                """
                INSERT INTO CustomerRelationship (
                    relationship_id, from_customer_id, to_customer_id,
                    relationship_type, effective_from,
                    effective_to, verified, verification_date, notes
                ) VALUES (%s, %s, %s, %s::relationship_type_enum, %s, %s, %s, %s, %s)
                ON CONFLICT (relationship_id) DO NOTHING
                """,
                (
                    rel_id,
                    from_id,
                    to_id,
                    rel_type,
                    r.get("effective_from", str(date.today())),
                    r.get("effective_to"),
                    r.get("verified", False),
                    r.get("verification_date"),
                    r.get("notes"),
                ),
            )
            count += 1
        return count

    # ── Signals ───────────────────────────────────────────────────────────────

    def _load_signals(self, cursor, signals: List[Dict]) -> int:
        count = 0
        for s in signals:
            signal_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO AccountSignals (
                    signal_id, account_id, as_of_date,
                    volume_30d, volume_90d, volume_deviation_pct,
                    txn_count_30d, velocity_zscore_7d,
                    cash_intensity, round_amount_ratio,
                    structuring_score, rapid_movement_score,
                    counterparty_count_30d, new_counterparty_rate,
                    counterparty_concentration,
                    corridor_risk_score, high_risk_country_ratio
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (account_id, as_of_date) DO NOTHING
                """,
                (
                    signal_id,
                    s["account_id"],
                    s.get("as_of_date", str(date.today())),
                    s.get("volume_30d"),
                    s.get("volume_90d"),
                    s.get("declared_vs_actual_volume"),
                    int(s.get("velocity_30d", 0)) if s.get("velocity_30d") is not None else None,
                    s.get("volume_zscore"),
                    s.get("cash_intensity"),
                    s.get("round_amount_ratio"),
                    s.get("structuring_score"),
                    s.get("rapid_movement_score"),
                    None,  # counterparty_count_30d not directly in signals
                    s.get("new_counterparty_rate"),
                    s.get("counterparty_concentration"),
                    s.get("corridor_risk_score"),
                    s.get("jurisdiction_risk"),
                ),
            )
            count += 1
        return count

    # ── Alerts ────────────────────────────────────────────────────────────────

    def _load_alerts(self, cursor, alert_queue: List[Dict], dataset_id: str) -> int:
        count = 0
        for a in alert_queue:
            alert_id = a["alert_id"]
            customer_id = None
            account_id = None

            cs = a.get("customer_summary", {})
            if cs:
                customer_id = cs.get("customer_id")
            acs = a.get("account_summary", {})
            if acs:
                account_id = acs.get("account_id")

            risk_level = RISK_LEVEL_MAP.get(
                a.get("risk_level", "medium").lower(), "MEDIUM"
            )

            cursor.execute(
                """
                INSERT INTO Alert (
                    alert_id, account_id, customer_id, alert_type, risk_level,
                    score, status, narrative, scenario_id,
                    rule_id, rule_name, amount_involved,
                    lookback_start, lookback_end, tms_dataset_id
                ) VALUES (%s, %s, %s, %s, %s::severity_enum, %s,
                         'NEW'::alert_status_enum, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (alert_id) DO NOTHING
                """,
                (
                    alert_id,
                    account_id,
                    customer_id,
                    a.get("alert_type"),
                    risk_level,
                    a.get("score"),
                    a.get("narrative"),
                    None,  # scenario_id comes from resolution
                    a.get("rule_id"),
                    a.get("rule_name"),
                    a.get("amount_involved"),
                    a.get("lookback_start"),
                    a.get("lookback_end"),
                    dataset_id,
                ),
            )
            count += 1
        return count

    # ── AlertTransaction ──────────────────────────────────────────────────────

    def _load_alert_transactions(self, cursor, alert_queue: List[Dict]) -> int:
        count = 0
        for a in alert_queue:
            alert_id = a["alert_id"]
            for txn in a.get("triggering_transactions", []):
                txn_id = txn.get("txn_id")
                if not txn_id:
                    continue
                at_id = str(uuid.uuid4())
                cursor.execute(
                    """
                    INSERT INTO AlertTransaction (
                        alert_txn_id, alert_id, txn_id, role
                    ) VALUES (%s, %s, %s, %s)
                    ON CONFLICT (alert_id, txn_id) DO NOTHING
                    """,
                    (at_id, alert_id, txn_id, "TRIGGER"),
                )
                count += 1
        return count

    # ── AlertResolution ───────────────────────────────────────────────────────

    def _load_alert_resolutions(self, cursor, resolutions: List[Dict], dataset_id: str) -> int:
        count = 0
        for r in resolutions:
            resolution_id = str(uuid.uuid4())
            alert_id = r["alert_id"]

            risk_level = RISK_LEVEL_MAP.get(
                r.get("risk_level", "medium").lower(), "MEDIUM"
            )

            cursor.execute(
                """
                INSERT INTO AlertResolution (
                    resolution_id, alert_id, is_true_positive, typology,
                    scenario_id, disposition, final_status,
                    assigned_analyst, investigation_started, investigation_closed,
                    investigation_days, sar_filed, sar_id,
                    investigation_notes, risk_level, score,
                    fp_category, fp_flag_reason, fp_legitimate_explanation,
                    fp_evidence_datasets, fp_investigation_playbook,
                    fp_resolution_criteria, fp_benign_trigger_type,
                    tms_dataset_id
                ) VALUES (%s, %s, %s, %s, %s, %s::tms_disposition_enum,
                         %s::tms_final_status_enum, %s, %s, %s, %s, %s, %s,
                         %s, %s::severity_enum, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (alert_id) DO NOTHING
                """,
                (
                    resolution_id,
                    alert_id,
                    r.get("is_true_positive", False),
                    r.get("typology"),
                    r.get("scenario_id"),
                    r.get("disposition", "FALSE_POSITIVE"),
                    r.get("final_status", "CLOSED_NO_ISSUE"),
                    r.get("assigned_analyst"),
                    r.get("investigation_started"),
                    r.get("investigation_closed"),
                    r.get("investigation_days"),
                    r.get("sar_filed", False),
                    r.get("sar_id"),
                    r.get("investigation_notes"),
                    risk_level,
                    r.get("score"),
                    r.get("fp_category"),
                    r.get("fp_flag_reason"),
                    r.get("fp_legitimate_explanation"),
                    json.dumps(r.get("fp_evidence_datasets")) if r.get("fp_evidence_datasets") else None,
                    json.dumps(r.get("fp_investigation_playbook")) if r.get("fp_investigation_playbook") else None,
                    r.get("fp_resolution_criteria"),
                    r.get("fp_benign_trigger_type"),
                    dataset_id,
                ),
            )

            # Also update the Alert table with ground truth
            cursor.execute(
                """
                UPDATE Alert SET
                    _true_positive = %s,
                    _typology = %s,
                    sar_filed = %s,
                    sar_filing_date = CASE WHEN %s THEN CURRENT_DATE ELSE NULL END,
                    scenario_id = %s
                WHERE alert_id = %s
                """,
                (
                    r.get("is_true_positive", False),
                    r.get("typology"),
                    r.get("sar_filed", False),
                    r.get("sar_filed", False),
                    r.get("scenario_id"),
                    alert_id,
                ),
            )

            count += 1
        return count

    # ── FP Reference Taxonomy ─────────────────────────────────────────────────

    def _load_fp_reference_taxonomy(self, cursor) -> int:
        """Load all 28 FP categories from fp_taxonomy.py into FPCategoryReference."""
        count = 0
        for alert_type, categories in FP_CATEGORIES.items():
            for cat in categories:
                cursor.execute(
                    """
                    INSERT INTO FPCategoryReference (
                        category_id, alert_type, triggering_rule, triggering_signals,
                        flag_reason, legitimate_explanation, applicable_dispositions,
                        benign_trigger_type, evidence_datasets, investigation_steps,
                        resolution_criteria, weight
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (category_id) DO NOTHING
                    """,
                    (
                        cat.category_id,
                        alert_type,
                        cat.triggering_rule,
                        json.dumps(cat.triggering_signals) if cat.triggering_signals else None,
                        cat.flag_reason,
                        cat.legitimate_explanation,
                        json.dumps(cat.applicable_dispositions) if cat.applicable_dispositions else None,
                        cat.benign_trigger_type,
                        json.dumps([ds.value for ds in cat.evidence_datasets]),
                        json.dumps(cat.investigation_playbook),
                        cat.resolution_criteria,
                        cat.weight,
                    ),
                )
                count += 1
        return count


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Load TMS pipeline output into PostgreSQL bank schema"
    )
    parser.add_argument(
        "--tms-dir",
        required=True,
        help="Path to TMS output directory (e.g. data/tms_alerts_v5/TMS_988c80636706)",
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Delete existing data for this dataset_id before loading",
    )
    args = parser.parse_args()

    loader = TMSPostgresLoader()
    loader.load_tms_dataset(args.tms_dir, drop_existing=args.drop_existing)


if __name__ == "__main__":
    main()
