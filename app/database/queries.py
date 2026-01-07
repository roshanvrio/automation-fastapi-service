from sqlalchemy.orm import Session
from sqlalchemy import text

def get_metrics(db: Session) -> dict:
    try:
        query = text("""
            SELECT
                SUM(CASE WHEN CaseStatus = 'EXCEPTION' THEN 1 ELSE 0 END) as exceptions,
                SUM(CASE WHEN CaseStatus = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN ProcessStatus = 'NEW' THEN 1 ELSE 0 END) as total_in_queue,
                SUM(CASE WHEN CaseStatus = 'ERROR' THEN 1 ELSE 0 END) as errors,
                CAST(AVG(
                    CASE
                        WHEN StartTime IS NOT NULL AND EndTime IS NOT NULL
                        THEN DATEDIFF(SECOND, StartTime, EndTime) / 60.0
                        ELSE NULL
                    END
                ) AS INT) as avg_time
            FROM process_transactions
        """)

        result = db.execute(query).fetchone()

        return {
            "exceptions": result.exceptions or 0,
            "successful": result.successful or 0,
            "totalInQueue": result.total_in_queue or 0,
            "errors": result.errors or 0,
            "avgTime": result.avg_time or 0
        }
    except Exception as e:
        print(f"Error in get_metrics: {e}")
        return {
            "exceptions": 0,
            "successful": 0,
            "totalInQueue": 0,
            "errors": 0,
            "avgTime": 0
        }
    
def get_queue_priority(db: Session):
    try:
        query = text("""
            SELECT
                ProcessName as processName,
                CASE
                    WHEN MAX(CASE WHEN EmailFrom IS NOT NULL THEN 1 ELSE 0 END) = 1
                    THEN 'Email'
                    ELSE 'Schedule'
                END as triggerIndication,
                SUM(CASE WHEN ProcessStatus = 'NEW' THEN 1 ELSE 0 END) as inQueueCount,
                COUNT(ProcessTransactionId) as totalCount,
                MAX(RPATool) as rpaTool
            FROM process_transactions
            GROUP BY ProcessName
            HAVING SUM(CASE WHEN ProcessStatus = 'NEW' THEN 1 ELSE 0 END) > 0
            ORDER BY inQueueCount DESC
        """)

        results = db.execute(query).fetchall()

        return [
            {
                "processName": row.processName,
                "triggerIndication": row.triggerIndication,
                "inQueueCount": row.inQueueCount,
                "totalCount": row.totalCount,
                "rpaTool": row.rpaTool
            }
            for row in results
        ]

    except Exception as e:
        print(f"Error in get_queue_priority: {e}")
        return []
    

def get_active_vms(db: Session) -> list:
    try:
        query = text("""
            WITH ongoing_vms AS (
                SELECT
                    ProcessTransactionId,
                    MachineName,
                    ProcessName,
                    StartTime,
                    EmailFrom,
                    RPATool
                FROM process_transactions
                WHERE ProcessStatus = 'INPROGRESS'
                  AND MachineName IS NOT NULL
            ),
            aggregated_stats AS (
                SELECT
                    MachineName,
                    ProcessName,
                    SUM(CASE WHEN ProcessStatus = 'COMPLETED' THEN 1 ELSE 0 END) as completed_count,
                    SUM(CASE
                        WHEN ProcessStatus = 'COMPLETED'
                         AND CaseStatus = 'COMPLETED'
                        THEN 1 ELSE 0
                    END) as successful_count,
                    SUM(CASE
                        WHEN ProcessStatus = 'FAILED'
                         AND CaseStatus IN ('ERROR', 'EXCEPTION')
                        THEN 1 ELSE 0
                    END) as failed_count
                FROM process_transactions
                GROUP BY MachineName, ProcessName
            )
            SELECT
                o.ProcessTransactionId as transactionId,
                o.MachineName as machineName,
                o.ProcessName as processName,
                CASE
                    WHEN o.EmailFrom IS NOT NULL THEN 'Email'
                    ELSE 'Scheduled'
                END as triggerIndication,
                COALESCE(s.completed_count, 0) as completedTransactions,
                CAST(DATEDIFF(SECOND, o.StartTime, GETDATE()) / 60 AS INT) as runTimeMinutes,
                o.RPATool as rpaTool,
                COALESCE(s.successful_count, 0) as successfulCount,
                COALESCE(s.failed_count, 0) as failedCount
            FROM ongoing_vms o
            LEFT JOIN aggregated_stats s
                ON o.MachineName = s.MachineName
               AND o.ProcessName = s.ProcessName
            ORDER BY runTimeMinutes DESC
        """)

        results = db.execute(query).fetchall()

        active_vms = []
        for row in results:
            # Format time display
            total_minutes = row.runTimeMinutes
            if total_minutes is None or total_minutes == 0:
                last_run_time = "0 mins"
            elif total_minutes >= 60:
                hours = total_minutes / 60
                last_run_time = f"{hours:.1f} Hours"
            else:
                last_run_time = f"{int(total_minutes)} mins"

            active_vms.append({
                "transactionId": row.transactionId,
                "machineName": row.machineName,
                "processName": row.processName,
                "triggerIndication": row.triggerIndication,
                "completedTransactions": row.completedTransactions,
                "lastRunTime": last_run_time,
                "rpaTool": row.rpaTool,
                "successfulCount": row.successfulCount,
                "failedCount": row.failedCount
            })

        return active_vms

    except Exception as e:
        print(f"Error in get_active_vms: {e}")
        return []
    
def get_idle_vms(db: Session) -> list:
    try:
        query = text("""
            WITH all_vms AS (
                SELECT [Automation Anywhere VMs] as vm_name
                FROM vm_pool
                WHERE [Automation Anywhere VMs] IS NOT NULL

                UNION

                SELECT [Uipath VMs] as vm_name
                FROM vm_pool
                WHERE [Uipath VMs] IS NOT NULL
            ),
            active_vms AS (
                SELECT DISTINCT
                    CASE
                        WHEN MachineName LIKE '%.BOT'
                        THEN LEFT(MachineName, LEN(MachineName) - 4)
                        ELSE MachineName
                    END as vm_name
                FROM process_transactions
                WHERE ProcessStatus = 'INPROGRESS'
                  AND MachineName IS NOT NULL
            ),
            idle_vms AS (
                SELECT vm_name
                FROM all_vms
                EXCEPT
                SELECT vm_name
                FROM active_vms
            )
            SELECT vm_name
            FROM idle_vms
            ORDER BY
                -- Extract the prefix (non-numeric part)
                LEFT(vm_name, PATINDEX('%[0-9]%', vm_name) - 1),
                -- Extract and sort by the numeric part
                CAST(SUBSTRING(vm_name, PATINDEX('%[0-9]%', vm_name), LEN(vm_name)) AS INT)
        """)

        results = db.execute(query).fetchall()
        return [row.vm_name for row in results]

    except Exception as e:
        print(f"Error in get_idle_vms: {e}")
        return []
    
def get_vm_utilization(db: Session) -> dict:
    try:
        query = text("""
            WITH all_vms AS (
                SELECT [Automation Anywhere VMs] as vm_name
                FROM vm_pool
                WHERE [Automation Anywhere VMs] IS NOT NULL
                UNION
                SELECT [Uipath VMs] as vm_name
                FROM vm_pool
                WHERE [Uipath VMs] IS NOT NULL
            ),
            vm_stats AS (
                SELECT
                    CASE
                        WHEN MachineName LIKE '%.BOT'
                        THEN LEFT(MachineName, LEN(MachineName) - 4)
                        ELSE MachineName
                    END as vm_name,
                    SUM(CASE WHEN ProcessStatus = 'COMPLETED' THEN 1 ELSE 0 END) as completed_count,
                    SUM(
                        CASE
                            WHEN ProcessStatus = 'COMPLETED'
                             AND StartTime IS NOT NULL
                             AND EndTime IS NOT NULL
                            THEN CAST(DATEDIFF(SECOND, StartTime, EndTime) AS FLOAT) / 3600.0
                            ELSE 0
                        END
                    ) as completed_hours,
                    SUM(
                        CASE
                            WHEN ProcessStatus = 'INPROGRESS'
                             AND StartTime IS NOT NULL
                            THEN CAST(DATEDIFF(SECOND, StartTime, GETDATE()) AS FLOAT) / 3600.0
                            ELSE 0
                        END
                    ) as ongoing_hours
                FROM process_transactions
                WHERE MachineName IS NOT NULL
                GROUP BY
                    CASE
                        WHEN MachineName LIKE '%.BOT'
                        THEN LEFT(MachineName, LEN(MachineName) - 4)
                        ELSE MachineName
                    END
            ),
            vm_utilization AS (
                SELECT
                    v.vm_name as vmName,
                    COALESCE(s.completed_count, 0) as completedTransactions,
                    ROUND(COALESCE(s.completed_hours, 0) + COALESCE(s.ongoing_hours, 0), 1) as utilizationHours
                FROM all_vms v
                LEFT JOIN vm_stats s ON
                    -- Handle both VM4 and VM04 formats - match if either exact or with leading zero
                    (v.vm_name = s.vm_name OR v.vm_name = 'VM0' + SUBSTRING(s.vm_name, 3, LEN(s.vm_name)) OR 'VM0' + SUBSTRING(v.vm_name, 3, LEN(v.vm_name)) = s.vm_name)
            )
            SELECT
                vmName,
                completedTransactions,
                utilizationHours,
                CASE
                    WHEN utilizationHours = MAX(utilizationHours) OVER () THEN 1
                    ELSE 0
                END as is_top_performer
            FROM vm_utilization
            ORDER BY utilizationHours DESC
        """)

        results = db.execute(query).fetchall()

        vm_utilization_list = []
        top_performer_data = {"vmName": "N/A", "utilizationHours": 0.0}

        for row in results:
            vm_data = {
                "vmName": row.vmName,
                "completedTransactions": row.completedTransactions,
                "utilizationHours": row.utilizationHours
            }
            vm_utilization_list.append(vm_data)

            if row.is_top_performer == 1:
                top_performer_data = {
                    "vmName": row.vmName,
                    "utilizationHours": row.utilizationHours
                }

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

def get_recently_completed_transactions(db: Session) -> dict:
    """
    Get the latest completed transactions, grouped by outcome.

    For testing: Returns latest 50 transactions regardless of time.
    Once animation works, this should be changed back to time-based filtering.

    Args:
        db: Database session

    Returns:
        dict with three lists: successful, error, exception
        Each list contains: transactionId, machineName, processName
    """
    try:
        # For testing: get the latest 50 completed transactions regardless of time
        # Once animation works, change this back to time-based filtering
        query = text("""
            WITH recently_completed AS (
                SELECT TOP 50
                    ProcessTransactionId as transactionId,
                    MachineName as machineName,
                    ProcessName as processName,
                    ProcessStatus,
                    CaseStatus,
                    EndTime
                FROM process_transactions
                WHERE EndTime IS NOT NULL
                  AND MachineName IS NOT NULL
                  AND CaseStatus IN ('SUCCESS', 'ERROR', 'EXCEPTION')
                ORDER BY EndTime DESC
            )
            SELECT
                transactionId,
                machineName,
                processName,
                CaseStatus as outcome
            FROM recently_completed
            ORDER BY EndTime DESC
        """)

        results = db.execute(query).fetchall()

        # Group by outcome
        successful = []
        error = []
        exception = []

        for row in results:
            transaction = {
                "transactionId": row.transactionId,
                "machineName": row.machineName,
                "processName": row.processName
            }

            if row.outcome == 'SUCCESS':
                successful.append(transaction)
            elif row.outcome == 'ERROR':
                error.append(transaction)
            elif row.outcome == 'EXCEPTION':
                exception.append(transaction)

        return {
            "successful": successful,
            "error": error,
            "exception": exception
        }

    except Exception as e:
        print(f"Error in get_recently_completed_transactions: {e}")
        return {
            "successful": [],
            "error": [],
            "exception": []
        }