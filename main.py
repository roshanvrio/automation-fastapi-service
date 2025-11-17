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

# Constants
UNKNOWN_BOT = "Unknown Bot"

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


def get_latest_vms(db: Session):
    """Get latest VM records from database"""
    latest_dates = db.query(
        VMMachine.machine_name,
        func.max(VMMachine.created_date).label('latest_date')
    ).group_by(VMMachine.machine_name).subquery()

    return db.query(VMMachine).join(
        latest_dates,
        (VMMachine.machine_name == latest_dates.c.machine_name) &
        (VMMachine.created_date == latest_dates.c.latest_date)
    ).filter(
        VMMachine.case_status.in_(['SUCCESS', 'EXCEPTION'])
    ).all()


def process_vm_records(latest_vms):
    """Process VM records and return status dict and bot mapping"""
    vm_status_dict = {}
    vm_bot_mapping = {}

    for vm in latest_vms:
        if not vm.machine_name:
            continue

        vm_number = extract_vm_number(vm.machine_name)
        if vm_number == 0:
            continue

        formatted_name = f"VM_{str(vm_number).zfill(2)}"
        vm_status = "active" if vm.case_status == "SUCCESS" else "pending"
        vm_bot_mapping[formatted_name] = vm.bot_id or UNKNOWN_BOT

        # Prioritize 'pending' over 'active'
        if formatted_name in vm_status_dict:
            if vm_status == "pending":
                vm_status_dict[formatted_name] = vm_status
                vm_bot_mapping[formatted_name] = vm.bot_id or UNKNOWN_BOT
        else:
            vm_status_dict[formatted_name] = vm_status

    return vm_status_dict, vm_bot_mapping


def filter_by_status(vm_status_dict, status: Optional[str]):
    """Filter VM status dict by requested status"""
    if not status:
        return vm_status_dict

    status_mapping = {'active': 'SUCCESS', 'pending': 'EXCEPTION'}
    if status.lower() not in status_mapping:
        return vm_status_dict

    requested_status = status.lower()
    return {
        vm: st for vm, st in vm_status_dict.items()
        if st == requested_status
    }


def build_response(vm_status_dict, vm_bot_mapping, status: Optional[str]):
    """Build final response with machine list and counts"""
    machines_with_status = [
        {
            "machine_name": vm,
            "status": st,
            "bot_id": vm_bot_mapping.get(vm, UNKNOWN_BOT)
        }
        for vm, st in sorted(vm_status_dict.items())
    ]

    active_count = sum(1 for m in machines_with_status if m["status"] == "active")
    pending_count = sum(1 for m in machines_with_status if m["status"] == "pending")

    return {
        "status": status.lower() if status else "all",
        "total_count": len(machines_with_status),
        "active_count": active_count,
        "pending_count": pending_count,
        "machines": machines_with_status
    }


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
            except (ValueError, TypeError):
                continue

        # If time only format (like "05:53.4"), assume it's from today
        if ':' in date_string and '.' in date_string:
            return True

        return False
    except Exception:
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
    latest_vms = get_latest_vms(db)
    vm_status_dict, vm_bot_mapping = process_vm_records(latest_vms)
    filtered_vms = filter_by_status(vm_status_dict, status)
    return build_response(filtered_vms, vm_bot_mapping, status)


def get_today_records(db: Session):
    """Get all records from today only"""
    all_records = db.query(VMMachine).all()
    return [r for r in all_records if is_today(r.created_date)]


def count_by_status(records):
    """Count records by process status"""
    return {
        'total': len(records),
        'completed': sum(1 for r in records if r.process_status == 'COMPLETED'),
        'failed': sum(1 for r in records if r.process_status == 'FAILED'),
        'in_queue': sum(1 for r in records if r.process_status == 'IN_QUEUE'),
        'in_progress': sum(1 for r in records if r.process_status == 'IN_PROGRESS')
    }


def extract_valid_times(records):
    """Extract valid time values from completed records"""
    completed_with_time = [
        r for r in records
        if r.process_status == 'COMPLETED' and r.time_taken
    ]

    valid_times = []
    for record in completed_with_time:
        try:
            time_val = float(record.time_taken)
            # Only include positive, reasonable values (1 second to 100000 seconds)
            if 1 <= time_val <= 100000:
                valid_times.append(time_val)
        except (ValueError, TypeError):
            continue

    return valid_times


def calculate_avg_execution_time(records):
    """Calculate average execution time in minutes from records"""
    try:
        valid_times = extract_valid_times(records)

        if valid_times:
            avg_time_seconds = sum(valid_times) / len(valid_times)
            # Convert seconds to minutes and round to 1 decimal place
            return round(avg_time_seconds / 60, 1)
        return 0.0
    except Exception as e:
        print(f"Error calculating average time: {e}")
        return 0.0


@app.get("/process-statistics/")
def get_process_statistics(db: Session = Depends(get_db)):
    """
    Get statistics for TODAY ONLY - cumulative for the current day
    Resets at midnight automatically
    """
    today_records = get_today_records(db)
    status_counts = count_by_status(today_records)
    avg_exec_mins = calculate_avg_execution_time(today_records)

    return {
        "total_processes": status_counts['total'],
        "completed": status_counts['completed'],
        "failed": status_counts['failed'],
        "in_queue": status_counts['in_queue'],
        "in_progress": status_counts['in_progress'],
        "avg_exec_time_mins": avg_exec_mins,
        "date": str(date.today())
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