from app.database.connection import PROD_TABLE


def get_process_analysis_query():
    return f"""
        SELECT TOP 5
            SubProcessName,
            COUNT(*) AS ErrorCount,
            CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER() AS DECIMAL(5,2)) AS ErrorPercentage
        FROM {PROD_TABLE}
        WHERE CaseStatus IN ('Error','Exception')
            AND CAST(ENDTIME AS DATE) = CAST(GETDATE() AS DATE)
        GROUP BY SubProcessName
        ORDER BY ErrorCount DESC
    """
