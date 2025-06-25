# =============================================================================
# Performance Monitor
# =============================================================================

import logging
import sqlite3
from datetime import datetime
from typing import Any

from .health_checker import HealthChecker


class PerformanceMonitor:
    def __init__(self):
        self.health_checker = HealthChecker()
        self.logger = logging.getLogger("job_agent.performance")

    async def collect_system_metrics(self) -> dict[str, Any]:
        """Collect system performance metrics - FIXED VERSION."""
        try:
            # FIXED: Better psutil handling
            try:
                import psutil
            except ImportError:
                self.logger.warning("psutil not installed, skipping system metrics")
                return {"error": "psutil not available"}

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available / (1024**3)  # GB

            # Disk usage
            disk = psutil.disk_usage('.')
            disk_percent = disk.percent
            disk_free = disk.free / (1024**3)  # GB

            # Log metrics
            self.health_checker.log_performance_metric("cpu_percent", cpu_percent)
            self.health_checker.log_performance_metric("memory_percent", memory_percent)
            self.health_checker.log_performance_metric("disk_percent", disk_percent)

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_available_gb": memory_available,
                "disk_percent": disk_percent,
                "disk_free_gb": disk_free,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return {"error": str(e)}

    async def analyze_api_performance(self) -> dict[str, Any]:
        """Analyse API performance trends."""
        with sqlite3.connect(self.health_checker.metrics_db) as conn:
            cursor = conn.cursor()

            # Average response times by API
            cursor.execute('''
                SELECT api_name, AVG(response_time) as avg_response_time,
                       COUNT(*) as request_count,
                       SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
                FROM api_metrics
                WHERE timestamp > datetime('now', '-1 hour')
                GROUP BY api_name
            ''')

            api_performance = {}
            for row in cursor.fetchall():
                api_name, avg_response, request_count, error_count = row
                error_rate = error_count / request_count if request_count > 0 else 0

                api_performance[api_name] = {
                    "avg_response_time": avg_response,
                    "request_count": request_count,
                    "error_count": error_count,
                    "error_rate": error_rate,
                    "success_rate": 1 - error_rate
                }

            return api_performance

    async def get_health_summary(self) -> dict[str, Any]:
        """Get comprehensive health summary."""
        # Run health checks
        db_health = await self.health_checker.check_database_health()
        api_health = await self.health_checker.check_api_health()
        system_metrics = await self.collect_system_metrics()
        api_performance = await self.analyze_api_performance()

        # Determine overall status
        issues = []
        if db_health["status"] != "healthy":
            issues.append("Database connectivity issues")
        if api_health["status"] not in ["healthy", "degraded"]:
            issues.append("External API failures")

        overall_status = "healthy" if not issues else "degraded" if len(issues) == 1 else "unhealthy"

        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "issues": issues,
            "database": db_health,
            "apis": api_health,
            "system": system_metrics,
            "performance": api_performance
        }
