# tests/test_api_routes.py
"""
Unit tests for the REST API metrics endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Import the FastAPI app
from app.main import app

# Create test client
client = TestClient(app)


class TestMetricsEndpoint:
    """Test suite for /api/v1/metrics endpoint"""

    @patch('app.api_routes.get_metrics')
    def test_get_metrics_success(self, mock_get_metrics):
        """Test successful metrics retrieval"""
        # Mock the database response
        mock_get_metrics.return_value = {
            "errors": 5,
            "exceptions": 2,
            "successful": 150,
            "inProgress": 10,
            "totalInQueue": 10,
            "avgTime": 45
        }

        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "timestamp" in data
        assert "data" in data

        metrics = data["data"]
        assert metrics["errors"] == 5
        assert metrics["exceptions"] == 2
        assert metrics["successful"] == 150
        assert metrics["inProgress"] == 10
        assert metrics["totalInQueue"] == 10
        assert metrics["avgTime"] == 45

    @patch('app.api_routes.get_metrics')
    def test_get_metrics_database_error(self, mock_get_metrics):
        """Test metrics endpoint when database fails"""
        mock_get_metrics.side_effect = Exception("Database connection failed")

        response = client.get("/api/v1/metrics")

        assert response.status_code == 500
        data = response.json()

        assert data["success"] is False
        assert "error" in data
        assert "Database connection failed" in data["error"]
        assert data["data"]["errors"] == 0
        assert data["data"]["exceptions"] == 0

    @patch('app.api_routes.get_metrics')
    def test_get_metrics_with_zeros(self, mock_get_metrics):
        """Test metrics endpoint with zero values"""
        mock_get_metrics.return_value = {
            "errors": 0,
            "exceptions": 0,
            "successful": 0,
            "inProgress": 0,
            "totalInQueue": 0,
            "avgTime": 0
        }

        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert all(value == 0 for value in data["data"].values())


class TestRawMetricsEndpoint:
    """Test suite for /api/v1/metrics/raw endpoint"""

    @patch('app.api_routes.get_metrics')
    def test_get_raw_metrics_success(self, mock_get_metrics):
        """Test raw metrics endpoint returns simple format"""
        mock_get_metrics.return_value = {
            "errors": 5,
            "exceptions": 2,
            "successful": 150,
            "inProgress": 10,
            "totalInQueue": 10,
            "avgTime": 45
        }

        response = client.get("/api/v1/metrics/raw")

        assert response.status_code == 200
        data = response.json()

        # Should return raw format without wrapper
        assert "success" not in data
        assert "timestamp" not in data
        assert data["errors"] == 5
        assert data["successful"] == 150

    @patch('app.api_routes.get_metrics')
    def test_get_raw_metrics_error(self, mock_get_metrics):
        """Test raw metrics endpoint error handling"""
        mock_get_metrics.side_effect = Exception("Database error")

        response = client.get("/api/v1/metrics/raw")

        assert response.status_code == 500
        data = response.json()

        assert "error" in data
        assert data["errors"] == 0


class TestHealthCheckEndpoint:
    """Test suite for /api/v1/metrics/health endpoint"""

    @patch('app.api_routes.get_metrics')
    def test_health_check_healthy(self, mock_get_metrics):
        """Test health check when service is healthy"""
        mock_get_metrics.return_value = {
            "errors": 5,
            "exceptions": 2,
            "successful": 150,
            "inProgress": 10,
            "totalInQueue": 10,
            "avgTime": 45
        }

        response = client.get("/api/v1/metrics/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "metrics-api"
        assert "timestamp" in data

    @patch('app.api_routes.get_metrics')
    def test_health_check_unhealthy(self, mock_get_metrics):
        """Test health check when service is unhealthy"""
        mock_get_metrics.side_effect = Exception("Database connection failed")

        response = client.get("/api/v1/metrics/health")

        assert response.status_code == 503
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["service"] == "metrics-api"
        assert "error" in data
        assert "Database connection failed" in data["error"]


class TestLegacyEndpoint:
    """Test suite for legacy /api/metrics endpoint"""

    @patch('app.crud.get_metrics')
    def test_legacy_metrics_endpoint(self, mock_get_metrics):
        """Test legacy endpoint maintains backward compatibility"""
        mock_get_metrics.return_value = {
            "errors": 5,
            "exceptions": 2,
            "successful": 150,
            "inProgress": 10,
            "totalInQueue": 10,
            "avgTime": 45
        }

        response = client.get("/api/metrics")

        assert response.status_code == 200
        data = response.json()

        # Legacy format - no wrapper
        assert data["errors"] == 5
        assert data["successful"] == 150


class TestRootEndpoint:
    """Test suite for root endpoint"""

    def test_root_endpoint(self):
        """Test root endpoint returns API info"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "version" in data
        assert "endpoints" in data

        endpoints = data["endpoints"]
        assert "/api/v1/metrics" in endpoints["metrics"]
        assert "/api/v1/metrics/health" in endpoints["metrics_health"]
        assert "/api/v1/metrics/raw" in endpoints["metrics_raw"]
        assert "/ws/metrics" in endpoints["websocket"]


class TestResponseStructure:
    """Test suite for response structure validation"""

    @patch('app.api_routes.get_metrics')
    def test_metrics_response_has_required_fields(self, mock_get_metrics):
        """Test that response has all required fields"""
        mock_get_metrics.return_value = {
            "errors": 1,
            "exceptions": 1,
            "successful": 1,
            "inProgress": 1,
            "totalInQueue": 1,
            "avgTime": 1
        }

        response = client.get("/api/v1/metrics")
        data = response.json()

        # Check top-level structure
        assert "success" in data
        assert "timestamp" in data
        assert "data" in data

        # Check data structure
        metrics = data["data"]
        required_fields = ["errors", "exceptions", "successful", "inProgress", "totalInQueue", "avgTime"]
        for field in required_fields:
            assert field in metrics, f"Missing required field: {field}"

    @patch('app.api_routes.get_metrics')
    def test_metrics_values_are_non_negative(self, mock_get_metrics):
        """Test that all metric values are non-negative integers"""
        mock_get_metrics.return_value = {
            "errors": 5,
            "exceptions": 2,
            "successful": 150,
            "inProgress": 10,
            "totalInQueue": 10,
            "avgTime": 45
        }

        response = client.get("/api/v1/metrics")
        data = response.json()

        metrics = data["data"]
        for key, value in metrics.items():
            assert isinstance(value, int), f"{key} should be an integer"
            assert value >= 0, f"{key} should be non-negative"


# Run with: python -m pytest tests/test_api_routes.py -v
