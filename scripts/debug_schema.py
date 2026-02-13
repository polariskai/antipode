#!/usr/bin/env python3
"""Debug schema creation - see what's happening with CREATE TYPE statements."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import psycopg2

# Connection parameters
host = "${POSTGRES_HOST:-your-rds-instance.region.rds.amazonaws.com}"
port = 5432
database = "postgres"
username = "postgres"
password = os.environ.get('BANK_POSTGRES_PASSWORD')

if not password:
    print("[ERROR] BANK_POSTGRES_PASSWORD not set")
    sys.exit(1)

print("Connecting...")
conn = psycopg2.connect(
    host=host, port=port, database=database,
    user=username, password=password, sslmode='require'
)
conn.autocommit = True
cursor = conn.cursor()
print("Connected!\n")

# Step 1: Drop all existing types
print("Step 1: Dropping existing types...")
enum_types = [
    'customer_type_enum', 'customer_status_enum', 'risk_rating_enum',
    'customer_segment_enum', 'gender_enum'
]
for t in enum_types:
    try:
        cursor.execute(f"DROP TYPE IF EXISTS {t} CASCADE")
        print(f"  Dropped {t}")
    except Exception as e:
        print(f"  Error dropping {t}: {e}")

# Step 2: Try creating a single type directly
print("\nStep 2: Creating customer_type_enum directly...")
try:
    cursor.execute("CREATE TYPE customer_type_enum AS ENUM ('PERSON', 'COMPANY')")
    print("  [OK] Created customer_type_enum")
except Exception as e:
    print(f"  [ERROR] {e}")

# Step 3: Verify type exists
print("\nStep 3: Verifying type exists...")
cursor.execute("""
    SELECT typname FROM pg_type WHERE typname = 'customer_type_enum'
""")
result = cursor.fetchone()
if result:
    print(f"  [OK] Type verified: {result[0]}")
else:
    print("  [ERROR] Type not found!")

# Step 4: Create the other needed types
print("\nStep 4: Creating other required types...")
types_to_create = [
    ("customer_status_enum", "('ACTIVE', 'DORMANT', 'CLOSED', 'BLOCKED')"),
    ("risk_rating_enum", "('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')"),
    ("customer_segment_enum", "('RETAIL', 'HNW', 'SMB', 'CORPORATE', 'CORRESPONDENT', 'PEP')"),
]
for type_name, values in types_to_create:
    try:
        cursor.execute(f"CREATE TYPE {type_name} AS ENUM {values}")
        print(f"  [OK] Created {type_name}")
    except Exception as e:
        print(f"  [ERROR] {type_name}: {e}")

# Step 5: Create Customer table
print("\nStep 5: Creating Customer table...")
try:
    cursor.execute("DROP TABLE IF EXISTS Customer CASCADE")
    cursor.execute("""
        CREATE TABLE Customer (
            customer_id VARCHAR(20) PRIMARY KEY,
            customer_type customer_type_enum NOT NULL,
            onboarding_date DATE NOT NULL,
            status customer_status_enum NOT NULL DEFAULT 'ACTIVE',
            risk_rating risk_rating_enum NOT NULL DEFAULT 'MEDIUM',
            segment customer_segment_enum NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  [OK] Customer table created!")
except Exception as e:
    print(f"  [ERROR] {e}")

# Step 6: List all types
print("\nStep 6: Listing all enum types...")
cursor.execute("""
    SELECT typname FROM pg_type WHERE typtype = 'e' ORDER BY typname
""")
types = cursor.fetchall()
print(f"  Found {len(types)} enum types:")
for t in types:
    print(f"    - {t[0]}")

# Step 7: List all tables
print("\nStep 7: Listing all tables...")
cursor.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name
""")
tables = cursor.fetchall()
print(f"  Found {len(tables)} tables:")
for t in tables:
    print(f"    - {t[0]}")

cursor.close()
conn.close()
print("\nDone!")
