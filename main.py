"""
FastAPI Backend for Queue Dashboard
====================================
This application provides REST API endpoints for monitoring VM machines and bot processing status.

Main Features:
- Real-time VM status tracking (active/pending)
- Process statistics (completed, failed, in queue, in progress)
- Auto-refresh every 30 seconds
- Daily statistics that reset at midnight
- Time tracking in seconds, converted to minutes for display
"""

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

# ==================== CONSTANTS ====================
# Default value for bot names when not available in database
UNKNOWN_BOT = "Unknown Bot"

# ==================== APP INITIALIZATION ====================
app = FastAPI(title="VM Machine Status API")

# Enable CORS - Allow all origins for development
# This allows the frontend to make API calls from any domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== DATABASE DEPENDENCY ====================
def get_db():
    """
    Database session dependency
    - Creates a new database session for each request
    - Ensures session is closed after request completes
    - Used with FastAPI's Depends() for dependency injection
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== API ENDPOINTS ====================

@app.get("/")
def home():
    """
    Root endpoint - Serves the dashboard HTML file
    - Returns: index.html with the queue dashboard interface
    """
    return FileResponse("index.html")


# ==================== HELPER FUNCTIONS FOR VM STATUS ====================

def extract_vm_number(machine_name: str) -> int:
    """
    Extract numeric VM number from machine name
    - Input: "VM17.BOT", "vm25", "VM_03" etc.
    - Output: 17, 25, 3 respectively
    - Returns: 0 if no valid number found
    - Uses regex to find digits after 'VM'
    """
    if not machine_name:
        return 0
    match = re.search(r'VM(\d+)', machine_name, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def get_latest_vms(db: Session):
    """
    Fetch only the most recent record for each VM machine from database
    - Groups by machine_name to avoid duplicates
    - Gets the latest created_date for each machine
    - Filters for SUCCESS and EXCEPTION status only
    - Returns: List of VM machine records
    """
    # Subquery to find latest date for each machine
    latest_dates = db.query(
        VMMachine.machine_name,
        func.max(VMMachine.created_date).label('latest_date')
    ).group_by(VMMachine.machine_name).subquery()

    # Join to get full records for only the latest entries
    return db.query(VMMachine).join(
        latest_dates,
        (VMMachine.machine_name == latest_dates.c.machine_name) &
        (VMMachine.created_date == latest_dates.c.latest_date)
    ).filter(
        VMMachine.case_status.in_(['SUCCESS', 'EXCEPTION'])
    ).all()


def process_vm_records(latest_vms):
    """
    Process VM records and format them for frontend display
    - Converts machine names to standard format (VM_01, VM_02, etc.)
    - Maps case_status: SUCCESS -> 'active', EXCEPTION -> 'pending'
    - Creates bot_id mapping for each VM
    - Extracts execution time (time_taken) in seconds
    - Prioritizes 'pending' status over 'active' if VM appears multiple times
    - Returns: (vm_status_dict, vm_bot_mapping, vm_time_mapping)
    """
    vm_status_dict = {}
    vm_bot_mapping = {}
    vm_time_mapping = {}

    for vm in latest_vms:
        # Skip records without machine name
        if not vm.machine_name:
            continue

        # Extract number and skip if invalid
        vm_number = extract_vm_number(vm.machine_name)
        if vm_number == 0:
            continue

        # Format as VM_01, VM_02, etc. (zero-padded)
        formatted_name = f"VM_{str(vm_number).zfill(2)}"

        # Convert database status to frontend status
        vm_status = "active" if vm.case_status == "SUCCESS" else "pending"
        vm_bot_mapping[formatted_name] = vm.bot_id or UNKNOWN_BOT

        # Extract execution time in seconds (convert to float, default to 0)
        try:
            execution_time = float(vm.time_taken) if vm.time_taken else 0.0
        except (ValueError, TypeError):
            execution_time = 0.0

        vm_time_mapping[formatted_name] = execution_time

        # If VM already exists, prioritize 'pending' over 'active'
        # This ensures error states are always visible
        if formatted_name in vm_status_dict:
            if vm_status == "pending":
                vm_status_dict[formatted_name] = vm_status
                vm_bot_mapping[formatted_name] = vm.bot_id or UNKNOWN_BOT
                vm_time_mapping[formatted_name] = execution_time
        else:
            vm_status_dict[formatted_name] = vm_status

    return vm_status_dict, vm_bot_mapping, vm_time_mapping


def filter_by_status(vm_status_dict, status: Optional[str]):
    """
    Filter VM machines by requested status
    - Input status: 'active', 'pending', or None (all)
    - Returns filtered dictionary containing only matching VMs
    - If status is invalid or None, returns all VMs
    """
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


def build_response(vm_status_dict, vm_bot_mapping, vm_time_mapping, status: Optional[str]):
    """
    Build final JSON response for /vm-status endpoint
    - Combines VM status, bot mapping, and execution time
    - Sorts machines by name (VM_01, VM_02, ...)
    - Counts active and pending machines
    - Returns: JSON with machines list and statistics including execution time
    """
    # Create list of machines with all their info
    machines_with_status = [
        {
            "machine_name": vm,
            "status": st,
            "bot_id": vm_bot_mapping.get(vm, UNKNOWN_BOT),
            "execution_time_seconds": vm_time_mapping.get(vm, 0.0)
        }
        for vm, st in sorted(vm_status_dict.items())
    ]

    # Count machines by status
    active_count = sum(1 for m in machines_with_status if m["status"] == "active")
    pending_count = sum(1 for m in machines_with_status if m["status"] == "pending")

    return {
        "status": status.lower() if status else "all",
        "total_count": len(machines_with_status),
        "active_count": active_count,
        "pending_count": pending_count,
        "machines": machines_with_status
    }


# ==================== DATE/TIME HELPER FUNCTIONS ====================

def is_today(date_string: str) -> bool:
    """
    Check if a date string represents today's date
    - Tries multiple date formats to parse the string
    - Handles: '2025-11-19', '19/11/2025', '15:45.3', etc.
    - Assumes time-only formats are from today
    - Returns: True if date is today, False otherwise
    - Used for filtering today's records for statistics
    """
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


# ==================== VM STATUS ENDPOINT ====================

@app.get("/vm-status")
def get_vm_by_status(
    status: Optional[str] = Query(None, description="Filter by status: 'active' (SUCCESS), 'pending' (EXCEPTION), or leave empty for all"),
    db: Session = Depends(get_db)
):
    """
    API Endpoint: Get VM machines by status
    - URL: GET /vm-status?status=active (or pending, or omit for all)
    - Returns: List of VMs with their status and bot assignments
    - Format: VM names as VM_01, VM_02, etc.
    - Auto-refreshed by frontend every 30 seconds

    Response example:
    {
        "status": "all",
        "total_count": 15,
        "active_count": 10,
        "pending_count": 5,
        "machines": [...]
    }
    """
    # Step 1: Get latest VM records from database
    latest_vms = get_latest_vms(db)

    # Step 2: Process and format VM records (now returns execution time too)
    vm_status_dict, vm_bot_mapping, vm_time_mapping = process_vm_records(latest_vms)

    # Step 3: Filter by requested status (if any)
    filtered_vms = filter_by_status(vm_status_dict, status)

    # Step 4: Build and return JSON response with execution time data
    return build_response(filtered_vms, vm_bot_mapping, vm_time_mapping, status)


# ==================== HELPER FUNCTIONS FOR PROCESS STATISTICS ====================

def get_today_records(db: Session):
    """
    Fetch all records from today only
    - Queries entire vm_machines table
    - Filters using is_today() function
    - Returns: List of today's records only
    - Used for daily statistics that reset at midnight
    """
    all_records = db.query(VMMachine).all()
    return [r for r in all_records if is_today(r.created_date)]


def count_by_status(records):
    """
    Count records by their process status
    - Counts: COMPLETED, FAILED, IN_QUEUE, IN_PROGRESS
    - Returns: Dictionary with counts for each status
    - Used for dashboard statistics display
    """
    return {
        'total': len(records),
        'completed': sum(1 for r in records if r.process_status == 'COMPLETED'),
        'failed': sum(1 for r in records if r.process_status == 'FAILED'),
        'in_queue': sum(1 for r in records if r.process_status == 'IN_QUEUE'),
        'in_progress': sum(1 for r in records if r.process_status == 'IN_PROGRESS')
    }


def extract_valid_times(records):
    """
    Extract valid execution time values from completed records
    - Filters for COMPLETED status with time_taken value
    - Validates time range: 1 to 100,000 seconds
    - Skips invalid/malformed time values
    - Returns: List of valid time values in seconds
    """
    # Get only completed records with time data
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
    """
    Calculate average execution time in MINUTES from records
    - Database stores time in SECONDS
    - Converts to MINUTES for frontend display (÷ 60)
    - Rounds to 1 decimal place
    - Returns: 0.0 if no valid data or error
    - Example: 164 seconds → 2.7 minutes
    """
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


# ==================== PROCESS STATISTICS ENDPOINT ====================

@app.get("/process-statistics/")
def get_process_statistics(db: Session = Depends(get_db)):
    """
    API Endpoint: Get today's process statistics
    - URL: GET /process-statistics/
    - Returns: Statistics for TODAY ONLY (resets at midnight)
    - Auto-refreshed by frontend every 30 seconds

    Response includes:
    - total_processes: Total count for today
    - completed: Successfully finished processes
    - failed: Processes with errors
    - in_queue: Waiting to be processed
    - in_progress: Currently running
    - avg_exec_time_mins: Average execution time in minutes
    - date: Current date (YYYY-MM-DD)
    """
    # Step 1: Get all records from today
    today_records = get_today_records(db)

    # Step 2: Count by each status
    status_counts = count_by_status(today_records)

    # Step 3: Calculate average execution time
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
    """
    API Endpoint: Get list of bots waiting in queue
    - URL: GET /bots
    - Returns: Up to 10 bots with process_status = 'IN_QUEUE'
    - Used for displaying queued bots on dashboard

    Response format:
    {
        "bots": [
            {"id": 123, "name": "Bot_ABC"},
            {"id": 124, "name": "Bot_XYZ"}
        ]
    }

    Notes:
    - Limited to 10 bots to prevent overwhelming the UI
    - Uses bot_id from database, or generates "Bot_{id}" if not available
    """
    bots = db.query(VMMachine).filter(
        VMMachine.process_status == 'IN_QUEUE'
    ).limit(10).all()

    return {
        "bots": [{"id": b.id, "name": b.bot_id or f"Bot_{b.id}"} for b in bots]
    }

@app.get("/bots-in-progress")
def get_bots_in_progress(db: Session = Depends(get_db)):
    """
    API Endpoint: Get bots currently being processed
    - URL: GET /bots-in-progress
    - Returns: All bots with process_status = 'IN_PROGRESS'
    - Displays real-time processing status on dashboard
    - Auto-refreshed by frontend every 30 seconds

    Response format:
    {
        "bots": [
            {
                "id": 123,
                "name": "Bot_ABC",
                "vm": "VM_01",
                "progress": 50
            }
        ]
    }

    Fields:
    - id: Database record ID
    - name: Bot identifier from bot_id column
    - vm: Machine name where bot is running
    - progress: Placeholder (currently fixed at 50%)
                TODO: Calculate based on start_time and estimated_tat

    Note: Progress calculation is not yet implemented
    """
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