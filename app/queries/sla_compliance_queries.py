from app.database.connection import PROD_TABLE


def get_sla_percentage_query(region_clause=""):
    return f"""
        SELECT
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
            {region_clause}
    """


def get_hourly_sla_query(region_clause=""):
    return f"""
        WITH top_subprocess AS (
            SELECT TOP 5 SubProcessName
            FROM {PROD_TABLE}
            WHERE EndTime IS NOT NULL
              AND CAST(EndTime AS DATE) = CAST(GETDATE() AS DATE)
              {region_clause}
            GROUP BY SubProcessName
            ORDER BY COUNT(*) DESC
        ),
        subprocess_sla AS (
            SELECT
                DATEPART(HOUR, EndTime) AS interval_start,
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
              {region_clause}
            GROUP BY
                DATEPART(HOUR, EndTime),
                SubProcessName
        )
        SELECT
            CONCAT(interval_start,'-',interval_start+1,' hrs') AS interval_range,
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


def get_two_hour_sla_query(region_clause=""):
    return f"""
        WITH today_data AS (
            SELECT
                SubProcessName,
                StartTime,
                EndTime,
                CaseStatus,
                TAT
            FROM {PROD_TABLE}
            WHERE EndTime IS NOT NULL
              AND CAST(EndTime AS DATE) = CAST(GETDATE() AS DATE)
              {region_clause}
        ),
        subprocess_sla_total AS (
            SELECT
                SubProcessName,
                ROUND(
                    SUM(CASE WHEN CaseStatus = 'Success' AND DATEDIFF(MINUTE, StartTime, EndTime) <= TAT THEN 1 ELSE 0 END)
                    * 100.0 / COUNT(*)
                ,2) AS today_sla
            FROM today_data
            GROUP BY SubProcessName
        ),
        top5_subprocess AS (
            SELECT TOP 5 SubProcessName
            FROM subprocess_sla_total
            ORDER BY today_sla DESC
        ),
        hourly_sla AS (
            SELECT
                SubProcessName,
                (DATEPART(HOUR, EndTime)/2)*2 AS interval_start,
                MIN(EndTime) AS FirstEndTime,
                MAX(EndTime) AS LastEndTime,
                ROUND(
                    SUM(CASE WHEN CaseStatus = 'Success' AND DATEDIFF(MINUTE, StartTime, EndTime) <= TAT THEN 1 ELSE 0 END)
                    * 100.0 / COUNT(*)
                ,2) AS sla_percentage
            FROM today_data
            WHERE SubProcessName IN (SELECT SubProcessName FROM top5_subprocess)
            GROUP BY SubProcessName, (DATEPART(HOUR, EndTime)/2)*2
        )
        SELECT
            CONCAT(interval_start,'-',interval_start+2,' hrs') AS interval_range,
            SubProcessName,
            FirstEndTime,
            LastEndTime,
            sla_percentage,
            ROUND(AVG(sla_percentage) OVER (PARTITION BY interval_start),2) AS avg_sla_interval
        FROM hourly_sla
        ORDER BY interval_start, SubProcessName
    """


def get_gauge_sla_query(region_clause=""):
    return f"""
        WITH top_subprocess AS (
            SELECT TOP 5 SubProcessName
            FROM {PROD_TABLE}
            WHERE EndTime IS NOT NULL
              AND CAST(EndTime AS DATE) = CAST(GETDATE() AS DATE)
              {region_clause}
            GROUP BY SubProcessName
            ORDER BY COUNT(*) DESC
        )
        SELECT
            SubProcessName,
            COUNT(*) AS total_transactions,
            SUM(CASE WHEN EndTime >= DATEADD(DAY,-7,GETDATE()) THEN 1 ELSE 0 END) AS weekly_count,
            SUM(CASE WHEN EndTime >= DATEADD(DAY,-30,GETDATE()) THEN 1 ELSE 0 END) AS monthly_count,
            ROUND(
                SUM(CASE
                        WHEN CAST(EndTime AS DATE) = CAST(GETDATE() AS DATE)
                             AND CaseStatus = 'Success'
                             AND DATEDIFF(MINUTE, StartTime, EndTime) <= TAT
                        THEN 1 ELSE 0 END
                ) * 100.0 /
                NULLIF(SUM(CASE WHEN CAST(EndTime AS DATE) = CAST(GETDATE() AS DATE) THEN 1 END), 0)
            ,2) AS today_sla,
            ROUND(
                SUM(CASE
                        WHEN EndTime >= DATEADD(DAY,-7,GETDATE())
                             AND CaseStatus = 'Success'
                             AND DATEDIFF(MINUTE, StartTime, EndTime) <= TAT
                        THEN 1 ELSE 0 END
                ) * 100.0 /
                NULLIF(SUM(CASE WHEN EndTime >= DATEADD(DAY,-7,GETDATE()) THEN 1 END), 0)
            ,2) AS weekly_sla,
            ROUND(
                SUM(CASE
                        WHEN EndTime >= DATEADD(DAY,-30,GETDATE())
                             AND CaseStatus = 'Success'
                             AND DATEDIFF(MINUTE, StartTime, EndTime) <= TAT
                        THEN 1 ELSE 0 END
                ) * 100.0 /
                NULLIF(SUM(CASE WHEN EndTime >= DATEADD(DAY,-30,GETDATE()) THEN 1 END), 0)
            ,2) AS monthly_sla
        FROM {PROD_TABLE}
        WHERE EndTime IS NOT NULL
          AND SubProcessName IN (SELECT SubProcessName FROM top_subprocess)
          {region_clause}
        GROUP BY SubProcessName
        ORDER BY SubProcessName
    """
