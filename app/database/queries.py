import re
from sqlalchemy.orm import Session
from sqlalchemy import text

def get_metrics(db: Session) -> dict:
    try:
        query = text("""
            SELECT
                SUM(CASE WHEN CaseStatus = 'EXCEPTION' THEN 1 ELSE 0 END) AS exceptions,
                SUM(CASE WHEN CaseStatus = 'SUCCESS' THEN 1 ELSE 0 END) AS successful,
                SUM(CASE WHEN ProcessStatus = 'NEW' THEN 1 ELSE 0 END) AS total_in_queue,
                SUM(CASE WHEN CaseStatus = 'ERROR' THEN 1 ELSE 0 END) AS errors,

            CAST(AVG(
                CASE 
                    WHEN StartTime IS NOT NULL 
                        AND EndTime IS NOT NULL
                        AND EndTime > StartTime
                    THEN DATEDIFF(SECOND, StartTime, EndTime) / 60.0

                 WHEN StartTime IS NOT NULL 
                        AND ProcessStatus = 'INPROGRESS'
                    THEN DATEDIFF(SECOND, StartTime, GETDATE()) / 60.0

                    ELSE NULL
                END
            ) AS INT) AS avg_time

        FROM VW_RPADashboard_New
        WHERE ProcessTransactionId IS NOT NULL
            AND CAST(CreatedDate AS DATE) = CAST(GETDATE() AS DATE);
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
            FROM VW_RPADashboard_New
            WHERE ProcessTransactionId IS NOT NULL
              AND CAST(CreatedDate AS DATE) = CAST(GETDATE() AS DATE)
            GROUP BY ProcessName
            HAVING SUM(CASE WHEN ProcessStatus = 'NEW' THEN 1 ELSE 0 END) > 0
            ORDER BY inQueueCount DESC, processName ASC
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
                    r.ProcessTransactionId,
                    r.MachineName,
                    r.ProcessName,
                    r.StartTime,
                    r.EmailFrom,
                    r.RPATool
                FROM VW_RPADashboard_New r
                WHERE r.ProcessStatus = 'INPROGRESS'
                    AND r.MachineName IS NOT NULL
                    AND r.ProcessTransactionId IS NOT NULL
                    AND CAST(r.CreatedDate AS DATE) = CAST(GETDATE() AS DATE)
            ),
            aggregated_stats AS (
                SELECT
                r.MachineName,
                r.ProcessName,
                SUM(CASE WHEN r.ProcessStatus = 'COMPLETED' THEN 1 ELSE 0 END) as completed_count,
                SUM(CASE
                        WHEN r.ProcessStatus = 'COMPLETED'
                        AND r.CaseStatus = 'COMPLETED'
                        THEN 1 ELSE 0
                    END) as successful_count,
                SUM(CASE
                        WHEN r.ProcessStatus = 'FAILED'
                        AND r.CaseStatus IN ('ERROR', 'EXCEPTION')
                        THEN 1 ELSE 0
                        END) as failed_count
                FROM VW_RPADashboard_New r
                WHERE r.ProcessTransactionId IS NOT NULL
                    AND CAST(r.CreatedDate AS DATE) = CAST(GETDATE() AS DATE)
                GROUP BY r.MachineName, r.ProcessName
            )
            SELECT
                o.ProcessTransactionId as transactionId,
                    COALESCE(m.UserName, o.MachineName) as machineName,
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
                LEFT JOIN [RPA_CoE_Dev_Manna].[dbo].[tblMachineDetails] m
                    ON o.MachineName = m.MachineName
                ORDER BY runTimeMinutes DESC;

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
    
# def get_idle_vms(db: Session) -> list:
#     try:
#         query = text("""
#             WITH all_vms AS (
#                 SELECT MachineName
#                 FROM [RPA_CoE_Dev_Manna].[dbo].[tblMachineDetails]
#                 WHERE MachineName IS NOT NULL
#                     AND Active = 1
#             ),
#             active_vms AS (
#                 SELECT DISTINCT
#                     MachineName
#                 FROM [dbo].[VW_RPADashboard_New]
#                 WHERE ProcessStatus = 'INPROGRESS'
#                     AND MachineName IS NOT NULL
#                     AND ProcessTransactionId IS NOT NULL
#                     AND CAST(CreatedDate AS DATE) = CAST(GETDATE() AS DATE)
#             ),
#             idle_vms AS (
#                 SELECT MachineName
#                 FROM all_vms
#                 EXCEPT
#                 SELECT MachineName
#                 FROM active_vms
#             )
#             SELECT DISTINCT m.UserName
#             FROM idle_vms i
#             LEFT JOIN [RPA_CoE_Dev_Manna].[dbo].[tblMachineDetails] m
#                 ON i.MachineName = m.MachineName
#             ORDER BY m.UserName;
#         """)

from sqlalchemy.orm import Session
from sqlalchemy import text

def get_idle_vms(db: Session) -> list:
    try:
        query = text("""
            WITH active_vms AS (
                SELECT DISTINCT MachineName
                FROM [dbo].[VW_RPADashboard_New]
                WHERE ProcessStatus = 'INPROGRESS'
                    AND MachineName IS NOT NULL
                    AND ProcessTransactionId IS NOT NULL
                    AND CAST(CreatedDate AS DATE) = CAST(GETDATE() AS DATE)
            ),
            idle_vms AS (
                SELECT
                     MachineName
                FROM [RPA_CoE_Dev_Manna].[dbo].[tblMachineDetails]
                WHERE MachineName IS NOT NULL
                    AND (
                        Active = 0
                        OR MachineName NOT IN (SELECT MachineName FROM active_vms)
                    )
            )
            SELECT DISTINCT m.UserName
            FROM [RPA_CoE_Dev_Manna].[dbo].[tblMachineDetails] m
            JOIN idle_vms i
                ON m.MachineName = i.MachineName
            ORDER BY m.UserName;
        """)

        results = db.execute(query).fetchall()
        return [row.UserName for row in results]

    except Exception as e:
        print(f"Error in get_idle_vms: {e}")
        return []

    
def get_vm_utilization(db: Session) -> dict:
    try:
        query = text("""
            WITH all_vms AS (
            SELECT
                MachineName,
                UserName
            FROM [RPA_CoE_Dev_Manna].[dbo].[tblMachineDetails]
            WHERE MachineName IS NOT NULL
                --AND Active = 1
            ),
            vm_stats AS (
                SELECT
                    MachineName,
                    SUM(CASE
                            WHEN ProcessStatus IN ('COMPLETED', 'FAILED')
                            THEN 1 ELSE 0
                        END) AS completed_count,
                    SUM(
                        CASE
                            WHEN ProcessStatus IN ('COMPLETED', 'FAILED')
                                AND StartTime IS NOT NULL
                                AND EndTime IS NOT NULL
                            THEN CAST(DATEDIFF(SECOND, StartTime, EndTime) AS FLOAT) / 60.0
                            ELSE 0
                        END
                    ) AS completed_minutes,
                    SUM(
                        CASE
                            WHEN ProcessStatus = 'INPROGRESS'
                                AND StartTime IS NOT NULL
                            THEN CAST(DATEDIFF(SECOND, StartTime, GETDATE()) AS FLOAT) / 60.0
                            ELSE 0
                        END
                    ) AS ongoing_minutes
                FROM [dbo].[VW_RPADashboard_New]
                WHERE MachineName IS NOT NULL
                    AND ProcessTransactionId IS NOT NULL
                    AND CAST(CreatedDate AS DATE) = CAST(GETDATE() AS DATE)
                GROUP BY MachineName
            ),
            vm_utilization AS (
                SELECT
            a.MachineName,
            a.UserName,
            COALESCE(s.completed_count, 0) AS completedTransactions,
            ROUND(
                    COALESCE(s.completed_minutes, 0)
                    + COALESCE(s.ongoing_minutes, 0),
                    1
            ) AS utilizationMinutes
        FROM all_vms a
        LEFT JOIN vm_stats s
            ON a.MachineName = s.MachineName
    )
    SELECT TOP (35)
        UserName AS vmName,
        completedTransactions,
        utilizationMinutes,
        CASE
            WHEN utilizationMinutes = MAX(utilizationMinutes) OVER ()
            THEN 1
            ELSE 0
        END AS is_top_performer
    FROM vm_utilization
    ORDER BY utilizationMinutes DESC;
        """)

        results = db.execute(query).fetchall()

        vm_utilization_list = []
        # top_performer_data = {"vmName": "N/A", "utilizationMinutes": 0.0}

        # for row in results:
        #     vm_data = {
        #         "vmName": row.vmName,
        #         "completedTransactions": row.completedTransactions,
        #         "utilizationMinutes": row.utilizationMinutes
        #     }
        #     vm_utilization_list.append(vm_data)

        #     if row.is_top_performer == 1:
        #         top_performer_data = {
        #             "vmName": row.vmName,
        #             "utilizationMinutes": row.utilizationMinutes
        #         }

        # return {
        #     "vmUtilization": vm_utilization_list,
        #     "topPerformer": top_performer_data
        # }

        # Revised Top Performing VM when execution hours are zero
        # Only show top performer if utilization > 0.00 (not for zero-usage VMs)

        top_performer_data = None
        
        for row in results:
            vm_utilization_list.append({
                "vmName": row.vmName,
                "completedTransactions": row.completedTransactions,
                "utilizationMinutes": row.utilizationMinutes
                })
            # Show top performer only if utilization is greater than 0.00
            # Example: 0.01 hrs will show, but 0.00 hrs will not
            if (
                top_performer_data is None
                and row.is_top_performer == 1
                and row.utilizationMinutes > 0
                ):
                top_performer_data = {
                    "vmName": row.vmName,
                    "utilizationMinutes": row.utilizationMinutes
                    }

        return {
            "vmUtilization": vm_utilization_list,
            "topPerformer": top_performer_data  # Returns None if all VMs have 0.00 hrs
        }
    except Exception as e:
        print(f"Error in get_vm_utilization: {e}")
        return {
            "vmUtilization": [],
            "topPerformer": {
                "vmName": "N/A",
                "utilizationMinutes": 0.0
            }
        }

def get_recently_completed_transactions(db: Session) -> dict:
    """
    Get the latest completed transactions from today, grouped by outcome.

    Returns transactions completed today to support completion animations.

    Args:
        db: Database session

    Returns:
        dict with three lists: successful, error, exception
        Each list contains: transactionId, machineName, processName, processStatus, caseStatus
    """
    try:
        query = text("""
            WITH recently_completed AS (
                SELECT              --TOP 50
                    ProcessTransactionId as transactionId,
                    MachineName as machineName,
                    ProcessName as processName,
                    ProcessStatus, 
                    CaseStatus,
                    EndTime
                FROM VW_RPADashboard_New
                WHERE EndTime IS NOT NULL
                  AND MachineName IS NOT NULL
                  AND ProcessTransactionId IS NOT NULL
                  AND CaseStatus IN ('SUCCESS', 'ERROR', 'EXCEPTION')
                  AND CAST(CreatedDate AS DATE) = CAST(GETDATE() AS DATE)
                --ORDER BY EndTime DESC
            )
            SELECT
                transactionId,
                machineName,
                processName,
                ProcessStatus,
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
                "processName": row.processName,
                "processStatus": row.ProcessStatus,
                "caseStatus": row.outcome
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

def get_vm_completed_transactions(db: Session) -> list:
    """
    Get all completed transactions (successful and failed) grouped by VM.

    Returns transactions from today, ordered by endTime DESC (most recent first)
    within each VM.

    Args:
        db: Database session

    Returns:
        List of VMs with their completed transactions:
        [
            {
                "machineName": "VM01.BOT",
                "transactions": [
                    {
                        "transactionId": 12345,
                        "processName": "Invoice Processing",
                        "caseStatus": "SUCCESS",
                        "startTime": "2026-01-08 14:25:00",
                        "endTime": "2026-01-08 14:30:25"
                    },
                    ...
                ]
            },
            ...
        ]
    """
    try:
        query = text("""
            SELECT
                MachineName as machineName,
                ProcessTransactionId as transactionId,
                ProcessName as processName,
                CaseStatus as caseStatus,
                FORMAT(StartTime, 'yyyy-MM-dd HH:mm:ss') as startTime,
                FORMAT(EndTime, 'yyyy-MM-dd HH:mm:ss') as endTime
            FROM VW_RPADashboard_New
            WHERE EndTime IS NOT NULL
              AND MachineName IS NOT NULL
              AND ProcessTransactionId IS NOT NULL
              AND CaseStatus IN ('SUCCESS', 'ERROR', 'EXCEPTION')
              AND CAST(CreatedDate AS DATE) = CAST(GETDATE() AS DATE)
            ORDER BY MachineName ASC, EndTime DESC
        """)

        results = db.execute(query).fetchall()

        # Group transactions by VM
        vm_transactions = {}
        for row in results:
            machine_name = row.machineName

            if machine_name not in vm_transactions:
                vm_transactions[machine_name] = []

            vm_transactions[machine_name].append({
                "transactionId": row.transactionId,
                "processName": row.processName,
                "caseStatus": row.caseStatus,
                "startTime": row.startTime,
                "endTime": row.endTime
            })

        # Sort VMs alphanumerically (VM1, VM2, VM10, not VM1, VM10, VM2)
        def extract_vm_number(name):
            match = re.search(r'\d+', name)
            return int(match.group()) if match else 0

        sorted_vms = sorted(vm_transactions.keys(), key=extract_vm_number)

        # Convert to list format with sorted VMs
        return [
            {
                "machineName": machine_name,
                "transactions": vm_transactions[machine_name]
            }
            for machine_name in sorted_vms
        ]

    except Exception as e:
        print(f"Error in get_vm_completed_transactions: {e}")
        return []
    


