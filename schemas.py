from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class VMMachineBase(BaseModel):
    mapping_process_type: Optional[str] = None
    region: Optional[str] = None
    tower_name: Optional[str] = None
    rpa_tool: Optional[str] = None
    process_name: Optional[str] = None
    sub_process: Optional[str] = None
    og_name: Optional[str] = None
    email_from: Optional[str] = None
    email_subject: Optional[str] = None
    transaction_number: Optional[str] = None
    process_status: Optional[str] = None
    In_Queue: Optional[str] = None  # NEW FIELD ADDED
    case_status: Optional[str] = None
    case_reason: Optional[str] = None
    process_owner: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    is_child: Optional[int] = None
    time_taken: Optional[str] = None
    bot_id: Optional[str] = None
    machine_name: Optional[str] = None
    email_received_tat: Optional[str] = None
    created_date: Optional[str] = None

class VMMachineResponse(VMMachineBase):
    id: int
    
    class Config:
        from_attributes = True

class VMStatusResponse(BaseModel):
    status: str
    count: int
    machines: List[str]

class MachineWithStatus(BaseModel):
    machine_name: str
    status: str

class VMStatusDetailResponse(BaseModel):
    status: str
    total_count: int
    active_count: int
    pending_count: int
    machines: List[MachineWithStatus]

class ProcessStatusResponse(BaseModel):
    status: str
    count: int
    processes: List[Dict[str, Any]]