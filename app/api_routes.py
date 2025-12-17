# app/api_routes.py
"""
REST API routes for KPI metrics
Provides fallback HTTP endpoints that return the same data as the WebSocket stream
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from app.schemas import MetricsResponse, MetricsData, ErrorResponse
from app.crud import get_metrics
from datetime import datetime, timezone
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(
    prefix="/api/v1",
    tags=["metrics"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current KPI Metrics",
    description="""
    Retrieve the current KPI metrics for the queue dashboard.

    This endpoint provides the same data delivered through the WebSocket stream,
    making it suitable as a fallback when WebSocket connections are not available
    or for clients that prefer REST API polling.

    **Metrics included:**
    - `errors`: Number of cases with ERROR status
    - `exceptions`: Number of cases with EXCEPTION status
    - `successful`: Number of cases with SUCCESS status
    - `inProgress`: Number of cases currently in progress (ProcessStatus = 'NEW')
    - `totalInQueue`: Total number of cases waiting in queue
    - `avgTime`: Average processing time in minutes for successful cases
    """
)
async def get_kpi_metrics():
    """
    Get current KPI metrics from the database.

    Returns:
        MetricsResponse: Structured response with metrics data and metadata
    """
    try:
        # Fetch metrics from database
        metrics_dict = get_metrics()

        # Validate and construct response
        metrics_data = MetricsData(**metrics_dict)

        response = MetricsResponse(
            success=True,
            timestamp=datetime.now(timezone.utc),
            data=metrics_data
        )

        return response

    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}", exc_info=True)

        # Return error response with fallback zero values
        error_response = ErrorResponse(
            success=False,
            timestamp=datetime.now(timezone.utc),
            error=f"Failed to retrieve metrics: {str(e)}",
            data=MetricsData(
                errors=0,
                exceptions=0,
                successful=0,
                inProgress=0,
                totalInQueue=0,
                avgTime=0
            )
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(mode='json')
        )


@router.get(
    "/metrics/health",
    status_code=status.HTTP_200_OK,
    summary="Health Check for Metrics API",
    description="Check if the metrics API is operational and can connect to the database"
)
async def health_check():
    """
    Perform a health check by attempting to fetch metrics.

    Returns:
        dict: Health status information
    """
    try:
        # Attempt to fetch metrics to verify database connectivity
        get_metrics()

        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc),
            "service": "metrics-api"
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "metrics-api",
                "error": str(e)
            }
        )


@router.get(
    "/metrics/raw",
    status_code=status.HTTP_200_OK,
    summary="Get Raw Metrics Data (Legacy Format)",
    description="""
    Get metrics in the original format without wrapper metadata.

    This endpoint maintains backward compatibility with existing clients
    that expect the simple JSON object format.
    """
)
async def get_raw_metrics():
    """
    Get metrics data in raw format without response wrapper.

    Returns:
        dict: Raw metrics dictionary
    """
    try:
        metrics_dict = get_metrics()
        return metrics_dict

    except Exception as e:
        logger.error(f"Error fetching raw metrics: {str(e)}", exc_info=True)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "errors": 0,
                "exceptions": 0,
                "successful": 0,
                "inProgress": 0,
                "totalInQueue": 0,
                "avgTime": 0,
                "error": str(e)
            }
        )
