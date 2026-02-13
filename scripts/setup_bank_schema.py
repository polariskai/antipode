#!/usr/bin/env python3
"""
Setup Bank Schema on AWS RDS PostgreSQL

Executes the bank_schema.sql file using psycopg2 directly for proper
handling of PostgreSQL-specific syntax (ENUMs, triggers, functions).
"""

import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def setup_schema():
    """Execute the bank schema SQL file."""
    import psycopg2

    # Connection parameters
    host = "${POSTGRES_HOST:-your-rds-instance.region.rds.amazonaws.com}"
    port = 5432
    database = "postgres"
    username = "postgres"
    password = os.environ.get('BANK_POSTGRES_PASSWORD')

    if not password:
        print("[ERROR] BANK_POSTGRES_PASSWORD environment variable not set")
        print("Set it with: set BANK_POSTGRES_PASSWORD=your_password")
        sys.exit(1)

    # Schema file path
    schema_path = Path(__file__).parent.parent / "sql" / "bank_schema.sql"

    if not schema_path.exists():
        print(f"[ERROR] Schema file not found: {schema_path}")
        sys.exit(1)

    print("=" * 60)
    print("Setting up Bank Schema on AWS RDS PostgreSQL")
    print("=" * 60)
    print(f"\nHost: {host}")
    print(f"Database: {database}")
    print(f"Schema file: {schema_path}")

    try:
        # Connect to database
        print("\nConnecting to database...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            sslmode='require'
        )
        conn.autocommit = True
        cursor = conn.cursor()

        print("[SUCCESS] Connected!\n")

        # First, drop all existing objects to start fresh
        print("Step 1: Dropping existing objects...")
        print("-" * 40)

        # Drop tables first (in dependency order)
        tables_to_drop = [
            'CorridorAnalysis', 'CounterpartyProfile', 'NetworkMetrics',
            'CustomerRiskProfile', 'TransactionAggregation', 'AccountSignals',
            'Alert', 'NewsEvent', 'CustomerRelationship', 'Transaction',
            'Counterparty', 'AccountOwnership', 'Account', 'CustomerIdentifier',
            'CustomerAddress', 'CompanyOfficer', 'CustomerCompany', 'CustomerPerson', 'Customer'
        ]

        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            except:
                pass

        # Drop views
        views_to_drop = ['vw_customer_complete', 'vw_account_with_owner', 'vw_transaction_enriched']
        for view in views_to_drop:
            try:
                cursor.execute(f"DROP VIEW IF EXISTS {view} CASCADE")
            except:
                pass

        # Drop enum types
        enum_types = [
            'customer_type_enum', 'customer_status_enum', 'risk_rating_enum',
            'customer_segment_enum', 'gender_enum', 'pep_type_enum', 'pep_status_enum',
            'fatca_status_enum', 'crs_status_enum', 'company_type_enum', 'company_status_enum',
            'officer_role_enum', 'address_type_enum', 'id_type_enum', 'product_type_enum',
            'account_status_enum', 'ownership_type_enum', 'signing_authority_enum',
            'txn_direction_enum', 'txn_type_enum', 'txn_channel_enum', 'counterparty_type_enum',
            'relationship_type_enum', 'news_category_enum', 'severity_enum',
            'source_credibility_enum', 'news_status_enum', 'alert_status_enum',
            'disposition_reason_enum', 'period_type_enum', 'entity_type_enum'
        ]

        for enum_type in enum_types:
            try:
                cursor.execute(f"DROP TYPE IF EXISTS {enum_type} CASCADE")
            except:
                pass

        print(f"  Dropped existing objects")

        # Read schema file
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        # Parse statements
        print("\nStep 2: Executing schema...")
        print("-" * 40)

        statements = parse_sql_statements(schema_sql)

        success_count = 0
        skip_count = 0
        error_count = 0
        tables_created = []
        types_created = []

        for i, stmt in enumerate(statements, 1):
            stmt = stmt.strip()
            if not stmt:
                continue

            # Skip DROP statements (we already did this)
            if stmt.upper().startswith('DROP '):
                skip_count += 1
                continue

            try:
                cursor.execute(stmt)
                success_count += 1

                # Track what was created
                upper_stmt = stmt.upper()
                if 'CREATE TABLE' in upper_stmt:
                    table_name = extract_table_name(stmt)
                    tables_created.append(table_name)
                    print(f"  [OK] Created table: {table_name}")
                elif 'CREATE TYPE' in upper_stmt:
                    type_name = extract_type_name(stmt)
                    types_created.append(type_name)
                elif 'CREATE OR REPLACE FUNCTION' in upper_stmt:
                    print(f"  [OK] Created function")
                elif 'CREATE TRIGGER' in upper_stmt:
                    print(f"  [OK] Created trigger")
                elif 'CREATE VIEW' in upper_stmt or 'CREATE OR REPLACE VIEW' in upper_stmt:
                    view_name = extract_view_name(stmt)
                    print(f"  [OK] Created view: {view_name}")

            except psycopg2.errors.DuplicateObject:
                skip_count += 1
            except psycopg2.errors.DuplicateTable:
                skip_count += 1
            except psycopg2.errors.UndefinedObject:
                skip_count += 1
            except psycopg2.errors.UndefinedTable:
                skip_count += 1
            except Exception as e:
                error_msg = str(e).split('\n')[0]
                if 'already exists' in error_msg.lower():
                    skip_count += 1
                elif 'does not exist' in error_msg.lower():
                    skip_count += 1
                else:
                    error_count += 1
                    print(f"  [ERROR] {error_msg[:100]}")

        print("-" * 40)
        print(f"\nResults:")
        print(f"  Types created: {len(types_created)}")
        print(f"  Tables created: {len(tables_created)}")
        print(f"  Total successful: {success_count}")
        print(f"  Skipped: {skip_count}")
        print(f"  Errors: {error_count}")

        # Verify tables were created
        print("\n" + "=" * 60)
        print("Verification")
        print("=" * 60)

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        tables = cursor.fetchall()
        print(f"\nTables ({len(tables)}):")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM \"{table[0]}\"")
            count = cursor.fetchone()[0]
            print(f"  - {table[0]} ({count} rows)")

        # List custom types
        cursor.execute("""
            SELECT typname FROM pg_type WHERE typtype = 'e' ORDER BY typname
        """)

        types = cursor.fetchall()
        print(f"\nEnum types ({len(types)}):")
        for t in types[:10]:
            print(f"  - {t[0]}")
        if len(types) > 10:
            print(f"  ... and {len(types) - 10} more")

        # List views
        cursor.execute("""
            SELECT table_name FROM information_schema.views
            WHERE table_schema = 'public' ORDER BY table_name
        """)

        views = cursor.fetchall()
        if views:
            print(f"\nViews ({len(views)}):")
            for v in views:
                print(f"  - {v[0]}")

        cursor.close()
        conn.close()

        if len(tables) >= 15:
            print("\n" + "=" * 60)
            print("[SUCCESS] Bank schema setup complete!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("[WARNING] Some tables may not have been created")
            print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def parse_sql_statements(sql_text):
    """
    Parse SQL text into individual statements.
    Handles PostgreSQL-specific syntax like functions with $$ delimiters.

    FIXED: Don't accumulate empty lines or comments between statements.
    """
    statements = []
    current = []
    in_dollar_quote = False
    in_statement = False  # Track if we're inside a SQL statement

    lines = sql_text.split('\n')

    for line in lines:
        stripped = line.strip()

        # Track $$ quoted blocks (functions, triggers)
        if '$$' in line:
            count = line.count('$$')
            if count % 2 == 1:
                in_dollar_quote = not in_dollar_quote

        # If we're in a $$ block, always add the line
        if in_dollar_quote:
            current.append(line)
            in_statement = True
            continue

        # Skip empty lines and comments when NOT inside a statement
        if not in_statement:
            if not stripped or stripped.startswith('--'):
                continue

        # If line is empty or comment and we ARE in a statement,
        # only add if it's part of a multi-line comment inside the statement
        if in_statement and (not stripped or stripped.startswith('--')):
            # Don't add standalone comments/empty lines to the statement
            # unless it's truly mid-statement (rare case)
            if stripped.startswith('--'):
                continue  # Skip comment lines even in statements
            # Empty line - could be formatting, skip it
            continue

        # This is actual SQL content
        current.append(line)
        in_statement = True

        # Statement ends with ;
        if stripped.endswith(';'):
            stmt = '\n'.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            in_statement = False

    # Handle any remaining statement
    if current:
        stmt = '\n'.join(current).strip()
        if stmt:
            statements.append(stmt)

    return statements


def extract_table_name(stmt):
    """Extract table name from CREATE TABLE statement."""
    import re
    match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', stmt, re.IGNORECASE)
    return match.group(1) if match else 'unknown'


def extract_type_name(stmt):
    """Extract type name from CREATE TYPE statement."""
    import re
    match = re.search(r'CREATE\s+TYPE\s+(\w+)', stmt, re.IGNORECASE)
    return match.group(1) if match else 'unknown'


def extract_view_name(stmt):
    """Extract view name from CREATE VIEW statement."""
    import re
    match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)', stmt, re.IGNORECASE)
    return match.group(1) if match else 'unknown'


if __name__ == "__main__":
    setup_schema()
