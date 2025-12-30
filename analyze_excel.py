import pandas as pd

# Path to Excel file
excel_file = "Sample_DB.xlsx"

# Read Excel file
excel_data = pd.ExcelFile(excel_file)

print("=" * 80)
print("EXCEL FILE ANALYSIS")
print("=" * 80)

# Get all sheet names
print(f"\nNumber of sheets: {len(excel_data.sheet_names)}")
print(f"Sheet names: {excel_data.sheet_names}")
print("\n" + "=" * 80)

# Analyze each sheet
for sheet_name in excel_data.sheet_names:
    print(f"\nSHEET: {sheet_name}")
    print("-" * 80)
    
    # Read the sheet
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    
    print(f"Total rows: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    print(f"\nColumn names and data types:")
    print(df.dtypes)
    
    print(f"\nFirst 5 rows of data:")
    print(df.head())
    
    print(f"\nSample data info:")
    print(df.info())
    
    print("\n" + "=" * 80)