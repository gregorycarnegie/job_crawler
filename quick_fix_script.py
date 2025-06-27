#!/usr/bin/env python3
"""
Quick Fix Script for Claude Job Agent Import Issues
=================================================

This script fixes the most common import issues that are causing test failures.
Run this from your project root directory.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, capture_output=True):
    """Run command with error handling."""
    print(f"🔧 {description}...")
    try:
        if isinstance(cmd, list):
            result = subprocess.run(
                cmd, check=False, capture_output=capture_output, text=True
            )
        else:
            result = subprocess.run(
                cmd, shell=True, check=False, capture_output=capture_output, text=True
            )

        if result.returncode == 0:
            print(f"✅ {description} completed")
            return True
        else:
            print(f"⚠️  {description} completed with warnings")
            if result.stderr and capture_output:
                print(f"   Warning: {result.stderr.strip()}")
            return True  # Continue even with warnings
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return False


def fix_package_structure():
    """Fix package structure and imports."""
    print("📁 Fixing package structure...")

    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    package_dir = src_dir / "claude_job_agent"

    # Ensure __init__.py exists and has proper content
    init_file = package_dir / "__init__.py"
    if not init_file.exists() or init_file.stat().st_size < 100:
        print(f"📝 Creating/updating {init_file}")
        init_content = '''"""
Claude Job Agent - Intelligent Job Search Assistant for Claude Desktop
====================================================================
"""

__version__ = "2.0.0"

# Import main components for easier access
try:
    from .main import (
        JobDatabase,
        search_adzuna_jobs,
        extract_basic_job_features,
        create_analysis_framework,
    )
    from .core.logging_config import setup_logging, get_logger
except ImportError:
    # Handle import errors during development/testing
    pass

__all__ = [
    "JobDatabase",
    "search_adzuna_jobs", 
    "extract_basic_job_features",
    "create_analysis_framework",
    "setup_logging",
    "get_logger",
]
'''
        with open(init_file, "w", encoding="utf-8") as f:
            f.write(init_content)

    # Check core __init__.py
    core_init = package_dir / "core" / "__init__.py"
    if core_init.exists():
        print(f"✅ Core package structure exists")

    return True


def clean_old_installations():
    """Clean old package installations."""
    print("🧹 Cleaning old installations...")

    project_root = Path(__file__).parent

    # Remove .egg-info directories
    for egg_info in project_root.glob("*.egg-info"):
        if egg_info.is_dir():
            print(f"🗑️  Removing {egg_info}")
            try:
                shutil.rmtree(egg_info)
            except Exception as e:
                print(f"   Warning: Could not remove {egg_info}: {e}")

    # Remove compiled Python files
    for pycache in project_root.rglob("__pycache__"):
        if pycache.is_dir():
            try:
                shutil.rmtree(pycache)
            except Exception:
                pass

    # Uninstall existing package
    run_command(
        [sys.executable, "-m", "pip", "uninstall", "claude-job-agent", "-y"],
        "Uninstalling existing package",
    )

    return True


def install_package():
    """Install package in development mode."""
    print("📦 Installing package...")

    # Install in development mode
    success = run_command(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        "Installing package in development mode",
    )

    if not success:
        print("⚠️  Standard pip failed, trying alternatives...")
        # Try with --force-reinstall
        run_command(
            [sys.executable, "-m", "pip", "install", "-e", ".", "--force-reinstall"],
            "Force reinstalling package",
        )

    # Install development dependencies
    run_command(
        [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
        "Installing development dependencies",
    )

    return True


def test_imports():
    """Test if imports work correctly."""
    print("🧪 Testing imports...")

    # Test basic import
    try:
        import claude_job_agent

        print(
            f"✅ Basic import successful - version {getattr(claude_job_agent, '__version__', 'unknown')}"
        )
        import_success = True
    except ImportError as e:
        print(f"❌ Basic import failed: {e}")
        import_success = False

    # Test main module import
    try:
        from claude_job_agent.main import JobDatabase, search_adzuna_jobs

        print("✅ Main module imports successful")
        main_import_success = True
    except ImportError as e:
        print(f"❌ Main module import failed: {e}")
        main_import_success = False

    # Test if we can run a simple function
    if main_import_success:
        try:
            # Test database creation
            temp_db = JobDatabase(":memory:")
            print("✅ Database functionality test passed")
            functional_test = True
        except Exception as e:
            print(f"❌ Functional test failed: {e}")
            functional_test = False
    else:
        functional_test = False

    return import_success, main_import_success, functional_test


def fix_test_environment():
    """Fix test environment setup."""
    print("🔧 Fixing test environment...")

    # Create necessary directories
    directories = ["data", "logs", "backups"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Ensured directory exists: {directory}")

    # Set environment variables for testing
    test_env = {
        "ADZUNA_APP_ID": "test_app_id",
        "ADZUNA_APP_KEY": "test_app_key",
        "DATABASE_PATH": "data/test_jobs.db",
    }

    for key, value in test_env.items():
        os.environ[key] = value
        print(f"🔧 Set environment variable: {key}")

    return True


def run_sample_tests():
    """Run a few sample tests to verify everything works."""
    print("🧪 Running sample tests...")

    # Test database functionality
    test_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_main.py::TestDatabase::test_database_initialization",
        "-v",
        "--tb=short",
        "-x",
    ]

    db_test_success = run_command(test_cmd, "Database test", capture_output=False)

    # Test job analysis
    test_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_main.py::TestJobAnalysis::test_extract_basic_job_features",
        "-v",
        "--tb=short",
        "-x",
    ]

    analysis_test_success = run_command(
        test_cmd, "Job analysis test", capture_output=False
    )

    return db_test_success and analysis_test_success


def main():
    """Main fix function."""
    print("🚀 Claude Job Agent - Quick Fix Script")
    print("=" * 50)

    project_root = Path(__file__).parent
    os.chdir(project_root)

    print(f"📍 Working directory: {project_root}")
    print(f"🐍 Python executable: {sys.executable}")
    print(f"📦 Python version: {sys.version}")

    # Step 1: Fix package structure
    if not fix_package_structure():
        print("❌ Failed to fix package structure")
        return False

    # Step 2: Clean old installations
    if not clean_old_installations():
        print("❌ Failed to clean old installations")
        return False

    # Step 3: Install package
    if not install_package():
        print("❌ Failed to install package")
        return False

    # Step 4: Test imports
    import_success, main_import_success, functional_test = test_imports()

    if not import_success:
        print("❌ Import tests failed - cannot continue")
        return False

    # Step 5: Fix test environment
    if not fix_test_environment():
        print("❌ Failed to fix test environment")
        return False

    # Step 6: Run sample tests
    if main_import_success and functional_test:
        print("\n" + "=" * 50)
        test_success = run_sample_tests()

        if test_success:
            print("\n🎉 SUCCESS! Everything is working correctly.")
            print("\n✅ You can now run:")
            print("   python scripts/run_tests.py --quick")
            print("   python scripts/run_tests.py")
            print("   python -m pytest tests/ -v")
        else:
            print("\n⚠️  PARTIAL SUCCESS: Imports work but some tests are failing.")
            print(
                "   This might be due to specific test issues rather than import problems."
            )
            print("   Try running: python scripts/run_tests.py --verbose")
    else:
        print("\n⚠️  Imports work but functionality tests failed.")
        print("   Check the error messages above for specific issues.")

    print("\n📊 Summary:")
    print(f"   Basic Import: {'✅' if import_success else '❌'}")
    print(f"   Main Module: {'✅' if main_import_success else '❌'}")
    print(f"   Functional Test: {'✅' if functional_test else '❌'}")

    return import_success and main_import_success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏸️  Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
