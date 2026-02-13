"""Test AWS RDS PostgreSQL connection."""

import os
import psycopg2

password = os.getenv("BANK_POSTGRES_PASSWORD", "your_password_here")
host = os.getenv("POSTGRES_HOST", "your-rds-instance.region.rds.amazonaws.com")

conn = None
try:
    conn = psycopg2.connect(
        host=host,
        port=5432,
        database='postgres',
        user='postgres',
        password=password,
        sslmode='require',
    )
    cur = conn.cursor()
    cur.execute('SELECT version();')
    print(cur.fetchone()[0])
    cur.close()
except Exception as e:
    print(f"Database error: {e}")
    raise
finally:
    if conn:
        conn.close()
