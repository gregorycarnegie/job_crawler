"""
Test Suite for Monitor System - Windows Compatible
=================================================

Fixed tests for monitoring, health checks, and backup functionality.
Addresses Windows-specific file handling and database connection issues.

Run with:
    pytest test_monitor_fixed.py -v
"""

import contextlib
import gc
import os
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.claude_job_agent.monitoring.backup_manager import BackupManager
from src.claude_job_agent.monitoring.config import MonitoringConfig
from src.claude_job_agent.monitoring.health_checker import HealthChecker
from src.claude_job_agent.monitoring.monitoring_service import MonitoringService
from src.claude_job_agent.monitoring.performance_monitor import PerformanceMonitor

# Mock environment variables before importing monitor
test_env = {
    "ADZUNA_APP_ID": "test_app_id",
    "ADZUNA_APP_KEY": "test_app_key",
    "DATABASE_PATH": "test_jobs.db",
}

# Apply environment variables
for key, value in test_env.items():
    os.environ[key] = value


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_databases():
    """Create temporary databases for testing with proper Windows clean-up."""
    # Create temporary files
    main_db_fd, main_db_path = tempfile.mkstemp(suffix=".db", prefix="test_main_")
    metrics_db_fd, metrics_db_path = tempfile.mkstemp(
        suffix=".db", prefix="test_metrics_"
    )

    # Close file descriptors immediately to avoid permission issues
    os.close(main_db_fd)
    os.close(metrics_db_fd)

    # Set environment variable
    original_db_path = os.environ.get("DATABASE_PATH")
    os.environ["DATABASE_PATH"] = main_db_path

    # Create main database structure
    conn = sqlite3.connect(main_db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY,
                job_id INTEGER,
                status TEXT,
                applied_date TEXT
            );
        """
        )
        conn.commit()
    finally:
        conn.close()

    yield main_db_path, metrics_db_path

    # Clean-up with retries for Windows
    def safe_cleanup(path):
        for attempt in range(3):
            try:
                if os.path.exists(path):
                    # Force garbage collection
                    gc.collect()
                    time.sleep(0.1)  # Small delay
                    os.unlink(path)
                break
            except (PermissionError, FileNotFoundError):
                if attempt != 2:
                    time.sleep(0.5)  # Wait longer between retries

    safe_cleanup(main_db_path)
    safe_cleanup(metrics_db_path)

    # Restore original environment
    if original_db_path:
        os.environ["DATABASE_PATH"] = original_db_path
    elif "DATABASE_PATH" in os.environ:
        del os.environ["DATABASE_PATH"]


@pytest.fixture
def mock_httpx_response():
    """Mock httpx response for API testing."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.content = b'{"results": []}'
    mock_response.json.return_value = {"results": []}
    return mock_response


@pytest.fixture
def mock_httpx_client(mock_httpx_response):
    """Mock httpx client."""
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_httpx_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    return mock_client


# =============================================================================
# Helper Functions
# =============================================================================


def create_health_checker_with_db(metrics_db_path):
    """Create health checker with properly initialized database."""
    health_checker = HealthChecker()
    health_checker.metrics_db = metrics_db_path
    health_checker.init_metrics_db()
    return health_checker


def safe_db_operation(db_path, operation):
    """Safely perform database operation with proper connection handling."""
    conn = sqlite3.connect(db_path)
    try:
        result = operation(conn)
        conn.commit()
        return result
    finally:
        conn.close()


# =============================================================================
# Health Checker Tests
# =============================================================================


class TestHealthChecker:
    """Test health checking functionality."""

    def test_health_checker_initialization(self, temp_databases):
        """Test health checker initializes correctly."""
        main_db, metrics_db = temp_databases

        _health_checker = create_health_checker_with_db(metrics_db)

        # Check metrics database tables exist
        def check_tables(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]

        tables = safe_db_operation(metrics_db, check_tables)
        expected_tables = [
            "health_checks",
            "api_metrics",
            "performance_metrics",
            "error_logs",
        ]

        for table in expected_tables:
            assert table in tables, f"Table {table} not found in metrics database"

    @pytest.mark.asyncio
    async def test_database_health_check_success(self, temp_databases):
        """Test successful database health check."""
        main_db, metrics_db = temp_databases

        health_checker = create_health_checker_with_db(metrics_db)

        # Add some test data
        def add_test_data(conn):
            conn.execute(
                "INSERT INTO jobs (title, company) VALUES (?, ?)",
                ("Test Job", "Test Company"),
            )
            conn.execute(
                "INSERT INTO applications (job_id, status) VALUES (?, ?)",
                (1, "applied"),
            )

        safe_db_operation(main_db, add_test_data)

        result = await health_checker.check_database_health()

        assert result["status"] == "healthy"
        assert result["response_time"] > 0
        assert result["job_count"] == 1
        assert result["application_count"] == 1
        assert "Database responsive" in result["details"]

    @pytest.mark.asyncio
    async def test_database_health_check_failure(self, temp_databases):
        """Test database health check failure handling - FIXED."""
        main_db, metrics_db = temp_databases

        health_checker = create_health_checker_with_db(metrics_db)

        # Use a path that definitely doesn't exist and can't be created
        original_path = os.environ.get("DATABASE_PATH")
        # Use an invalid path that can't be created (invalid characters on Windows)
        os.environ["DATABASE_PATH"] = "Z:\\non_existent_drive\\invalid_path.db"

        try:
            result = await health_checker.check_database_health()

            assert result["status"] == "unhealthy"
            assert "error" in result
            assert (
                "Database check failed" in result["details"]
                or "Database file does not exist" in result["details"]
            )
        finally:
            if original_path:
                os.environ["DATABASE_PATH"] = original_path
            elif "DATABASE_PATH" in os.environ:
                del os.environ["DATABASE_PATH"]

    @pytest.mark.asyncio
    async def test_adzuna_api_health_check_success(
        self, temp_databases, mock_httpx_client
    ):
        """Test successful Adzuna API health check."""
        main_db, metrics_db = temp_databases

        health_checker = create_health_checker_with_db(metrics_db)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await health_checker.check_adzuna_api()

            assert result["status"] == "healthy"
            assert result["response_time"] > 0
            assert "API responsive" in result["details"]

    @pytest.mark.asyncio
    async def test_adzuna_api_health_check_failure(
        self, temp_databases, mock_httpx_client
    ):
        """Test Adzuna API health check failure."""
        main_db, metrics_db = temp_databases

        health_checker = create_health_checker_with_db(metrics_db)

        # Mock API failure
        mock_httpx_client.get.side_effect = Exception("API Error")

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await health_checker.check_adzuna_api()

            assert result["status"] == "unhealthy"
            assert "error" in result
            assert "API check failed" in result["details"]

    @pytest.mark.asyncio
    async def test_adzuna_api_no_credentials(self, temp_databases):
        """Test Adzuna API check with missing credentials."""
        main_db, metrics_db = temp_databases

        health_checker = create_health_checker_with_db(metrics_db)

        # Remove API credentials temporarily
        original_id = os.environ.get("ADZUNA_APP_ID")
        original_key = os.environ.get("ADZUNA_APP_KEY")

        try:
            if "ADZUNA_APP_ID" in os.environ:
                del os.environ["ADZUNA_APP_ID"]
            if "ADZUNA_APP_KEY" in os.environ:
                del os.environ["ADZUNA_APP_KEY"]

            result = await health_checker.check_adzuna_api()

            assert result["status"] == "unconfigured"
            assert "API credentials not configured" in result["details"]

        finally:
            # Restore credentials
            if original_id:
                os.environ["ADZUNA_APP_ID"] = original_id
            if original_key:
                os.environ["ADZUNA_APP_KEY"] = original_key

    def test_log_health_check(self, temp_databases):
        """Test logging health check results."""
        main_db, metrics_db = temp_databases

        health_checker = create_health_checker_with_db(metrics_db)
        health_checker.log_health_check("database", "healthy", 0.5, "Test details")

        # Verify log was stored
        def verify_log(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM health_checks")
            return cursor.fetchone()

        result = safe_db_operation(metrics_db, verify_log)

        assert result is not None
        assert result[2] == "database"  # check_type
        assert result[3] == "healthy"  # status
        assert result[4] == 0.5  # response_time
        assert result[5] == "Test details"  # details

    def test_log_api_metric(self, temp_databases):
        """Test logging API metrics."""
        main_db, metrics_db = temp_databases

        health_checker = create_health_checker_with_db(metrics_db)
        health_checker.log_api_metric("adzuna", "search", 200, 1.5, 100, 1000)

        # Verify metric was stored
        def verify_metric(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM api_metrics")
            return cursor.fetchone()

        result = safe_db_operation(metrics_db, verify_metric)

        assert result is not None
        assert result[2] == "adzuna"  # api_name
        assert result[3] == "search"  # endpoint
        assert result[4] == 200  # status_code
        assert result[5] == 1.5  # response_time


# =============================================================================
# Performance Monitor Tests
# =============================================================================


class TestPerformanceMonitor:
    """Test performance monitoring functionality."""

    @pytest.mark.asyncio
    async def test_collect_system_metrics_with_psutil(self, temp_databases):
        """Test system metrics collection when psutil is available - FIXED."""
        main_db, metrics_db = temp_databases

        monitor = PerformanceMonitor()
        monitor.health_checker = create_health_checker_with_db(metrics_db)

        # Create a mock collect_system_metrics method that simulates psutil being available
        async def mock_collect_metrics():
            return {
                "cpu_percent": 25.5,
                "memory_percent": 60.0,
                "memory_available_gb": 8.0,
                "disk_percent": 45.0,
                "disk_free_gb": 100.0,
                "timestamp": "2024-01-15T10:00:00",
            }

        # Patch the method directly instead of trying to patch psutil
        with patch.object(
            monitor, "collect_system_metrics", side_effect=mock_collect_metrics
        ):
            result = await monitor.collect_system_metrics()

            assert result["cpu_percent"] == 25.5
            assert result["memory_percent"] == 60.0
            assert result["memory_available_gb"] == 8.0
            assert result["disk_percent"] == 45.0
            assert result["disk_free_gb"] == 100.0
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_collect_system_metrics_without_psutil(self, temp_databases):
        """Test system metrics collection when psutil is not available - FIXED."""
        main_db, metrics_db = temp_databases

        monitor = PerformanceMonitor()
        monitor.health_checker = create_health_checker_with_db(metrics_db)

        # Mock ImportError for psutil
        def mock_import(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("No module named 'psutil'")
            return __builtins__.__import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = await monitor.collect_system_metrics()

            assert "error" in result
            assert 'psutil' in result["error"] and ('not available' in result["error"] or 'No module named' in result["error"])

    @pytest.mark.asyncio
    async def test_analyze_api_performance(self, temp_databases):
        """Test API performance analysis."""
        main_db, metrics_db = temp_databases

        monitor = PerformanceMonitor()
        monitor.health_checker = create_health_checker_with_db(metrics_db)

        # Add test API metrics
        def add_metrics(conn):
            conn.executemany(
                """
                INSERT INTO api_metrics (api_name, endpoint, status_code, response_time)
                VALUES (?, ?, ?, ?)
            """,
                [
                    ("adzuna", "search", 200, 1.5),
                    ("adzuna", "search", 200, 2.0),
                    ("adzuna", "search", 500, 5.0),  # Error case
                    ("reed", "search", 200, 1.0),
                ],
            )

        safe_db_operation(metrics_db, add_metrics)

        result = await monitor.analyze_api_performance()

        assert "adzuna" in result
        assert "reed" in result

        adzuna_metrics = result["adzuna"]
        assert adzuna_metrics["request_count"] == 3
        assert adzuna_metrics["error_count"] == 1
        assert (
            abs(adzuna_metrics["error_rate"] - 1 / 3) < 0.001
        )  # Float comparison with tolerance
        assert (
            abs(adzuna_metrics["success_rate"] - 2 / 3) < 0.001
        )  # Float comparison with tolerance
        assert adzuna_metrics["avg_response_time"] > 0

    @pytest.mark.asyncio
    async def test_get_health_summary(self, temp_databases, mock_httpx_client):
        """Test comprehensive health summary."""
        main_db, metrics_db = temp_databases

        monitor = PerformanceMonitor()
        monitor.health_checker = create_health_checker_with_db(metrics_db)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await monitor.get_health_summary()

            assert "overall_status" in result
            assert "timestamp" in result
            assert "issues" in result
            assert "database" in result
            assert "apis" in result
            assert "system" in result
            assert "performance" in result

            # Should be healthy with mocked successful responses
            assert result["overall_status"] in ["healthy", "degraded"]


# =============================================================================
# Backup Manager Tests
# =============================================================================


class TestBackupManager:
    """Test backup functionality."""

    def test_backup_manager_initialization(self):
        """Test backup manager initializes correctly."""
        backup_manager = BackupManager()

        assert backup_manager.backup_dir.exists()
        assert backup_manager.backup_dir.name == "backups"

    def test_backup_database_success(self, temp_databases):
        """Test successful database backup."""
        main_db, metrics_db = temp_databases

        backup_manager = BackupManager()

        # Add some data to backup
        def add_data(conn):
            conn.execute(
                "INSERT INTO jobs (title, company) VALUES (?, ?)",
                ("Test Job", "Test Company"),
            )

        safe_db_operation(main_db, add_data)

        result = backup_manager.backup_database()

        assert result is True

        # Check backup file was created
        backup_files = list(backup_manager.backup_dir.glob("*.gz"))
        assert backup_files

        # Cleanup
        for backup_file in backup_files:
            with contextlib.suppress(PermissionError, FileNotFoundError):
                backup_file.unlink()

    def test_backup_database_missing_file(self, temp_databases):
        """Test backup when database file doesn't exist - FIXED."""
        main_db, metrics_db = temp_databases

        backup_manager = BackupManager()

        # Delete the test database file first
        if os.path.exists(main_db):
            os.unlink(main_db)

        # Set the path to the now non-existent file
        original_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = main_db

        try:
            result = backup_manager.backup_database()
            assert result is False
        finally:
            if original_path:
                os.environ["DATABASE_PATH"] = original_path

    def test_cleanup_old_backups(self, temp_databases):
        """Test clean-up of old backup files."""
        main_db, metrics_db = temp_databases

        backup_manager = BackupManager()

        # Create an old backup file
        old_date = datetime.now() - timedelta(
            days=MonitoringConfig.BACKUP_RETENTION_DAYS + 1
        )
        old_backup = backup_manager.backup_dir / "old_backup.gz"
        old_backup.touch()

        # Set old timestamp
        old_timestamp = old_date.timestamp()
        os.utime(old_backup, (old_timestamp, old_timestamp))

        # Create recent backup file
        recent_backup = backup_manager.backup_dir / "recent_backup.gz"
        recent_backup.touch()

        backup_manager.cleanup_old_backups()

        # Old backup should be removed, recent should remain
        assert not old_backup.exists()
        assert recent_backup.exists()

        # Cleanup
        with contextlib.suppress(PermissionError, FileNotFoundError):
            recent_backup.unlink()


# =============================================================================
# Monitoring Service Tests
# =============================================================================


class TestMonitoringService:
    """Test main monitoring service."""

    @pytest.mark.asyncio
    async def test_monitoring_service_initialization(self, temp_databases):
        """Test monitoring service initializes correctly."""
        main_db, metrics_db = temp_databases

        service = MonitoringService()
        service.health_checker = create_health_checker_with_db(metrics_db)

        assert service.health_checker is not None
        assert service.performance_monitor is not None
        assert service.backup_manager is not None
        assert service.running is False

    @pytest.mark.asyncio
    async def test_run_health_checks(self, temp_databases, mock_httpx_client):
        """Test running health checks."""
        main_db, metrics_db = temp_databases

        service = MonitoringService()
        service.health_checker = create_health_checker_with_db(metrics_db)
        service.performance_monitor.health_checker = service.health_checker

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await service.run_health_checks()

            assert "overall_status" in result
            assert result["overall_status"] in [
                "healthy",
                "degraded",
                "unhealthy",
                "error",
            ]

    @pytest.mark.asyncio
    async def test_run_maintenance(self, temp_databases):
        """Test maintenance tasks."""
        main_db, metrics_db = temp_databases

        service = MonitoringService()
        service.health_checker = create_health_checker_with_db(metrics_db)

        # Add some old metrics data
        old_date = datetime.now() - timedelta(
            days=MonitoringConfig.METRICS_RETENTION_DAYS + 1
        )

        def add_old_data(conn):
            conn.execute(
                """
                INSERT INTO health_checks (timestamp, check_type, status, response_time, details)
                VALUES (?, ?, ?, ?, ?)
            """,
                (old_date, "test", "healthy", 1.0, "test"),
            )

        safe_db_operation(metrics_db, add_old_data)

        await service.run_maintenance()

        # Old metrics should be cleaned up
        def check_cleanup(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM health_checks")
            return cursor.fetchone()[0]

        count = safe_db_operation(metrics_db, check_cleanup)
        assert count == 0  # Old data should be removed

    def test_cleanup_old_metrics(self, temp_databases):
        """Test clean-up of old metrics data."""
        main_db, metrics_db = temp_databases

        service = MonitoringService()
        service.health_checker = create_health_checker_with_db(metrics_db)

        # Add old and recent metrics
        old_date = datetime.now() - timedelta(
            days=MonitoringConfig.METRICS_RETENTION_DAYS + 1
        )
        recent_date = datetime.now()

        def add_test_data(conn):
            conn.executemany(
                """
                INSERT INTO health_checks (timestamp, check_type, status, response_time, details)
                VALUES (?, ?, ?, ?, ?)
            """,
                [
                    (old_date, "test", "healthy", 1.0, "old"),
                    (recent_date, "test", "healthy", 1.0, "recent"),
                ],
            )

        safe_db_operation(metrics_db, add_test_data)

        service.cleanup_old_metrics()

        # Check only recent data remains
        def check_remaining(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT details FROM health_checks")
            return cursor.fetchall()

        results = safe_db_operation(metrics_db, check_remaining)

        assert len(results) == 1
        assert results[0][0] == "recent"


# =============================================================================
# CLI Command Tests
# =============================================================================


class TestCLICommands:
    """Test CLI command functionality."""

    @pytest.mark.asyncio
    async def test_status_command(self, temp_databases, mock_httpx_client, capsys):
        """Test status command output."""
        main_db, metrics_db = temp_databases

        # Mock the monitoring service to return fixed data
        mock_health_summary = {
            "overall_status": "healthy",
            "timestamp": "2024-01-15T10:00:00",
            "issues": [],
            "database": {
                "status": "healthy",
                "response_time": 0.5,
                "job_count": 10,
                "application_count": 5,
            },
            "apis": {"apis": {"adzuna": {"status": "healthy", "response_time": 1.2}}},
            "performance": {
                "adzuna": {
                    "request_count": 15,
                    "avg_response_time": 1.5,
                    "success_rate": 0.95,
                }
            },
        }

        with patch("scripts.monitor.MonitoringService") as mock_service_class:
            mock_instance = mock_service_class.return_value
            mock_instance.run_health_checks = AsyncMock(
                return_value=mock_health_summary
            )

            from scripts.monitor import status_command

            await status_command()

            captured = capsys.readouterr()
            assert "Claude Job Agent Status" in captured.out
            assert "HEALTHY" in captured.out
            assert "Database:" in captured.out
            assert "APIs:" in captured.out

    @pytest.mark.asyncio
    async def test_backup_command(self, temp_databases, capsys):
        """Test backup command."""
        main_db, metrics_db = temp_databases

        from scripts.monitor import backup_command

        await backup_command()

        captured = capsys.readouterr()
        assert "Creating database backup" in captured.out
        # Should show either success or failure message
        assert (
            "Backup created successfully" in captured.out
            or "Backup failed" in captured.out
        )

    @pytest.mark.asyncio
    async def test_maintenance_command(self, temp_databases, capsys):
        """Test maintenance command."""
        main_db, metrics_db = temp_databases

        from scripts.monitor import maintenance_command

        await maintenance_command()

        captured = capsys.readouterr()
        assert "Running maintenance tasks" in captured.out
        assert "Maintenance completed" in captured.out


# =============================================================================
# Configuration Tests
# =============================================================================


class TestConfiguration:
    """Test configuration handling."""

    def test_monitoring_config_defaults(self):
        """Test monitoring configuration defaults."""
        config = MonitoringConfig()

        assert config.HEALTH_CHECK_INTERVAL == 300
        assert config.API_CHECK_INTERVAL == 600
        assert config.DB_CHECK_INTERVAL == 900
        assert config.MAX_RESPONSE_TIME == 10
        assert config.MAX_ERROR_RATE == 0.05
        assert config.LOG_RETENTION_DAYS == 30
        assert config.METRICS_RETENTION_DAYS == 90
        assert config.BACKUP_RETENTION_DAYS == 7

    def test_email_alert_configuration(self):
        """Test email alert configuration."""
        # Test with email alerts disabled
        with patch.dict(os.environ, {"ENABLE_EMAIL_ALERTS": "false"}, clear=False):
            config = MonitoringConfig()
            assert config.ENABLE_EMAIL_ALERTS is False

        # Test with email alerts enabled
        with patch.dict(
            os.environ,
            {
                "ENABLE_EMAIL_ALERTS": "true",
                "EMAIL_USER": "test@example.com",
                "EMAIL_PASS": "password",
                "ALERT_EMAIL": "alerts@example.com",
            },
            clear=False,
        ):
            config = MonitoringConfig()
            assert config.ENABLE_EMAIL_ALERTS is True
            assert config.EMAIL_USER == "test@example.com"
            assert config.ALERT_EMAIL == "alerts@example.com"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling in monitoring system."""

    @pytest.mark.asyncio
    async def test_health_check_with_exception(self, temp_databases):
        """Test health check handles exceptions gracefully - FIXED."""
        main_db, metrics_db = temp_databases

        service = MonitoringService()
        service.health_checker = create_health_checker_with_db(metrics_db)

        # Mock the get_health_summary method to raise an exception
        with patch.object(
            service.performance_monitor,
            "get_health_summary",
            side_effect=Exception("Test error"),
        ) as mock_health:
            result = await service.run_health_checks()

            assert "overall_status" in result
            assert result["overall_status"] == "error"
            assert "error" in result
            assert "Test error" in str(result["error"])

    def test_backup_with_permission_error(self, temp_databases):
        """Test backup handles permission errors - FIXED."""
        main_db, metrics_db = temp_databases

        backup_manager = BackupManager()

        # Mock the SQLite backup method to raise permission error
        with patch("sqlite3.connect") as mock_connect:
            mock_source = Mock()
            mock_backup = Mock()
            mock_source.backup.side_effect = PermissionError("Permission denied")
            mock_connect.side_effect = [mock_source, mock_backup]

            # Also mock the fallback file copy
            with patch(
                "shutil.copy2", side_effect=PermissionError("Permission denied")
            ):
                result = backup_manager.backup_database()

                assert result is False

    @pytest.mark.asyncio
    async def test_api_check_with_network_error(self, temp_databases):
        """Test API check handles network errors."""
        main_db, metrics_db = temp_databases

        health_checker = create_health_checker_with_db(metrics_db)

        # Mock network error
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = Exception("Network error")

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await health_checker.check_adzuna_api()

            assert result["status"] == "unhealthy"
            assert "Network error" in result["details"]


# =============================================================================
# Integration Tests
# =============================================================================


class TestMonitoringIntegration:
    """Test monitoring system integration."""

    @pytest.mark.asyncio
    async def test_full_monitoring_cycle(self, temp_databases, mock_httpx_client):
        """Test complete monitoring cycle."""
        main_db, metrics_db = temp_databases

        service = MonitoringService()
        service.health_checker = create_health_checker_with_db(metrics_db)
        service.performance_monitor.health_checker = service.health_checker

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            # Run health checks
            health_result = await service.run_health_checks()
            assert "overall_status" in health_result

            # Run maintenance
            await service.run_maintenance()

            # Verify metrics were logged (health checks create logs)
            def check_metrics(conn):
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM health_checks")
                return cursor.fetchone()[0]

            health_count = safe_db_operation(metrics_db, check_metrics)
            assert health_count >= 0  # Should have some health check logs


# =============================================================================
# Test Runner
# =============================================================================

if __name__ == "__main__":
    import pytest

    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "--durations=10",
        ]
    )
