import asyncio
from app.database.connection import async_execute, PROD_TABLE


async def get_total_completed():
    query = f"""
        SELECT COUNT(*) AS TotalCompleted
        FROM {PROD_TABLE}
        WHERE ProcessStatus IN ('COMPLETED', 'FAILED')
            AND EndTime >= CAST(GETDATE() AS DATE)
            AND EndTime < DATEADD(DAY, 1, CAST(GETDATE() AS DATE))
    """
    return await async_execute(query)


async def get_sla_percentage():
    query = f"""
        SELECT
            CAST(
                ROUND(
                    (COUNT(CASE WHEN DATEDIFF(MINUTE, StartTime, EndTime) <= TAT THEN 1 END) * 100.0 / COUNT(*)),
                    2
                ) AS DECIMAL(5,2)
            ) AS SLA_Percentage
        FROM {PROD_TABLE}
        WHERE CaseStatus = 'SUCCESS'
            AND EndTime >= CAST(GETDATE() AS DATE)
            AND EndTime < DATEADD(DAY, 1, CAST(GETDATE() AS DATE))
    """
    return await async_execute(query)


async def get_sla_bar_graph():
    query = f"""
        WITH top_subprocess AS (
            SELECT TOP 5 SubProcessName
            FROM {PROD_TABLE}
            WHERE EndTime IS NOT NULL
              AND CAST(EndTime AS DATE) = CAST(GETDATE() AS DATE)
            GROUP BY SubProcessName
            ORDER BY COUNT(*) DESC
        ),
        subprocess_sla AS (
            SELECT
                (DATEPART(HOUR, EndTime)/2)*2 AS interval_start,
                SubProcessName,
                MIN(EndTime) AS FirstEndTime,
                MAX(EndTime) AS LastEndTime,
                ROUND(
                    SUM(
                        CASE
                            WHEN CaseStatus = 'Success'
                            AND DATEDIFF(MINUTE, StartTime, EndTime) <= TAT
                            THEN 1 ELSE 0
                        END
                    ) * 100.0 / COUNT(*)
                ,2) AS sla_percentage
            FROM {PROD_TABLE}
            WHERE EndTime IS NOT NULL
              AND CAST(EndTime AS DATE) = CAST(GETDATE() AS DATE)
              AND SubProcessName IN (SELECT SubProcessName FROM top_subprocess)
            GROUP BY
                (DATEPART(HOUR, EndTime)/2)*2,
                SubProcessName
        )
        SELECT
            CONCAT(interval_start,'-',interval_start+2,' hrs') AS interval_range,
            SubProcessName,
            FirstEndTime,
            LastEndTime,
            sla_percentage,
            ROUND(
                AVG(sla_percentage) OVER (PARTITION BY interval_start)
            ,2) AS avg_sla_interval
        FROM subprocess_sla
        ORDER BY interval_start, SubProcessName
    """
    return await async_execute(query)


async def get_subprocess_wise():
    query = f"""
        SELECT TOP (5)
            SubProcessName,
            DATEADD(HOUR, DATEDIFF(HOUR, 0, EndTime)/2*2, 0) AS TwoHourIntervalStart,
            COUNT(*) AS TotalCompleted,
            COUNT(CASE WHEN DATEDIFF(MINUTE, StartTime, EndTime) <= TAT THEN 1 END) AS CompletedWithinTAT,
            CAST(
                ROUND(
                    (COUNT(CASE WHEN DATEDIFF(MINUTE, StartTime, EndTime) <= TAT THEN 1 END) * 100.0 / COUNT(*)),
                    2
                ) AS DECIMAL(5,2)
            ) AS SLA_Percentage
        FROM {PROD_TABLE}
        WHERE CaseStatus = 'SUCCESS'
            AND CAST(EndTime AS DATE) = CAST(GETDATE() AS DATE)
        GROUP BY
            SubProcessName,
            DATEADD(HOUR, DATEDIFF(HOUR, 0, EndTime)/2*2, 0)
        ORDER BY
            TwoHourIntervalStart,
            SubProcessName
    """
    return await async_execute(query)


async def get_header():
    total_completed, sla_percentage, sla_bar_graph, subprocess_wise = await asyncio.gather(
        get_total_completed(),
        get_sla_percentage(),
        get_sla_bar_graph(),
        get_subprocess_wise(),
    )

    return {
        "total_completed": total_completed,
        "sla_percentage": sla_percentage,
        "sla_bar_graph": sla_bar_graph,
        "subprocess_wise": subprocess_wise,
    }
