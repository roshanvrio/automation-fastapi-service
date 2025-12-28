from sqlalchemy.orm import Session
from sqlalchemy import case, func
from app.models.models import ProcessTransaction, VMPool
from datetime import datetime, date

def get_metrics(db: Session) -> dict:
    try:
        today = date.today()

        exceptions = db.query(ProcessTransaction).filter(ProcessTransaction.CaseStatus == "EXCEPTION", func.date(ProcessTransaction.CreatedDate) == today).count()

        successful = db.query(ProcessTransaction).filter(ProcessTransaction.CaseStatus == "SUCCESS", func.date(ProcessTransaction.CreatedDate) == today).count()

        total_in_queue = db.query(ProcessTransaction).filter(ProcessTransaction.ProcessStatus == "NEW", func.date(ProcessTransaction.CreatedDate) == today).count()

        errors = db.query(ProcessTransaction).filter(ProcessTransaction.CaseStatus == "ERROR", func.date(ProcessTransaction.CreatedDate) == today).count()

        #avg time(Only completed Transactions)
        completed_transactions = db.query(ProcessTransaction.StartTime, ProcessTransaction.EndTime).filter(ProcessTransaction.EndTime.isnot(None), func.date(ProcessTransaction.CreatedDate) == today).all()

        if completed_transactions:
            total_minutes = 0
            for trans in completed_transactions:
                time_diff = trans.EndTime - trans.StartTime
                minutes = time_diff.total_seconds() / 60
                total_minutes += minutes

            avg_time = int(total_minutes/len(completed_transactions))    
        else:
            avg_time = 0
        
        return {
            "exceptions" : exceptions,
            "successful" : successful,
            "totalInQueue" : total_in_queue,
            "errors" : errors,
            "avgTime" : avg_time
        }
    except Exception as e:
        print(f"Error in get_metrics: {e}")
        return {
            "exceptions" : 0,
            "successful" : 0,
            "totalInQueue" : 0,
            "errors" : 0,
            "avgTime" : 0
        }
    
def get_queue_priority(db: Session):
    try:
        today = date.today()

        results = db.query(
            ProcessTransaction.ProcessName.label("processName"),

            func.max(
                case(
                    (ProcessTransaction.EmailFrom != None, "Email"),
                    else_="Schedule"
                )
            ).label("triggerIndication"),

            func.sum(
                case(
                    (ProcessTransaction.ProcessStatus == "NEW", 1),
                    else_=0
                )
            ).label("inQueueCount"),

            func.count(ProcessTransaction.ProcessTransactionId).label("totalCount"),

            func.max(ProcessTransaction.RPATool).label("rpaTool")
        ).filter(func.date(ProcessTransaction.CreatedDate) == today).group_by(ProcessTransaction.ProcessName).all()

        return [
            {
                "processName": row.processName,
                "triggerIndication": row.triggerIndication,
                "inQueueCount": row.inQueueCount,
                "totalCount": row.totalCount,
                "rpaTool": row.rpaTool
            }
            for row in results
            if row.inQueueCount > 0
        ]
    
    except Exception as e:
        print(f"Error in get_queue_priority: {e}")
        return []
    

def get_active_vms(db: Session) -> list:
    
    try:
        today = date.today()
        
        # Get all ongoing transactions (Active VMs)
        ongoing_transactions = db.query(ProcessTransaction).filter(
            ProcessTransaction.ProcessStatus == "ONGOING",
            ProcessTransaction.MachineName.isnot(None),
            func.date(ProcessTransaction.CreatedDate) == today
        ).all()
        
        active_vms = []
        
        for trans in ongoing_transactions:
            machine_name = trans.MachineName
            process_name = trans.ProcessName
            
            # 1. Trigger Indication
            if trans.StartTime and trans.EmailFrom:
                trigger_indication = "Email"
            else:
                trigger_indication = "Scheduled"
            
            # 2. Completed Transactions for this VM + this Process
            completed_count = db.query(ProcessTransaction).filter(
                ProcessTransaction.MachineName == machine_name,
                ProcessTransaction.ProcessName == process_name,
                ProcessTransaction.ProcessStatus == "COMPLETED",
                func.date(ProcessTransaction.CreatedDate) == today
            ).count()
            
            # 3. Last Run Time (Current Time - Start Time)
            if trans.StartTime:
                current_time = datetime.now()
                time_diff = current_time - trans.StartTime
                total_minutes = time_diff.total_seconds() / 60
                
                # Format as hours if >= 60 minutes, otherwise minutes
                if total_minutes >= 60:
                    hours = total_minutes / 60
                    last_run_time = f"{hours:.1f} Hours"
                else:
                    last_run_time = f"{int(total_minutes)} mins"
            else:
                last_run_time = "0 mins"
            
            # 4. RPA Tool
            rpa_tool = trans.RPATool
            
            # 5. Successful Count (Green dots)
            successful_count = db.query(ProcessTransaction).filter(
                ProcessTransaction.MachineName == machine_name,
                ProcessTransaction.ProcessName == process_name,
                ProcessTransaction.ProcessStatus == "COMPLETED",
                ProcessTransaction.CaseStatus == "SUCCESS",
                func.date(ProcessTransaction.CreatedDate) == today
            ).count()
            
            # 6. Failed Count (Red dots) - Error + Exception
            failed_count = db.query(ProcessTransaction).filter(
                ProcessTransaction.MachineName == machine_name,
                ProcessTransaction.ProcessName == process_name,
                ProcessTransaction.ProcessStatus == "FAILED",
                ProcessTransaction.CaseStatus.in_(["ERROR", "EXCEPTION"]),
                func.date(ProcessTransaction.CreatedDate) == today
            ).count()
            
            # Build VM data
            active_vms.append({
                "machineName": machine_name,
                "processName": process_name,
                "triggerIndication": trigger_indication,
                "completedTransactions": completed_count,
                "lastRunTime": last_run_time,
                "rpaTool": rpa_tool,
                "successfulCount": successful_count,
                "failedCount": failed_count
            })
        
        return active_vms
        
    except Exception as e:
        print(f"Error in get_active_vms: {e}")
        return []
    
def get_idle_vms(db: Session) -> list:
    
    try:
        today = date.today()
        
        # Step 1: Get all VMs from vm_pool table
        all_vms_rows = db.query(VMPool).all()
        
        all_vms = set()  # Use set to avoid duplicates
        
        for row in all_vms_rows:
            # Add Automation Anywhere VMs (if not NULL)
            if row.automation_anywhere_vms:
                all_vms.add(row.automation_anywhere_vms)
            
            # Add UiPath VMs (if not NULL)
            if row.uipath_vms:
                all_vms.add(row.uipath_vms)
        
        # Step 2: Get all active VMs (ONGOING transactions, current date)
        active_transactions = db.query(ProcessTransaction.MachineName).filter(
            ProcessTransaction.ProcessStatus == "ONGOING",
            ProcessTransaction.MachineName.isnot(None),
            func.date(ProcessTransaction.CreatedDate) == today
        ).all()
        
        # Step 3: Extract base VM names (remove .BOT suffix)
        active_vms = set()
        
        for trans in active_transactions:
            machine_name = trans.MachineName
            
            # Remove .BOT suffix if present
            # e.g., "VM1.BOT" -> "VM1"
            if machine_name.endswith(".BOT"):
                base_name = machine_name.replace(".BOT", "")
                active_vms.add(base_name)
            else:
                # If no .BOT suffix, use as is
                active_vms.add(machine_name)
        
        # Step 4: Calculate idle VMs (all VMs - active VMs)
        idle_vms = all_vms - active_vms
        
        # Return as sorted list
        return sorted(list(idle_vms))
        
    except Exception as e:
        print(f"Error in get_idle_vms: {e}")
        return []
    
def get_vm_utilization(db: Session) -> dict:

    try:
        today = date.today()
        current_time = datetime.now()

        all_vm_rows = db.query(VMPool).all()

        all_vms = set()
        for row in all_vm_rows:
            if row.automation_anywhere_vms:
                all_vms.add(row.automation_anywhere_vms)
            if row.uipath_vms:
                all_vms.add(row.uipath_vms)

        vm_utilization_list = []

        for vm_name in all_vms:
             machine_name_with_bot = f"{vm_name}.BOT"

             completed_count = db.query(ProcessTransaction).filter(
                 ProcessTransaction.MachineName == machine_name_with_bot,
                 ProcessTransaction.ProcessStatus == "COMPLETED",
                 func.date(ProcessTransaction.CreatedDate) == today
             ).count()

             total_hours = 0.0

             completed_transactions = db.query(ProcessTransaction.StartTime, ProcessTransaction.EndTime).filter(
                 ProcessTransaction.MachineName == machine_name_with_bot,
                 ProcessTransaction.ProcessStatus == "COMPLETED",
                 ProcessTransaction.StartTime.isnot(None),
                 ProcessTransaction.EndTime.isnot(None),
                 func.date(ProcessTransaction.CreatedDate) == today
             ).all()

             for trans in completed_transactions:
                 time_diff = trans.EndTime - trans.StartTime
                 hours = time_diff.total_seconds() / 3600
                 total_hours += hours
             
             active_transaction = db.query(ProcessTransaction.StartTime).filter(
                 ProcessTransaction.MachineName == machine_name_with_bot,
                 ProcessTransaction.ProcessStatus == "ONGOING",
                 ProcessTransaction.StartTime.isnot(None),
                 func.date(ProcessTransaction.CreatedDate) == today
             ).first()

             if active_transaction:
                 time_diff = current_time - active_transaction.StartTime
                 hours = time_diff.total_seconds() / 3600
                 total_hours += hours

             total_hours = round(total_hours, 1)

             vm_utilization_list.append({
                 "vmName": vm_name,
                 "completedTransactions": completed_count,
                 "utilizationHours": total_hours
             })

        if vm_utilization_list:
            top_performer = max(vm_utilization_list, key = lambda x: x["utilizationHours"])
            top_performer_data = {
                "vmName": top_performer["vmName"],
                "utilizationHours": top_performer["utilizationHours"]
            }

        else:
            top_performer_data = {
                "vmName": "N/A",
                "utilizationHours": 0.0
            }

        vm_utilization_list.sort(key = lambda x: x["utilizationHours"], reverse = True)

        return {
            "vmUtilization": vm_utilization_list,
            "topPerformer": top_performer_data
        }
    
    except Exception as e:
        print(f"Error in get_vm_utilization: {e}")
        return {
            "vmUtilization": [],
            "topPerformer": {
                "vmName": "N/A",
                "utilizationHours": 0.0
            }
        }