from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, PrimaryKeyConstraint
from app.database.connection import Base

class ProcessTransaction(Base):
    __tablename__ = "process_transactions"

    __table_args__ = (
        PrimaryKeyConstraint('ProcessTransactionId', 'StartTime', name='pk_process_transaction'),
    )
    
    
    # Integer fields
    MappingId = Column(Integer, nullable=False)
    ProcessTransactionId = Column(Integer, nullable=False)
    TimeTaken = Column(Integer, nullable=False)
    TAT = Column(Integer, nullable=False)
    
    # String fields
    Country = Column(String(100), nullable=False)
    TowerName = Column(String(100), nullable=False)
    RPATool = Column(String(100), nullable=False)
    ProcessName = Column(String(200), nullable=False)
    OGName = Column(String(100), nullable=False)
    TransactionNo = Column(String(200), nullable=False)
    ProcessStatus = Column(String(100), nullable=False)
    CaseStatus = Column(String(100), nullable=False)
    CaseReason = Column(String(500), nullable=False)
    ProcessOwner = Column(String(200), nullable=False)
    MachineName = Column(String(200), nullable=True)
    
    # DateTime fields
    StartTime = Column(DateTime, nullable=True)
    EndTime = Column(DateTime, nullable=True)
    CreatedDate = Column(DateTime, nullable=True)
    
    # Boolean field
    isChild = Column(Boolean, nullable=False, default=False)
    
    # Nullable fields
    EmailFrom = Column(String(50), nullable=True)
    EmailSubject = Column(String(200), nullable=True)
    BotID = Column(String(100), nullable=True)
    EmailReceivedTime = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ProcessTransaction(id={self.id}, ProcessTransactionId={self.ProcessTransactionId}, ProcessName={self.ProcessName})>"


class VMPool(Base):
    __tablename__ = "vm_pool"
    
    automation_anywhere_vms = Column("Automation Anywhere VMs", String(50), primary_key=True, nullable=True)
    uipath_vms = Column("Uipath VMs", String(50), primary_key=True, nullable=True)
    
    def __repr__(self):
        return f"<VMPool(aa_vm={self.automation_anywhere_vms}, uipath_vm={self.uipath_vms})>"