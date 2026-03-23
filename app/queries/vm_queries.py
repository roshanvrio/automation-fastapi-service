from app.database.connection import PROD_TABLE


def get_vm_utilization_query():
    return f"""
        SELECT TOP 5
            CASE
                WHEN MachineName LIKE '%.BOT'
                THEN LEFT(MachineName, LEN(MachineName)-4)
                ELSE MachineName
            END AS machineName,
            COUNT(*) AS ErrorCount,
            CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER() AS DECIMAL(5,2)) AS ErrorPercentage
        FROM {PROD_TABLE}
        WHERE CaseStatus IN ('Error','Exception')
            AND CAST(ENDTIME AS DATE) = CAST(GETDATE() AS DATE)
        GROUP BY machineName
        ORDER BY ErrorCount DESC
    """
