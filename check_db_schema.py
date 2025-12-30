import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

DB_SERVER = os.getenv("DB_SERVER")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# Connect to database
conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USERNAME};"
    f"PWD={DB_PASSWORD};"
    f"TrustServerCertificate=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    print("=" * 80)
    print("DATABASE SCHEMA CHECK")
    print("=" * 80)

    # Get column names from process_transactions table
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'process_transactions'
        ORDER BY ORDINAL_POSITION
    """)

    print("\nColumns in 'process_transactions' table:")
    print("-" * 80)

    columns = cursor.fetchall()
    for col in columns:
        print(f"  - {col.COLUMN_NAME:30} | {col.DATA_TYPE:15} | Nullable: {col.IS_NULLABLE}")

    print("\n" + "=" * 80)

    # Get sample data
    cursor.execute("SELECT TOP 1 * FROM process_transactions")
    row = cursor.fetchone()

    if row:
        print("\nSample row (first record):")
        print("-" * 80)
        for i, col in enumerate(cursor.description):
            print(f"  {col[0]}: {row[i]}")

    conn.close()
    print("\n✓ Database connection successful!")

except Exception as e:
    print(f"\n✗ Error: {e}")
