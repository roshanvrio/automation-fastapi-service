from app.database.connection import async_execute, PROD_TABLE


async def get_country():
    query = f"""
        SELECT DISTINCT region
        FROM {PROD_TABLE}
        WHERE ProcessStatus IN ('SUCCESS', 'FAILED')
            AND CAST(EndTime AS DATE) = CAST(GETDATE() AS DATE)
    """
    return await async_execute(query)
