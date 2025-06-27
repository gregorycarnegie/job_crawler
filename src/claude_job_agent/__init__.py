"""
Claude Job Agent - Intelligent Job Search Assistant for Claude Desktop
====================================================================
"""

import contextlib

__version__ = "2.0.0"

# Import main components for easier access
with contextlib.suppress(ImportError):
    from .core.logging_config import get_logger, setup_logging
    from .main import (
        JobDatabase,
        create_analysis_framework,
        extract_basic_job_features,
        search_adzuna_jobs,
    )
__all__ = [
    "JobDatabase",
    "search_adzuna_jobs",
    "extract_basic_job_features",
    "create_analysis_framework",
    "setup_logging",
    "get_logger",
]
