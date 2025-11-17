from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import SessionLocal
from models import VMMachine
from schemas import VMMachineResponse, VMStatusResponse, ProcessStatusResponse, VMStatusDetailResponse
from typing import List, Optional
import re
from datetime import datetime, date
from sqlalchemy import func

app = FastAPI(title="VM Machine Status API")

# Enable CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home():
    """Serve the dashboard HTML file"""
    return FileResponse("index.html")


def extract_vm_number(machine_name: str) -> int:
    """Extract VM number from machine name like 'VM17.BOT' -> 17"""
    if not machine_name:
        return 0
    match = re.search(r'VM(\d+)', machine_name, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def is_today(date_string: str) -> bool:
    """Check if a date string is from today"""
    if not date_string:
        return False
    try:
        # Try different date formats
        for fmt in ['%H:%M.%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d:%M.%S']:
            try:
                record_date = datetime.strptime(date_string, fmt).date()
                return record_date == date.today()
            except:
                continue

        # If time only format (like "05:53.4"), assume it's from today
        if ':' in date_string and '.' in date_string:
            return True

        return False
    except:
        return False


@app.get("/vm-status")
def get_vm_by_status(
    status: Optional[str] = Query(None, description="Filter by status: 'active' (SUCCESS), 'pending' (EXCEPTION), or leave empty for all"),
    db: Session = Depends(get_db)
):
    """
    Get VM machines by CaseStatus with latest date filtering
    Returns VM status in format expected by frontend (VM_01, VM_02, etc.)
    """
    status_mapping = {
        'active': 'SUCCESS',
        'pending': 'EXCEPTION'
    }
    
    # Get all VMs with their latest entries
    # Subquery to get the latest created_date for each machine
    latest_dates = db.query(
        VMMachine.machine_name,
        func.max(VMMachine.created_date).label('latest_date')
    ).group_by(VMMachine.machine_name).subquery()
    
    # Join to get only the latest records
    latest_vms = db.query(VMMachine).join(
        latest_dates,
        (VMMachine.machine_name == latest_dates.c.machine_name) &
        (VMMachine.created_date == latest_dates.c.latest_date)
    ).filter(
        VMMachine.case_status.in_(['SUCCESS', 'EXCEPTION'])
    ).all()
    
    # Process VMs and format for frontend
    vm_status_dict = {}
    vm_bot_mapping = {}  # Store bot_id for each VM
    
    for vm in latest_vms:
        if not vm.machine_name:
            continue
            
        vm_number = extract_vm_number(vm.machine_name)
        if vm_number == 0:
            continue
        
        # Format as VM_01, VM_02, etc.
        formatted_name = f"VM_{str(vm_number).zfill(2)}"
        
        # Determine status
        vm_status = "active" if vm.case_status == "SUCCESS" else "pending"
        
        # Store bot_id for this VM
        vm_bot_mapping[formatted_name] = vm.bot_id or "Unknown Bot"
        
        # If VM already exists, prioritize 'pending' over 'active'
        if formatted_name in vm_status_dict:
            if vm_status == "pending":
                vm_status_dict[formatted_name] = vm_status
                vm_bot_mapping[formatted_name] = vm.bot_id or "Unknown Bot"
        else:
            vm_status_dict[formatted_name] = vm_status
    
    # If specific status requested, filter
    if status and status.lower() in status_mapping:
        requested_status = status.lower()
        vm_status_dict = {
            vm: st for vm, st in vm_status_dict.items() 
            if st == requested_status
        }
    
    # Convert to list format with bot_id included
    machines_with_status = [
        {
            "machine_name": vm, 
            "status": st,
            "bot_id": vm_bot_mapping.get(vm, "Unknown Bot")
        }
        for vm, st in sorted(vm_status_dict.items())
    ]
    
    # Count active and pending
    active_count = sum(1 for m in machines_with_status if m["status"] == "active")
    pending_count = sum(1 for m in machines_with_status if m["status"] == "pending")
    
    return {
        "status": status.lower() if status else "all",
        "total_count": len(machines_with_status),
        "active_count": active_count,
        "pending_count": pending_count,
        "machines": machines_with_status
    }


@app.get("/process-statistics/")
def get_process_statistics(db: Session = Depends(get_db)):
    """
    Get statistics for TODAY ONLY - cumulative for the current day
    Resets at midnight automatically
    """
    # Get all records from database
    all_records = db.query(VMMachine).all()
    
    # Filter only today's records
    today_records = [r for r in all_records if is_today(r.created_date)]
    
    # Count by status for today only
    total = len(today_records)
    
    completed_count = sum(1 for r in today_records if r.process_status == 'COMPLETED')
    failed_count = sum(1 for r in today_records if r.process_status == 'FAILED')
    in_queue_count = sum(1 for r in today_records if r.process_status == 'IN_QUEUE')
    in_progress_count = sum(1 for r in today_records if r.process_status == 'IN_PROGRESS')
    
    # Calculate average execution time from time_taken column (today's records only)
    # time_taken is in SECONDS - convert to MINUTES for display
    completed_with_time = [
        r for r in today_records
        if r.process_status == 'COMPLETED' and r.time_taken
    ]

    if completed_with_time:
        try:
            # Filter out invalid values and convert to float
            valid_times = []
            for r in completed_with_time:
                try:
                    time_val = float(r.time_taken)
                    # Only include positive, reasonable values (1 second to 100000 seconds)
                    if 1 <= time_val <= 100000:
                        valid_times.append(time_val)
                except (ValueError, TypeError):
                    continue

            if valid_times:
                # Calculate average in seconds
                avg_time_seconds = sum(valid_times) / len(valid_times)
                # Convert seconds to minutes and round to 1 decimal place
                avg_exec_mins = round(avg_time_seconds / 60, 1)
            else:
                avg_exec_mins = 0.0
        except Exception as e:
            print(f"Error calculating average time: {e}")
            avg_exec_mins = 0.0
    else:
        avg_exec_mins = 0.0
    
    return {
        "total_processes": total,
        "completed": completed_count,
        "failed": failed_count,
        "in_queue": in_queue_count,
        "in_progress": in_progress_count,
        "avg_exec_time_mins": avg_exec_mins,
        "date": str(date.today())  # Include current date in response
    }

@app.get("/bots")
def get_bots(db: Session = Depends(get_db)):
    """Get list of bots in queue"""
    bots = db.query(VMMachine).filter(
        VMMachine.process_status == 'IN_QUEUE'
    ).limit(10).all()
    
    return {
        "bots": [{"id": b.id, "name": b.bot_id or f"Bot_{b.id}"} for b in bots]
    }

@app.get("/bots-in-progress")
def get_bots_in_progress(db: Session = Depends(get_db)):
    """Get bots currently processing"""
    bots = db.query(VMMachine).filter(
        VMMachine.process_status == 'IN_PROGRESS'
    ).all()
    
    return {
        "bots": [
            {
                "id": b.id,
                "name": b.bot_id,
                "vm": b.machine_name,
                "progress": 50  # Calculate based on start_time and estimated_tat
            } for b in bots
        ]
    }