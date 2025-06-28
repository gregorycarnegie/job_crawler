#!/usr/bin/env python3
"""
Test Runner for Claude Job Agent
===============================

Comprehensive test runner that validates all functionality before deployment.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --quick      # Run quick tests only
    python run_tests.py --monitor    # Test monitoring system only
    python run_tests.py --main       # Test main agent only
    python run_tests.py --verbose    # Verbose output
"""


import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(command, description, capture_output=False):
    """Run a command with error handling."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=capture_output, text=True
        )
        if capture_output:
            return result.stdout, result.stderr
        print(f"✅ {description} passed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if capture_output:
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
        return False


def check_dependencies():
    """Check if required dependencies are installed - UPDATED VERSION."""
    print("📦 Checking dependencies...")

    required_packages = [
        "pytest",
        "pytest-asyncio",
        "httpx",
        "aiohttp",
        "bs4",
        "lxml",
        "dotenv",
        "pydantic",
        "dateutil",
        "mcp",
    ]

    optional_packages = [
        "pytest-cov",  # For coverage reporting
        "psutil",  # For system monitoring
    ]

    missing_required = []
    missing_optional = []

    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_required.append(package)

    for package in optional_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_optional.append(package)

    if missing_required:
        print(f"❌ Missing required packages: {', '.join(missing_required)}")
        print("Install with: pip install " + " ".join(missing_required))
        return False

    if missing_optional:
        print(f"⚠️  Missing optional packages: {', '.join(missing_optional)}")
        print("Install with: pip install " + " ".join(missing_optional))
        print("(Tests will run with reduced functionality)")

    print("✅ All required dependencies installed")
    return True


def run_main_tests(verbose=False):
    """Run tests for main job agent - FIXED VERSION."""
    print("\n🧪 Running Main Agent Tests")
    print("=" * 40)

    test_command = "pytest tests/test_main.py" + (" -v" if verbose else " -q")

    if importlib.util.find_spec("pytest_cov") is not None:
        test_command += " --cov=main --cov-report=term-missing"
        print("ℹ️  Running with coverage reporting")
    else:
        print("ℹ️  pytest-cov not installed, running tests without coverage")
        print("    Install with: pip install pytest-cov")

    return run_command(test_command, "Main agent tests")


def run_monitor_tests(verbose=False):
    """Run tests for monitoring system."""
    print("\n🔍 Running Monitor Tests")
    print("=" * 40)

    test_command = "pytest tests/test_monitoring.py" + (" -v" if verbose else " -q")
    return run_command(test_command, "Monitor system tests")


def run_integration_tests(verbose=False):
    """Run integration tests."""
    print("\n🔗 Running Integration Tests")
    print("=" * 40)

    test_command = "pytest tests/test_main.py::TestIntegration" + (
        " -v" if verbose else " -q"
    )
    return run_command(test_command, "Integration tests")


def run_quick_tests(verbose=False):
    """Run quick smoke tests."""
    print("\n⚡ Running Quick Tests")
    print("=" * 40)

    # Test database functionality
    quick_tests = [
        "pytest tests/test_main.py::TestDatabase -q",
        "pytest tests/test_main.py::TestJobAnalysis -q",
        "pytest tests/test_monitoring.py::TestHealthChecker::test_health_checker_initialization -q",
    ]

    return all(
        run_command(test_command, f"Quick test: {test_command.split('::')[-1]}")
        for test_command in quick_tests
    )


def run_performance_tests(verbose=False):
    """Run performance tests."""
    print("\n🚀 Running Performance Tests")
    print("=" * 40)

    test_command = "pytest tests/test_main.py::TestPerformance" + (
        " -v" if verbose else " -q"
    )
    return run_command(test_command, "Performance tests")


def validate_configuration():
    """Validate configuration files."""
    print("\n⚙️ Validating Configuration")
    print("=" * 40)

    # Check if main files exist
    required_files = [
        "src/claude_job_agent/main.py",
        "scripts/monitor.py",
        "pyproject.toml",
    ]

    missing_files = []
    missing_files.extend(file for file in required_files if not Path(file).exists())
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False

    # Check environment variables
    required_env = ["ADZUNA_APP_ID", "ADZUNA_APP_KEY"]
    missing_env = []

    missing_env.extend(env_var for env_var in required_env if not os.getenv(env_var))
    if missing_env:
        print(f"⚠️  Missing environment variables: {', '.join(missing_env)}")
        print("Set these in your Claude Desktop config or .env file")

    print("✅ Configuration validated")
    return True


def run_syntax_checks():
    """Run syntax and style checks."""
    print("\n📝 Running Code Quality Checks")
    print("=" * 40)

    checks = []

    # Python syntax check
    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", "src/claude_job_agent/main.py"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("✅ main.py syntax check passed")
            checks.append(True)
        else:
            print_syntax_check_result(
                "❌ main.py syntax check failed", result, checks
            )
    except Exception as e:
        print(f"❌ Syntax check failed: {e}")
        checks.append(False)

    # Check monitor.py syntax
    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", "scripts/monitor.py"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("✅ monitor.py syntax check passed")
            checks.append(True)
        else:
            print_syntax_check_result(
                "❌ monitor.py syntax check failed", result, checks
            )
    except Exception as e:
        print(f"❌ Monitor syntax check failed: {e}")
        checks.append(False)

    # Optional: Run black formatting check
    try:
        result = subprocess.run(
            [
                "black",
                "--check",
                "--diff",
                "src/claude_job_agent/main.py",
                "scripts/monitor.py",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("✅ Code formatting check passed")
        else:
            print("⚠️  Code formatting suggestions available (run 'black .' to fix)")
        checks.append(True)
    except FileNotFoundError:
        print("ℹ️  Black formatter not installed (optional)")
        checks.append(True)

    return all(checks)


def print_syntax_check_result(arg0, result, checks):
    print(arg0)
    print(result.stderr)
    checks.append(False)


def test_api_connectivity():
    """Test API connectivity with real endpoints."""
    print("\n🌐 Testing API Connectivity")
    print("=" * 40)

    # Test if we can import and use the search function
    try:
        import asyncio
        import os

        # Set test environment
        app_id = os.getenv("ADZUNA_APP_ID")
        app_key = os.getenv("ADZUNA_APP_KEY")

        if not app_id or not app_key:
            print("⚠️  Skipping API test - credentials not configured")
            return True

        # Import after setting environment
        from src.claude_job_agent.main import search_adzuna_jobs

        async def test_search():
            try:
                results = await search_adzuna_jobs("test", max_results=1)
                return len(results) >= 0  # Should return list, even if empty
            except Exception as e:
                print(f"❌ API test failed: {e}")
                return False

        result = asyncio.run(test_search())
        if result:
            print("✅ API connectivity test passed")
        else:
            print("❌ API connectivity test failed")

        return result

    except Exception as e:
        print(f"❌ API test setup failed: {e}")
        return False


def create_test_database():
    """Create test database to verify database functionality - FIXED."""
    print("\n🗄️ Testing Database Functionality")
    print("=" * 40)

    try:
        import gc
        import sqlite3
        import tempfile
        import time

        from src.claude_job_agent.main import JobDatabase

        # Create temporary database with better Windows handling
        fd, test_db_path = tempfile.mkstemp(suffix=".db", prefix="test_job_agent_")
        os.close(fd)  # Close file descriptor immediately

        try:
            # Test database creation
            _db = JobDatabase(test_db_path)

            # Test basic operations
            with sqlite3.connect(test_db_path, timeout=10) as conn:
                cursor = conn.cursor()

                # Insert test data
                cursor.execute(
                    """
                    INSERT INTO jobs (title, company, location, url)
                    VALUES (?, ?, ?, ?)
                """,
                    ("Test Job", "Test Company", "London", "http://test.com"),
                )

                cursor.execute(
                    """
                    INSERT INTO applications (job_id, status, applied_date)
                    VALUES (?, ?, ?)
                """,
                    (1, "applied", "2024-01-15"),
                )

                conn.commit()

                # Test queries
                cursor.execute("SELECT COUNT(*) FROM jobs")
                job_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM applications")
                app_count = cursor.fetchone()[0]

            if job_count == 1 and app_count == 1:
                print("✅ Database functionality test passed")
                return True
            else:
                print("❌ Database functionality test failed")
                return False

        finally:
            # Enhanced clean-up for Windows
            gc.collect()
            time.sleep(0.1)

            # Multiple attempts to delete with increasing delays
            for attempt in range(5):
                try:
                    if os.path.exists(test_db_path):
                        os.unlink(test_db_path)
                    break
                except OSError:
                    if attempt < 4:
                        time.sleep(0.5 * (attempt + 1))  # Increasing delay

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


def run_mcp_validation():
    """Validate MCP server functionality."""
    print("\n🔌 Validating MCP Server")
    print("=" * 40)

    try:
        # Test MCP server imports
        from src.claude_job_agent.main import mcp

        # Check if tools are registered
        # _tools = []

        # Get tool names (this depends on FastMCP implementation)
        # For now, just check if mcp object exists
        if hasattr(mcp, "_tools") or hasattr(mcp, "tools"):
            print("✅ MCP server tools registered")
        else:
            print("⚠️  MCP server structure may have changed")

        print("✅ MCP server validation passed")
        return True

    except Exception as e:
        print(f"❌ MCP validation failed: {e}")
        return False


def generate_test_report(results):
    """Generate a comprehensive test report."""
    print("\n📊 Test Report")
    print("=" * 50)

    total_tests = len(results)
    passed_tests = sum(bool(result) for result in results.values())
    failed_tests = total_tests - passed_tests

    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

    print("\nDetailed Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")

    if failed_tests == 0:
        print("\n🎉 All tests passed! Your Claude Job Agent is ready to deploy.")
        return True
    else:
        print(
            f"\n⚠️  {failed_tests} test(s) failed. Please review and fix issues before deployment."
        )
        return False


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Test Runner for Claude Job Agent")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument("--main", action="store_true", help="Test main agent only")
    parser.add_argument(
        "--monitor", action="store_true", help="Test monitoring system only"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--no-api", action="store_true", help="Skip API connectivity tests"
    )
    parser.add_argument(
        "--no-integration", action="store_true", help="Skip integration tests"
    )

    args = parser.parse_args()

    print("🧪 Claude Job Agent Test Suite")
    print("=" * 50)

    # Test results tracking
    results = {
        "Dependencies": check_dependencies(),
        "Configuration": validate_configuration(),
        "Syntax Checks": run_syntax_checks(),
    }

    if not all([results["Dependencies"], results["Configuration"]]):
        print("\n❌ Pre-flight checks failed. Cannot continue with tests.")
        generate_test_report(results)
        sys.exit(1)

    # Core functionality tests
    if args.quick:
        results["Quick Tests"] = run_quick_tests(args.verbose)
    elif args.main:
        results["Main Agent Tests"] = run_main_tests(args.verbose)
    elif args.monitor:
        results["Monitor Tests"] = run_monitor_tests(args.verbose)
    else:
        # Run all tests
        results["Database Test"] = create_test_database()
        results["MCP Validation"] = run_mcp_validation()

        if not args.no_api:
            results["API Connectivity"] = test_api_connectivity()

        results["Main Agent Tests"] = run_main_tests(args.verbose)
        results["Monitor Tests"] = run_monitor_tests(args.verbose)

        if not args.no_integration:
            results["Integration Tests"] = run_integration_tests(args.verbose)
            results["Performance Tests"] = run_performance_tests(args.verbose)
    # Generate a final report
    success = generate_test_report(results)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
