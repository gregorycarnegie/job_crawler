#!/usr/bin/env python3
"""
Claude Job Agent - Monitoring & Health Checks
=============================================

Lightweight monitoring system for the Claude Desktop Job Agent.
No external AI API dependencies - focuses on system health and performance.

Features:
- Health checks for database and APIs
- Performance metrics tracking
- Error logging and alerting
- Automated backups
- Log rotation
- Application statistics

Usage:
    python monitor.py status    # Show current status
    python monitor.py monitor   # Start monitoring service
    python monitor.py backup    # Create database backup
    python monitor.py cleanup   # Run maintenance tasks
"""

import argparse
import asyncio
import logging
from pathlib import Path

from src.claude_job_agent.monitoring.backup_manager import BackupManager
from src.claude_job_agent.monitoring.monitoring_service import MonitoringService

# =============================================================================
# Logging Setup
# =============================================================================


def setup_logging():
    """Configure comprehensive logging."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Main application logger
    app_logger = logging.getLogger("job_agent")
    app_logger.setLevel(logging.INFO)

    # File handler for all logs
    app_handler = logging.FileHandler(log_dir / "job_agent.log")
    app_handler.setFormatter(detailed_formatter)
    app_logger.addHandler(app_handler)

    # Error logger
    error_logger = logging.getLogger("job_agent.errors")
    error_handler = logging.FileHandler(log_dir / "errors.log")
    error_handler.setFormatter(detailed_formatter)
    error_handler.setLevel(logging.ERROR)
    error_logger.addHandler(error_handler)

    # Performance logger
    perf_logger = logging.getLogger("job_agent.performance")
    perf_handler = logging.FileHandler(log_dir / "performance.log")
    perf_handler.setFormatter(detailed_formatter)
    perf_logger.addHandler(perf_handler)

    # API usage logger
    api_logger = logging.getLogger("job_agent.api")
    api_handler = logging.FileHandler(log_dir / "api_usage.log")
    api_handler.setFormatter(detailed_formatter)
    api_logger.addHandler(api_handler)

    return app_logger, error_logger, perf_logger, api_logger


# =============================================================================
# CLI Commands
# =============================================================================


async def status_command():
    """Show current system status."""
    monitor = MonitoringService()
    health_summary = await monitor.run_health_checks()

    print("🔍 Claude Job Agent Status")
    print("=" * 40)
    print(f"Overall Status: {health_summary['overall_status'].upper()}")
    print(f"Timestamp: {health_summary['timestamp']}")

    if health_summary.get("issues"):
        print("\n⚠️  Issues:")
        for issue in health_summary["issues"]:
            print(f"  - {issue}")

    print("\n📊 Database:")
    db = health_summary.get("database", {})
    print(f"  Status: {db.get('status', 'unknown')}")
    print(f"  Response Time: {db.get('response_time', 0):.2f}s")
    print(f"  Jobs: {db.get('job_count', 0)}")
    print(f"  Applications: {db.get('application_count', 0)}")

    print("\n🌐 APIs:")
    apis = health_summary.get("apis", {}).get("apis", {})
    for api_name, api_status in apis.items():
        status_icon = "✅" if api_status["status"] == "healthy" else "❌"
        print(
            f"  {status_icon} {api_name}: {api_status['status']} ({api_status.get('response_time', 0):.2f}s)"
        )

    if performance := health_summary.get("performance", {}):
        print("\n📈 Performance (last hour):")
        for api_name, metrics in performance.items():
            print(f"  {api_name}:")
            print(f"    Requests: {metrics.get('request_count', 0)}")
            print(f"    Avg Response: {metrics.get('avg_response_time', 0):.2f}s")
            print(f"    Success Rate: {metrics.get('success_rate', 0):.1%}")


async def monitor_command():
    """Start monitoring service."""
    print("🚀 Starting Claude Job Agent Monitoring Service")

    # Setup logging
    setup_logging()

    # Start monitoring
    monitor = MonitoringService()

    try:
        await monitor.monitoring_loop()
    except KeyboardInterrupt:
        print("\n🛑 Monitoring service stopped")
    finally:
        monitor.stop()


async def backup_command():
    """Create database backup."""
    print("💾 Creating database backup...")
    backup_manager = BackupManager()

    if backup_manager.backup_database():
        print("✅ Backup created successfully")
    else:
        print("❌ Backup failed")


async def maintenance_command():
    """Run maintenance tasks."""
    print("🔧 Running maintenance tasks...")
    monitor = MonitoringService()
    await monitor.run_maintenance()
    print("✅ Maintenance completed")


def main():
    """Main CLI entry point."""

    parser = argparse.ArgumentParser(description="Claude Job Agent Operations")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    subparsers.add_parser("status", help="Show system status")

    # Monitor command
    subparsers.add_parser("monitor", help="Start monitoring service")

    # Backup command
    subparsers.add_parser("backup", help="Create database backup")

    # Maintenance command
    subparsers.add_parser("maintenance", help="Run maintenance tasks")

    args = parser.parse_args()

    if args.command == "status":
        asyncio.run(status_command())
    elif args.command == "monitor":
        asyncio.run(monitor_command())
    elif args.command == "backup":
        asyncio.run(backup_command())
    elif args.command == "maintenance":
        asyncio.run(maintenance_command())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
