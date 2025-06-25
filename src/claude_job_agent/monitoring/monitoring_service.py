# =============================================================================
# Main Monitoring Service
# =============================================================================

import asyncio
import gzip
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .backup_manager import BackupManager
from .config import MonitoringConfig
from .health_checker import HealthChecker
from .performance_monitor import PerformanceMonitor


class MonitoringService:
    def __init__(self):
        self.health_checker = HealthChecker()
        self.performance_monitor = PerformanceMonitor()
        self.backup_manager = BackupManager()
        self.logger = logging.getLogger("job_agent.monitor")
        self.running = False

    async def run_health_checks(self):
        """Run comprehensive health checks."""
        try:
            health_summary = await self.performance_monitor.get_health_summary()

            # Log health status
            self.logger.info(f"Health check completed: {health_summary['overall_status']}")

            return health_summary

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"overall_status": "error", "error": str(e)}

    async def monitoring_loop(self):
        """Main monitoring loop."""
        self.logger.info("Starting monitoring service")
        self.running = True

        while self.running:
            try:
                # Run health checks
                await self.run_health_checks()

                # Wait for next check
                await asyncio.sleep(MonitoringConfig.HEALTH_CHECK_INTERVAL)

            except KeyboardInterrupt:
                self.logger.info("Monitoring service interrupted")
                break
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry

    def stop(self):
        """Stop monitoring service."""
        self.running = False

    async def run_maintenance(self):
        """Run maintenance tasks."""
        self.logger.info("Running maintenance tasks")

        # Create database backup
        self.backup_manager.backup_database()

        # Clean-up old backups
        self.backup_manager.cleanup_old_backups()

        # Clean-up old metrics
        self.cleanup_old_metrics()

        # Rotate logs
        self.rotate_logs()

    def cleanup_old_metrics(self):
        """Remove old metric data."""
        try:
            cutoff_date = datetime.now() - timedelta(days=MonitoringConfig.METRICS_RETENTION_DAYS)

            with sqlite3.connect(self.health_checker.metrics_db) as conn:
                self._extracted_from_cleanup_old_metrics_7(conn, cutoff_date)
            self.logger.info("Old metrics cleaned up")

        except Exception as e:
            self.logger.error(f"Metrics cleanup failed: {e}")

    # TODO Rename this here and in `cleanup_old_metrics`
    @staticmethod
    def _extracted_from_cleanup_old_metrics_7(conn, cutoff_date):
        conn.execute("DELETE FROM health_checks WHERE timestamp < ?", (cutoff_date,))
        conn.execute("DELETE FROM api_metrics WHERE timestamp < ?", (cutoff_date,))
        conn.execute("DELETE FROM performance_metrics WHERE timestamp < ?", (cutoff_date,))

        # Keep error logs for longer
        error_cutoff = datetime.now() - timedelta(days=MonitoringConfig.METRICS_RETENTION_DAYS * 2)
        conn.execute("DELETE FROM error_logs WHERE timestamp < ?", (error_cutoff,))

        conn.commit()

    def rotate_logs(self):
        """Rotate log files."""
        try:
            log_dir = Path("logs")
            if not log_dir.exists():
                return

            cutoff_date = datetime.now() - timedelta(days=MonitoringConfig.LOG_RETENTION_DAYS)

            for log_file in log_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    # Compress old log file
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                            f_in.seek(0)
                            f_out.write(f_in.read())

                    # Remove original
                    log_file.unlink()
                    self.logger.info(f"Rotated log file: {log_file}")

        except Exception as e:
            self.logger.error(f"Log rotation failed: {e}")
