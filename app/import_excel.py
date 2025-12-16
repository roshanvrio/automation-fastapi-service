# app/import_excel.py
import pandas as pd
from app.db import engine

def import_excel(path):
    # Load the Excel file as-is
    df = pd.read_excel(path)

    print("\n=== Excel Columns Detected ===")
    print(df.columns.tolist())
    print("================================\n")

    # Import full dataframe to SQL Server (create table automatically)
    df.to_sql(
        name="excel_data",      # table name in SQL Server
        con=engine,
        if_exists="replace",    # replace table each time
        index=False
    )

    print(f"Successfully imported {len(df)} rows into 'excel_data' table.")

if __name__ == "__main__":
    import_excel("C:/Users/DELL/Downloads/Sample_DB.xlsx")
