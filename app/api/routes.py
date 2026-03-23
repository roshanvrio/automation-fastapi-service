import asyncio
from fastapi import APIRouter, HTTPException, Query
from app.database.connection import async_execute
from app.queries.header_queries import get_header
from app.queries.country_queries import get_country
from app.queries.case_reason_queries import get_case_reasons_query
from app.queries.process_analysis_queries import get_process_analysis_query
from app.queries.vm_queries import get_vm_utilization_query
from app.queries.sla_compliance_queries import (
    get_sla_percentage_query,
    get_hourly_sla_query,
    get_two_hour_sla_query,
    get_gauge_sla_query,
)
from app.functions.region_filter import apply_region_filter, build_region_clause, get_region_params

router = APIRouter()


@router.get("/api/header")
async def api_header():
    try:
        return {"data": await get_header()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/country")
async def api_country():
    try:
        return await get_country()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/summary")
async def api_summary(region: str = Query(None)):
    try:
        params = get_region_params(region)
        rc = build_region_clause(region)

        (case_reasons, process_analysis, vm_utilization,
         sla_pct, sla_hourly, sla_two_hour, sla_gauge) = await asyncio.gather(
            async_execute(apply_region_filter(get_case_reasons_query(), region), params),
            async_execute(apply_region_filter(get_process_analysis_query(), region), params),
            async_execute(apply_region_filter(get_vm_utilization_query(), region), params),
            async_execute(get_sla_percentage_query(rc), params),
            async_execute(get_hourly_sla_query(rc), params),
            async_execute(get_two_hour_sla_query(rc), params),
            async_execute(get_gauge_sla_query(rc), params),
        )

        return {
            "case_reasons": case_reasons,
            "process_analysis": process_analysis,
            "vm_utilization": vm_utilization,
            "sla_compliance": {
                "percentage": sla_pct,
                "hourly": sla_hourly,
                "two_hour": sla_two_hour,
                "gauge": sla_gauge,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
