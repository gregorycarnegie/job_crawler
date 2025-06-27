# =============================================================================
# Health Check System
# =============================================================================

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

import httpx

from claude_job_agent.core.logging_config import get_logger


class HealthChecker:
    def __init__(self):
        self.logger = get_logger("monitoring.health")
        self.metrics_db = "data/metrics.db"
        self.init_metrics_db()

    def init_metrics_db(self):
        """Initialize metrics database."""
        Path("data").mkdir(exist_ok=True)

        with sqlite3.connect(self.metrics_db) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    check_type TEXT,
                    status TEXT,
                    response_time REAL,
                    details TEXT
                );

                CREATE TABLE IF NOT EXISTS api_metrics (
                    id INTEGER PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    api_name TEXT,
                    endpoint TEXT,
                    status_code INTEGER,
                    response_time REAL,
                    request_size INTEGER,
                    response_size INTEGER
                );

                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metric_name TEXT,
                    metric_value REAL,
                    context TEXT
                );

                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    error_type TEXT,
                    error_message TEXT,
                    stack_trace TEXT,
                    context TEXT
                );
            """
            )

    async def check_database_health(self) -> dict[str, Any]:
        """Check database connectivity and performance - FIXED VERSION."""
        start_time = time.time()

        try:
            db_path = os.getenv("DATABASE_PATH", "data/jobs.db")

            # CRITICAL FIX: Check if database file exists first
            if not Path(db_path).exists():
                response_time = time.time() - start_time
                status = {
                    "status": "unhealthy",
                    "response_time": response_time,
                    "error": "Database file not found",
                    "details": f"Database file does not exist: {db_path}",
                }
                self.log_health_check(
                    "database", "unhealthy", response_time, f"File not found: {db_path}"
                )
                return status

            with sqlite3.connect(db_path, timeout=5) as conn:
                cursor = conn.cursor()

                # Basic connectivity check
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

                if result is None or result[0] != 1:
                    raise sqlite3.Error("Connectivity test failed")

                # Check table existence
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                # Check record counts
                try:
                    cursor.execute("SELECT COUNT(*) FROM jobs")
                    job_count = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    job_count = 0

                try:
                    cursor.execute("SELECT COUNT(*) FROM applications")
                    app_count = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    app_count = 0

                response_time = time.time() - start_time

                status = {
                    "status": "healthy",
                    "response_time": response_time,
                    "tables": len(tables),
                    "job_count": job_count,
                    "application_count": app_count,
                    "details": f"Database responsive in {response_time:.2f}s",
                }

                self.log_health_check(
                    "database", "healthy", response_time, json.dumps(status)
                )
                return status

        except Exception as e:
            response_time = time.time() - start_time
            status = {
                "status": "unhealthy",
                "response_time": response_time,
                "error": str(e),
                "details": f"Database check failed: {e}",
            }

            self.log_health_check("database", "unhealthy", response_time, str(e))
            return status

    async def check_api_health(self) -> dict[str, Any]:
        """Check external API connectivity."""
        # Check Adzuna API
        adzuna_status = await self.check_adzuna_api()
        api_checks = {"adzuna": adzuna_status}

        # Overall API health
        healthy_apis = sum(
            status["status"] == "healthy" for status in api_checks.values()
        )
        overall_status = "healthy" if healthy_apis == len(api_checks) else "degraded"

        return {
            "status": overall_status,
            "apis": api_checks,
            "healthy_count": healthy_apis,
            "total_count": len(api_checks),
        }

    async def check_adzuna_api(self) -> dict[str, Any]:
        """Check Adzuna API connectivity."""
        start_time = time.time()

        app_id = os.getenv("ADZUNA_APP_ID")
        app_key = os.getenv("ADZUNA_APP_KEY")

        if not app_id or not app_key:
            return {
                "status": "unconfigured",
                "response_time": 0,
                "details": "API credentials not configured",
            }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.adzuna.com/v1/api/jobs/gb/search/1",
                    params={
                        "app_id": app_id,
                        "app_key": app_key,
                        "results_per_page": 1,
                        "what": "test",
                    },
                )

                response_time = time.time() - start_time

                if response.status_code == 200:
                    self.log_api_metric(
                        "adzuna", "search", 200, response_time, 0, len(response.content)
                    )
                    return {
                        "status": "healthy",
                        "response_time": response_time,
                        "details": f"API responsive in {response_time:.2f}s",
                    }
                else:
                    self.log_api_metric(
                        "adzuna", "search", response.status_code, response_time, 0, 0
                    )
                    return {
                        "status": "unhealthy",
                        "response_time": response_time,
                        "status_code": response.status_code,
                        "details": f"API returned status {response.status_code}",
                    }

        except Exception as e:
            response_time = time.time() - start_time
            self.log_error("adzuna_api_check", str(e), "", "health_check")
            return {
                "status": "unhealthy",
                "response_time": response_time,
                "error": str(e),
                "details": f"API check failed: {e}",
            }

    def log_health_check(
        self, check_type: str, status: str, response_time: float, details: str
    ):
        """Log health check result."""
        try:
            self.safe_db_execute(
                """
                INSERT INTO health_checks (check_type, status, response_time, details)
                VALUES (?, ?, ?, ?)
            """,
                (check_type, status, response_time, details),
            )
        except Exception as e:
            # Log error but don't fail the health check
            self.logger.warning("Failed to log health check to database: %s", e)

    def log_api_metric(
        self,
        api_name: str,
        endpoint: str,
        status_code: int,
        response_time: float,
        request_size: int,
        response_size: int,
    ):
        """Log API usage metrics."""
        try:
            self.safe_db_execute(
                """
                INSERT INTO api_metrics (api_name, endpoint, status_code, response_time, request_size, response_size)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    api_name,
                    endpoint,
                    status_code,
                    response_time,
                    request_size,
                    response_size,
                ),
            )
        except Exception as e:
            # Log error but don't fail the health check
            self.logger.warning("Failed to log API metric: %s", e)

    def log_performance_metric(
        self, metric_name: str, metric_value: float, context: str = ""
    ):
        """Log performance metrics."""
        try:
            self.safe_db_execute(
                """
                INSERT INTO performance_metrics (metric_name, metric_value, context)
                VALUES (?, ?, ?)
            """,
                (metric_name, metric_value, context),
            )
        except Exception as e:
            # Log error but don't fail the health check
            self.logger.warning("Failed to log performance metric: %s", e)

    def log_error(
        self, error_type: str, error_message: str, stack_trace: str, context: str = ""
    ):
        """Log error information."""
        try:
            self.safe_db_execute(
                """
                INSERT INTO error_logs (error_type, error_message, stack_trace, context)
                VALUES (?, ?, ?, ?)
            """,
                (error_type, error_message, stack_trace, context),
            )
        except Exception as e:
            # Log error but don't fail the health check
            self.logger.warning("Failed to log error to database: %s", e)

    def safe_db_execute(self, query, params=None, fetch=None):
        """Safely execute database query with proper connection handling."""
        conn = sqlite3.connect(self.metrics_db)
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch == "one":
                result = cursor.fetchone()
            elif fetch == "all":
                result = cursor.fetchall()
            else:
                result = None

            conn.commit()
            return result
        finally:
            conn.close()
