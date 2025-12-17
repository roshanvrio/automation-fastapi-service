# app/import_excel_1.py
# Use this script to APPEND new Excel data to existing excel_data table

import pandas as pd
from app.db import engine

def import_excel_append(path):
    """Import Excel data and APPEND to existing table (keeps previous data)"""

    # Load the Excel file
    df = pd.read_excel(path)

    print("\n=== Excel Columns Detected ===")
    print(df.columns.tolist())
    print(f"Total rows to import: {len(df)}")
    print("================================\n")

    # Import to SQL Server - APPEND mode (keeps existing data)
    df.to_sql(
        name="excel_data",      # table name in SQL Server
        con=engine,
        if_exists="append",     # APPEND to existing table
        index=False
    )

    print(f"Successfully APPENDED {len(df)} rows to 'excel_data' table.")
    print("Previous data has been preserved.")

if __name__ == "__main__":
    # ========================================
    # PUT YOUR NEW EXCEL FILE PATH HERE:
    # ========================================
    file_path = "C:/Users/DELL/Downloads/Idle_VMs.xlsx"

    import_excel_append(file_path)
