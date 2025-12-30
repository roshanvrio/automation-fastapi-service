import pandas as pd
from sqlalchemy import create_engine
from app.database.connection import DATABASE_URL

def import_excel_data(excel_path: str):
    """
    Import Excel data into process_transactions table
    
    Args:
        excel_path: Path to the Excel file
    """
    try:
        # Read Excel file
        print(f"\n1. Reading Excel file: {excel_path}")
        df = pd.read_excel(excel_path)
        
        print(f"   ✓ Found {len(df)} rows and {len(df.columns)} columns")
        print(f"   ✓ Columns: {df.columns.tolist()}")
        
        # Create engine for pandas
        engine = create_engine(DATABASE_URL)
        
        # Import to SQL Server - APPEND mode
        print(f"\n2. Importing data to 'process_transactions' table...")
        df.to_sql(
            name="process_transactions",
            con=engine,
            if_exists="append",  # Add to existing table
            index=False          # Don't import DataFrame index
        )
        
        print(f"   ✓ Successfully imported {len(df)} rows!")
        
    except Exception as e:
        print(f"\n✗ Error during import: {e}")

if __name__ == "__main__":
    # Excel file path
    excel_file = "Sample_DB.xlsx"
    
    import_excel_data(excel_file)