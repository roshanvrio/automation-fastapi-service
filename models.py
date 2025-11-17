from sqlalchemy import Column, Integer, String, Float, DateTime
from database import metadata, engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class VMMachine(Base):
    __tablename__ = "vm_machines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mapping_process_type = Column(String(100))
    region = Column(String(100))
    tower_name = Column(String(100))
    rpa_tool = Column(String(100))
    process_name = Column(String(100))
    sub_process = Column(String(100))
    og_name = Column(String(200))
    email_from = Column(String(200))
    email_subject = Column(String(500))
    transaction_number = Column(String(100))
    process_status = Column(String(50))
    In_Queue = Column(String(50))  # NEW COLUMN ADDED
    case_status = Column(String(50))  # SUCCESS or EXCEPTION
    case_reason = Column(String(500))
    process_owner = Column(String(200))
    start_time = Column(String(50))
    end_time = Column(String(50))
    is_child = Column(Integer)
    time_taken = Column(String(50))
    bot_id = Column(String(100))
    machine_name = Column(String(200))  # VM Name
    email_received_tat = Column(String(50))
    created_date = Column(String(50))

# Create all tables
Base.metadata.create_all(engine)