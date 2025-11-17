import pandas as pd
from database import SessionLocal
from models import VMMachine

def upload_excel_to_database(excel_file_path):
    """
    Upload Excel data directly to MySQL database
    """
    db = SessionLocal()
    
    try:
        print("Reading Excel file...")
        df = pd.read_excel(excel_file_path)
        
        print(f"Found {len(df)} rows in Excel file")
        print(f"Columns: {df.columns.tolist()}")
        
        # Map Excel columns to database columns
        # Updated to match your actual Excel columns
        column_mapping = {
            'MappingId': 'mapping_process_type',
            'ProcessTransactionId': 'transaction_number',
            'Region': 'region',
            'TowerName': 'tower_name',
            'RPATool': 'rpa_tool',
            'ProcessName': 'process_name',
            'SubProcessName': 'sub_process',
            'OGName': 'og_name',
            'EmailFrom': 'email_from',
            'EmailSubject': 'email_subject',
            'TransactionNo': 'transaction_number',
            'ProcessStatus': 'process_status',
            'In_Queue': 'In_Queue',  # NEW COLUMN MAPPING
            'CaseStatus': 'case_status',
            'CaseReason': 'case_reason',
            'ProcessOwner': 'process_owner',
            'StartTime': 'start_time',
            'EndTime': 'end_time',
            'isChild': 'is_child',
            'TimeTaken': 'time_taken',
            'BotID': 'bot_id',
            'MachineName': 'machine_name',
            'EmailReceivedTime': 'email_received_tat',
            'TAT': 'email_received_tat',
            'CreatedDate': 'created_date'
        }
        
        # Rename columns to match database
        df.rename(columns=column_mapping, inplace=True)
        
        # Get only the columns that exist in the database model
        db_columns = [
            'mapping_process_type', 'region', 'tower_name', 'rpa_tool',
            'process_name', 'sub_process', 'og_name', 'email_from',
            'email_subject', 'transaction_number', 'process_status',
            'In_Queue',  # NEW COLUMN ADDED
            'case_status', 'case_reason', 'process_owner', 'start_time',
            'end_time', 'is_child', 'time_taken', 'bot_id', 'machine_name',
            'email_received_tat', 'created_date'
        ]
        
        # Keep only columns that exist in both dataframe and db_columns list
        available_columns = [col for col in db_columns if col in df.columns]
        df = df[available_columns]
        
        print(f"\nMapped columns: {available_columns}")
        
        print("\nClearing existing data from database...")
        deleted_count = db.query(VMMachine).delete()
        print(f"Deleted {deleted_count} old records")
        
        print("\nInserting new data...")
        records_added = 0
        
        for index, row in df.iterrows():
            # Convert row to dict and handle NaN values
            row_dict = row.to_dict()
            # Replace NaN with None
            row_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
            
            vm_machine = VMMachine(**row_dict)
            db.add(vm_machine)
            records_added += 1
            
            if records_added % 50 == 0:
                print(f"Processed {records_added} records...")
        
        db.commit()
        
        print(f"\n✅ SUCCESS! Uploaded {records_added} records to database")
        
        # Show statistics
        active_count = db.query(VMMachine).filter(
            VMMachine.case_status == 'SUCCESS'
        ).count()
        
        pending_count = db.query(VMMachine).filter(
            VMMachine.case_status == 'EXCEPTION'
        ).count()
        
        unique_active = db.query(VMMachine.machine_name).filter(
            VMMachine.case_status == 'SUCCESS'
        ).distinct().count()
        
        unique_pending = db.query(VMMachine.machine_name).filter(
            VMMachine.case_status == 'EXCEPTION'
        ).distinct().count()
        
        print("\n📊 Database Statistics:")
        print(f"   Total Records: {records_added}")
        print(f"   Active (SUCCESS): {active_count} records, {unique_active} unique VMs")
        print(f"   Pending (EXCEPTION): {pending_count} records, {unique_pending} unique VMs")
        
        # Show sample of VM machines
        print("\n🖥️  Sample VM Machines:")
        sample_vms = db.query(VMMachine.machine_name, VMMachine.case_status).limit(5).all()
        for vm in sample_vms:
            status = "Active" if vm.case_status == "SUCCESS" else "Pending"
            print(f"   - {vm.machine_name}: {status}")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        db.close()

if __name__ == "__main__":
    # Use raw string (r"") to handle backslashes in Windows path
    excel_file = r"C:\Users\DELL\Downloads\Sample_Data.xlsx"
    
    print("="*60)
    print("VM Machine Data Upload Tool")
    print("="*60)
    
    upload_excel_to_database(excel_file)