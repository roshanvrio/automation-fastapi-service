from app.database.connection import PROD_TABLE


def get_case_reasons_query():
    return f"""
        SELECT TOP 5
            CaseReason,
            COUNT(*) AS ErrorCount,
            CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER() AS DECIMAL(5,2)) AS ErrorPercentage
        FROM {PROD_TABLE}
        WHERE CaseStatus IN ('Error','Exception')
            AND CAST(EndTime AS DATE) = CAST(GETDATE() AS DATE)
        GROUP BY CaseReason
        ORDER BY ErrorCount DESC
    """
