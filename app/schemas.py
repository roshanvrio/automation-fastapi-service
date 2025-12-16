# app/schemas.py
from pydantic import BaseModel
from typing import Optional


# -----------------------------
# Metrics schema
# -----------------------------
class Metrics(BaseModel):
    exceptions: int
    successful: int
    inProgress: int
    errors: int
    avgTime: int


# -----------------------------
# VM Schema for Honeycomb Grid
# -----------------------------
class VMBase(BaseModel):
    id: str
    task: str
    utilization: Optional[str] = None    # "800 mins"
    status: Optional[str] = None         # success / error / busy
    automation: Optional[str] = None     # uipath / email / etc


class VMList(BaseModel):
    vms: list[VMBase]
