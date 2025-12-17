# app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import SessionLocal
from datetime import datetime

def get_metrics():
    db = SessionLocal()
    
    try:
        # Count errors
        errors = db.execute(
            text("SELECT COUNT(*) FROM excel_data WHERE CaseStatus = 'ERROR'")
        ).scalar()

        # Count exceptions
        exceptions = db.execute(
            text("SELECT COUNT(*) FROM excel_data WHERE CaseStatus = 'EXCEPTION'")
        ).scalar()

        # Count successful
        successful = db.execute(
            text("SELECT COUNT(*) FROM excel_data WHERE CaseStatus = 'SUCCESS'")
        ).scalar()

        # Count in progress (ProcessStatus = 'NEW')
        in_progress = db.execute(
            text("SELECT COUNT(*) FROM excel_data WHERE ProcessStatus = 'NEW'")
        ).scalar()

        # Count total in queue (same as in progress for now)
        total_queue = in_progress

        # Calculate average utilization time
        # Assuming you have StartTime and EndTime columns
        avg_time_result = db.execute(
            text("""
                SELECT AVG(DATEDIFF(MINUTE, StartTime, EndTime)) 
                FROM excel_data 
                WHERE StartTime IS NOT NULL 
                AND EndTime IS NOT NULL
                AND CaseStatus = 'SUCCESS'
            """)
        ).scalar()
        
        avg_time = int(avg_time_result) if avg_time_result else 0

        return {
            "errors": errors or 0,
            "exceptions": exceptions or 0,
            "successful": successful or 0,
            "inProgress": in_progress or 0,
            "totalInQueue": total_queue or 0,
            "avgTime": avg_time
        }
    
    except Exception as e:
        print(f"Error in get_metrics: {str(e)}")
        return {
            "errors": 0,
            "exceptions": 0,
            "successful": 0,
            "inProgress": 0,
            "totalInQueue": 0,
            "avgTime": 0
        }
    finally:
        db.close()


def get_queue_prioritization():
    """Get queue prioritization data with inQueueCount (NEW) and totalCount (all statuses)"""
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT
                    [ProcessName],
                    MAX(CASE WHEN [EmailFrom] IS NOT NULL THEN 'Email' ELSE 'No Email' END) AS TriggerIndication,
                    COUNT(CASE WHEN UPPER([ProcessStatus]) = 'NEW' THEN 1 END) AS InQueueCount,
                    COUNT(*) AS TotalCount
                FROM [dbo].[excel_data]
                GROUP BY [ProcessName]
                HAVING COUNT(CASE WHEN UPPER([ProcessStatus]) = 'NEW' THEN 1 END) > 0
                ORDER BY COUNT(CASE WHEN UPPER([ProcessStatus]) = 'NEW' THEN 1 END) DESC
            """)
        ).fetchall()

        return [
            {
                "processName": row[0],
                "triggerIndication": row[1],
                "inQueueCount": row[2],
                "totalCount": row[3]
            }
            for row in result
        ]
    except Exception as e:
        print(f"Error in get_queue_prioritization: {str(e)}")
        return []
    finally:
        db.close()


def get_active_vms():
    """Get machine names and process names where CaseStatus is InProgress"""
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT [MachineName], [ProcessName]
                FROM [dbo].[excel_data]
                WHERE [CaseStatus] = 'InProgress'
                AND [MachineName] IS NOT NULL
                ORDER BY [MachineName]
            """)
        ).fetchall()

        return [
            {
                "machineName": row[0],
                "processName": row[1] or "Unknown Process"
            }
            for row in result
        ]
    except Exception as e:
        print(f"Error in get_active_vms: {str(e)}")
        return []
    finally:
        db.close()


def get_idle_vms():
    """Get distinct machine names that are NOT currently in progress (for Entry/Exit pool)"""
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT DISTINCT [MachineName]
                FROM [dbo].[excel_data]
                WHERE [MachineName] IS NOT NULL
                AND [MachineName] NOT IN (
                    SELECT DISTINCT [MachineName]
                    FROM [dbo].[excel_data]
                    WHERE [CaseStatus] = 'InProgress'
                    AND [MachineName] IS NOT NULL
                )
                ORDER BY [MachineName]
            """)
        ).fetchall()

        return [row[0] for row in result]
    except Exception as e:
        print(f"Error in get_idle_vms: {str(e)}")
        return []
    finally:
        db.close()