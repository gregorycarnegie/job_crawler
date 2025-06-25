"""
Claude Desktop Optimized Job Search Agent - FIXED VERSION
=========================================================

Fixed version that addresses Claude Desktop compatibility issues:
1. Proper MCP server initialization
2. Error handling for database operations
3. Windows path compatibility
4. Async/await consistency
5. Tool parameter validation

Features:
- Multi-source job aggregation
- Structured data extraction for Claude analysis
- Smart compatibility frameworks
- Application assistance templates
- Career planning frameworks
- All powered by Claude Desktop's built-in AI
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

# Try to import MCP with proper error handling
try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    print(f"Error importing MCP: {e}")
    print("Please ensure MCP is installed: pip install mcp")
    sys.exit(1)

# Load environment variables
load_dotenv()

# =============================================================================
# Data Models (No AI API dependencies)
# =============================================================================

@dataclass
class UserProfile:
    skills: list[dict[str, Any]]
    experience_years: int
    current_role: str
    target_roles: list[str]
    salary_expectation: int | None
    location_preference: str
    remote_preference: str
    industry_preferences: list[str]
    company_size_preference: str

@dataclass
class JobAnalysisFramework:
    """Framework for Claude to analyze jobs consistently."""
    job_title: str
    job_description: str
    company: str
    analysis_prompts: dict[str, str]
    scoring_criteria: dict[str, list[str]]

@dataclass
class EnhancedJob:
    # Basic job info
    title: str
    company: str
    location: str
    salary_min: int | None
    salary_max: int | None
    contract_type: str
    url: str
    description: str
    posted_date: str
    source: str

    # Analysis framework for Claude
    analysis_framework: JobAnalysisFramework | None = None
    raw_requirements: list[str] | None = None
    benefits_mentioned: list[str] | None = None
    tech_stack: list[str] | None = None

# =============================================================================
# Database Setup (Lightweight)
# =============================================================================

class JobDatabase:
    def __init__(self, db_path: str = None):
        # Use environment variable or default path
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", "data/jobs.db")

        self.db_path = str(Path(db_path).resolve())  # Ensure absolute path

        # Create directory if it doesn't exist
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self.init_db()

    def init_db(self):
        """Initialize database with improved error handling."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with sqlite3.connect(self.db_path, timeout=30) as conn:
                    conn.executescript('''
                        CREATE TABLE IF NOT EXISTS jobs (
                            id INTEGER PRIMARY KEY,
                            title TEXT,
                            company TEXT,
                            location TEXT,
                            url TEXT UNIQUE,
                            description TEXT,
                            salary_min INTEGER,
                            salary_max INTEGER,
                            contract_type TEXT,
                            posted_date TEXT,
                            source TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );

                        CREATE TABLE IF NOT EXISTS applications (
                            id INTEGER PRIMARY KEY,
                            job_id INTEGER,
                            status TEXT,
                            applied_date TEXT,
                            follow_up_date TEXT,
                            notes TEXT,
                            FOREIGN KEY (job_id) REFERENCES jobs (id)
                        );

                        CREATE TABLE IF NOT EXISTS user_profiles (
                            id INTEGER PRIMARY KEY,
                            profile_data TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );

                        CREATE TABLE IF NOT EXISTS job_searches (
                            id INTEGER PRIMARY KEY,
                            query TEXT,
                            results_count INTEGER,
                            search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    ''')
                break  # Success, exit retry loop
            except sqlite3.Error as e:
                if attempt >= max_retries - 1:
                    raise RuntimeError(
                        f"Failed to initialize database after {max_retries} attempts: {e}"
                    ) from e
                time.sleep(0.5)  # Wait before retry
                continue

# =============================================================================
# Job Search Functions (No AI API calls)
# =============================================================================

async def search_adzuna_jobs(query: str, location: str = "London", max_results: int = 20) -> list[dict]:
    """Enhanced Adzuna search with better error handling."""
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        print("Warning: Adzuna API credentials not configured")
        return []

    endpoint = "https://api.adzuna.com/v1/api/jobs/gb/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": min(max_results, 50),
        "what": query,
        "where": location,
        "sort_by": "date",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            jobs = []
            for item in data.get("results", []):
                # Extract basic info and let Claude do the analysis
                job = {
                    "source": "adzuna",
                    "title": item.get("title", ""),
                    "company": item.get("company", {}).get("display_name", ""),
                    "location": item.get("location", {}).get("display_name", ""),
                    "salary_min": item.get("salary_min"),
                    "salary_max": item.get("salary_max"),
                    "contract_type": item.get("contract_type", ""),
                    "url": item.get("redirect_url", ""),
                    "description": item.get("description", "")[:1000],  # Limit for Claude
                    "posted_date": item.get("created", ""),
                    "category": item.get("category", {}).get("label", "")
                }
                jobs.append(job)

            return jobs

    except Exception as e:
        print(f"Adzuna search failed: {e}")
        return []

def extract_basic_job_features(job: dict) -> dict[str, Any]:
    """Extract structured features from job data for Claude analysis."""
    description = (job.get("description") or "").lower()
    title = (job.get("title") or "").lower()

    # Common tech keywords
    tech_keywords = [
        "python", "javascript", "java", "c++", "c#", "ruby", "php", "go", "rust",
        "react", "vue", "angular", "node", "django", "flask", "spring", "laravel",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins",
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "git", "agile", "scrum", "devops", "ci/cd", "microservices", "api"
    ]

    # Experience level indicators
    experience_indicators = {
        "junior": ["junior", "graduate", "entry level", "1-2 years", "early career"],
        "mid": ["mid", "intermediate", "3-5 years", "4+ years", "experienced"],
        "senior": ["senior", "lead", "5+ years", "7+ years", "expert", "principal"],
        "management": ["manager", "director", "head of", "vp", "cto", "lead team"]
    }

    # Remote work indicators
    remote_indicators = {
        "remote": ["remote", "work from home", "wfh", "distributed"],
        "hybrid": ["hybrid", "flexible", "2-3 days", "part remote"],
        "onsite": ["office", "on-site", "in person", "london office"]
    }

    # Extract features
    found_tech = [tech for tech in tech_keywords if tech in description or tech in title]

    experience_level = "not_specified"
    for level, keywords in experience_indicators.items():
        if any(keyword in description or keyword in title for keyword in keywords):
            experience_level = level
            break

    remote_policy = "not_specified"
    for policy, keywords in remote_indicators.items():
        if any(keyword in description for keyword in keywords):
            remote_policy = policy
            break

    # Salary analysis
    salary_info = {}
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")

    if salary_min and salary_max and isinstance(salary_min, int | float) and isinstance(salary_max, int | float):
        salary_info = {
            "min": salary_min,
            "max": salary_max,
            "average": (salary_min + salary_max) / 2
        }

    return {
        "tech_stack": found_tech,
        "experience_level": experience_level,
        "remote_policy": remote_policy,
        "salary_info": salary_info,
        "description_length": len(job.get("description", "")),
        "has_benefits": any(benefit in description for benefit in [
            "pension", "healthcare", "insurance", "holiday", "flexible", "learning"
        ])
    }

def create_analysis_framework(job: dict) -> JobAnalysisFramework:
    """Create a structured framework for Claude to analyze the job."""

    # Extract basic features
    _features = extract_basic_job_features(job)

    # Create analysis prompts for Claude
    analysis_prompts = {
        "requirements_extraction": f"""
        Analyze this job posting and extract:
        1. Required technical skills (must-have)
        2. Nice-to-have skills (preferred)
        3. Years of experience needed
        4. Key responsibilities
        5. Company benefits offered
        6. Any red flags or concerning requirements

        Job Title: {job.get('title', '')}
        Company: {job.get('company', '')}
        Description: {job.get('description', '')[:800]}
        """,
        "compatibility_scoring": """
        Score this job compatibility for a candidate with:
        - Skills: [TO BE PROVIDED BY USER]
        - Experience: [TO BE PROVIDED BY USER]

        Consider:
        - Technical skill match
        - Experience level alignment
        - Role responsibilities fit
        - Salary expectations vs offering
        - Remote work preferences

        Provide a score 1-10 with detailed reasoning.
        """,
        "application_strategy": """
        Based on this job posting, suggest:
        1. Key points to highlight in CV
        2. Cover letter talking points
        3. Potential interview questions
        4. Research areas about the company

        Focus on what would make a candidate stand out for this specific role.
        """,
    }

    # Scoring criteria for consistency
    scoring_criteria = {
        "technical_skills": [
            "Exact match for required skills",
            "Related/transferable skills",
            "Learning curve for missing skills"
        ],
        "experience": [
            "Years of experience alignment",
            "Relevant project experience",
            "Industry experience match"
        ],
        "cultural_fit": [
            "Company size preference",
            "Industry alignment",
            "Remote work policy match"
        ],
        "growth_potential": [
            "Career progression opportunities",
            "Skill development prospects",
            "Learning and training offered"
        ]
    }

    return JobAnalysisFramework(
        job_title=job.get('title', ''),
        job_description=job.get('description', '')[:800],
        company=job.get('company', ''),
        analysis_prompts=analysis_prompts,
        scoring_criteria=scoring_criteria
    )

# =============================================================================
# Initialize MCP Server and Database
# =============================================================================

def initialize_app():
    """Initialize the MCP server and database with proper error handling."""
    try:
        # Initialize MCP server
        mcp = FastMCP(name="Claude Desktop Job Search Agent")

        # Initialize database
        db = JobDatabase()

        print(f"Job Agent initialized successfully. Database: {db.db_path}")
        return mcp, db

    except Exception as e:
        print(f"Failed to initialize Job Agent: {e}")
        raise

# Initialize at module level
try:
    mcp, db = initialize_app()
except Exception as e:
    print(f"Critical error during initialization: {e}")
    sys.exit(1)

# =============================================================================
# MCP Tools (Claude Desktop Optimized)
# =============================================================================

@mcp.tool()
async def search_jobs_with_analysis_framework(
    query: str,
    location: str = "London",
    max_results: int = 15,
    include_analysis_framework: bool = True
) -> list[dict[str, Any]]:
    """
    Search for jobs and provide structured analysis frameworks for Claude to process.

    This tool finds jobs and prepares them with analysis prompts and scoring criteria
    so Claude can provide intelligent insights without external AI API calls.

    Parameters:
    - query: Job search keywords (e.g., "python developer", "data scientist")
    - location: Job location (default: London)
    - max_results: Maximum number of jobs to return (default: 15)
    - include_analysis_framework: Whether to include analysis prompts for Claude
    """
    try:
        # Validate parameters
        if not query or not query.strip():
            return {"error": "Query parameter is required"}

        query = query.strip()
        location = location.strip() if location else "London"
        max_results = max(1, min(max_results, 50))

        # Search multiple sources
        all_jobs = []

        # Search Adzuna
        try:
            adzuna_jobs = await search_adzuna_jobs(query, location, max_results)
            all_jobs.extend(adzuna_jobs)
        except Exception as e:
            print(f"Adzuna search error: {e}")

        # Remove duplicates based on company + title
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            key = f"{job.get('company', '').lower()}_{job.get('title', '').lower()}"
            if key not in seen and job.get('title') and job.get('company'):
                seen.add(key)
                unique_jobs.append(job)

        # Limit results
        unique_jobs = unique_jobs[:max_results]

        # Enhance jobs with analysis frameworks
        enhanced_jobs = []
        for job in unique_jobs:
            try:
                # Extract basic features
                features = extract_basic_job_features(job)

                enhanced_job = {
                    **job,
                    "extracted_features": features
                }

                # Add analysis framework if requested
                if include_analysis_framework:
                    framework = create_analysis_framework(job)
                    enhanced_job["analysis_framework"] = asdict(framework)

                enhanced_jobs.append(enhanced_job)

            except Exception as e:
                print(f"Error enhancing job {job.get('title', 'Unknown')}: {e}")
                # Include job without enhancement rather than skipping
                enhanced_jobs.append(job)

        # Log search to database (with error handling)
        try:
            with sqlite3.connect(db.db_path, timeout=10) as conn:
                conn.execute(
                    "INSERT INTO job_searches (query, results_count) VALUES (?, ?)",
                    (query, len(enhanced_jobs))
                )
                conn.commit()
        except Exception as e:
            print(f"Database logging error: {e}")
            # Don't fail the entire operation for logging errors

        return enhanced_jobs

    except Exception as e:
        print(f"Error in search_jobs_with_analysis_framework: {e}")
        return {"error": f"Search failed: {str(e)}"}

@mcp.tool()
async def create_job_compatibility_template(
    user_skills: list[str],
    experience_years: int,
    salary_expectation: int | None = None,
    remote_preference: str = "hybrid"
) -> dict[str, Any]:
    """
    Create a compatibility analysis template that Claude can use to score jobs.

    This provides Claude with a structured framework to consistently evaluate
    job compatibility without needing external AI API calls.

    Parameters:
    - user_skills: List of user's technical skills
    - experience_years: Years of professional experience
    - salary_expectation: Expected salary (optional)
    - remote_preference: "remote", "hybrid", or "onsite"
    """
    try:
        # Validate parameters
        if not isinstance(user_skills, list) or not user_skills:
            return {"error": "user_skills must be a non-empty list"}

        experience_years = max(0, experience_years)
        remote_preference = remote_preference.lower()

        if remote_preference not in ["remote", "hybrid", "onsite"]:
            remote_preference = "hybrid"

        # Create user profile
        user_profile = {
            "skills": user_skills,
            "experience_years": experience_years,
            "salary_expectation": salary_expectation,
            "remote_preference": remote_preference,
            "skill_levels": {
                "programming_languages": [s for s in user_skills if s.lower() in [
                    "python", "javascript", "java", "c++", "c#", "ruby", "php", "go", "rust"
                ]],
                "frameworks": [s for s in user_skills if s.lower() in [
                    "react", "vue", "angular", "django", "flask", "spring", "laravel"
                ]],
                "tools": [s for s in user_skills if s.lower() in [
                    "aws", "docker", "kubernetes", "git", "jenkins", "terraform"
                ]],
                "databases": [s for s in user_skills if s.lower() in [
                    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch"
                ]]
            }
        }

        # Compatibility scoring template
        scoring_template = {
            "evaluation_criteria": {
                "technical_skills": {
                    "weight": 40,
                    "scoring_guide": {
                        "10": "Perfect match - candidate has all required skills",
                        "8-9": "Excellent match - has most required skills + some nice-to-haves",
                        "6-7": "Good match - has core skills, missing 1-2 requirements",
                        "4-5": "Moderate match - has transferable skills, some learning needed",
                        "1-3": "Low match - significant skill gaps, major learning required"
                    }
                },
                "experience_level": {
                    "weight": 25,
                    "scoring_guide": {
                        "10": "Perfect experience level match",
                        "8-9": "Slightly over/under qualified but strong fit",
                        "6-7": "Some experience gap but manageable",
                        "4-5": "Noticeable experience gap",
                        "1-3": "Significant experience mismatch"
                    }
                },
                "salary_alignment": {
                    "weight": 20,
                    "scoring_guide": {
                        "10": "Salary meets or exceeds expectations",
                        "8-9": "Salary close to expectations",
                        "6-7": "Salary somewhat below expectations",
                        "4-5": "Salary notably below expectations",
                        "1-3": "Salary significantly below expectations"
                    }
                },
                "work_arrangement": {
                    "weight": 15,
                    "scoring_guide": {
                        "10": "Perfect remote work policy match",
                        "8-9": "Good work arrangement fit",
                        "6-7": "Acceptable work arrangement",
                        "4-5": "Work arrangement not ideal",
                        "1-3": "Work arrangement doesn't match preference"
                    }
                }
            },
            "analysis_prompts": {
                "skill_analysis": "Compare the candidate's skills against job requirements. Identify exact matches, transferable skills, and gaps.",
                "experience_analysis": "Evaluate if candidate's experience level aligns with job requirements and responsibilities.",
                "growth_potential": "Assess learning opportunities and career growth potential in this role.",
                "red_flags": "Identify any concerning aspects like unrealistic expectations, poor work-life balance indicators, or unclear requirements."
            },
            "output_format": {
                "compatibility_score": "Overall score 1-10",
                "skill_match_percentage": "Percentage of required skills matched",
                "strengths": "List of candidate's advantages for this role",
                "gaps": "List of missing skills or experience",
                "recommendation": "High/Medium/Low application priority with reasoning",
                "application_tips": "Specific advice for applying to this role"
            }
        }

        return {
            "user_profile": user_profile,
            "scoring_template": scoring_template,
            "usage_instructions": {
                "step_1": "Use this template to analyze each job posting",
                "step_2": "Score each criteria according to the guides",
                "step_3": "Calculate weighted average for overall compatibility",
                "step_4": "Provide specific recommendations and application tips"
            }
        }

    except Exception as e:
        return {"error": f"Failed to create compatibility template: {str(e)}"}

@mcp.tool()
async def track_job_application(
    job_url: str,
    company_name: str,
    position: str,
    application_date: str,
    status: str = "applied",
    notes: str = ""
) -> dict[str, Any]:
    """
    Track a job application with follow-up reminders and next steps.

    Parameters:
    - job_url: URL of the job posting
    - company_name: Name of the company
    - position: Job title/position
    - application_date: Date application was submitted (YYYY-MM-DD)
    - status: Current status (applied, interview_scheduled, rejected, etc.)
    - notes: Additional notes about the application
    """
    try:
        # Validate parameters
        if not all([job_url, company_name, position, application_date]):
            return {"error": "All required parameters must be provided"}

        # Store in database
        application_id = None

        try:
            # Use the same database path resolution as other functions
            # This ensures we use the test database during testing
            db_path = os.getenv("DATABASE_PATH", db.db_path)

            # Store in database with error handling
            with sqlite3.connect(db_path, timeout=10) as conn:
                cursor = conn.cursor()

                # First, store/update job info
                cursor.execute('''
                    INSERT OR REPLACE INTO jobs (title, company, url)
                    VALUES (?, ?, ?)
                ''', (position, company_name, job_url))

                job_id = cursor.lastrowid

                # If this was a REPLACE operation (not INSERT), we need to get the actual job_id
                if cursor.rowcount != 1:
                    # This was a REPLACE, need to get the actual job_id
                    cursor.execute('SELECT id FROM jobs WHERE url = ?', (job_url,))
                    if result := cursor.fetchone():
                        job_id = result[0]

                # Store application tracking
                cursor.execute('''
                    INSERT INTO applications (job_id, status, applied_date, notes)
                    VALUES (?, ?, ?, ?)
                ''', (job_id, status, application_date, notes))

                conn.commit()
                application_id = cursor.lastrowid

        except sqlite3.Error as e:
            # Log error but continue with response
            print(f"Database error in track_job_application: {e}")
            application_id = -1  # Indicate database failure
        except Exception as e:
            print(f"Unexpected error in track_job_application: {e}")
            application_id = -1

        # Calculate follow-up dates
        try:
            apply_date = datetime.strptime(application_date, "%Y-%m-%d")
            follow_up_date = apply_date + timedelta(days=7)
            reminder_date = apply_date + timedelta(days=14)
        except ValueError:
            # Handle invalid date format
            apply_date = datetime.now()
            follow_up_date = apply_date + timedelta(days=7)
            reminder_date = apply_date + timedelta(days=14)

        # Generate next actions based on status
        next_actions = {
            "applied": [
                "Research hiring manager on LinkedIn",
                "Set calendar reminder for follow-up in 1 week",
                "Prepare for potential screening call",
                "Research company recent news and developments"
            ],
            "interview_scheduled": [
                "Research interviewer backgrounds on LinkedIn",
                "Prepare technical examples relevant to role",
                "Practice common interview questions",
                "Plan interview outfit and logistics"
            ],
            "interviewed": [
                "Send thank-you email within 24 hours",
                "Reflect on interview questions for future prep",
                "Follow up if no response within their timeline",
                "Continue applying to other opportunities"
            ]
        }

        return {
            "application_id": application_id,
            "tracking_info": {
                "company": company_name,
                "position": position,
                "status": status,
                "applied_date": application_date,
                "follow_up_date": follow_up_date.strftime("%Y-%m-%d"),
                "reminder_date": reminder_date.strftime("%Y-%m-%d")
            },
            "next_actions": next_actions.get(status, [
                "Update application status as situation develops",
                "Continue job search activities",
                "Network within the industry"
            ]),
            "timeline": {
                "application_submitted": application_date,
                "expected_response": (apply_date + timedelta(days=14)).strftime("%Y-%m-%d"),
                "follow_up_if_no_response": follow_up_date.strftime("%Y-%m-%d"),
                "move_on_date": (apply_date + timedelta(days=30)).strftime("%Y-%m-%d")
            },
            "tips": [
                "Keep detailed notes of all interactions",
                "Set calendar reminders for follow-ups",
                "Research company and role continuously",
                "Prepare for multiple interview rounds",
                "Keep applying to other opportunities"
            ],
            "database_status": "success" if application_id and application_id > 0 else "failed"
        }

    except Exception as e:
        return {"error": f"Failed to track application: {str(e)}"}

@mcp.tool()
async def get_application_status_summary() -> dict[str, Any]:
    """
    Get a summary of all tracked job applications and their current status.

    Provides an overview of application pipeline and follow-up actions needed.
    """
    try:
        # Use the same database path resolution as other functions
        db_path = os.getenv("DATABASE_PATH", db.db_path)

        with sqlite3.connect(db_path, timeout=10) as conn:
            cursor = conn.cursor()

            # Get all applications with job details
            cursor.execute('''
                SELECT a.id, j.title, j.company, j.url, a.status, a.applied_date, a.notes
                FROM applications a
                LEFT JOIN jobs j ON a.job_id = j.id
                ORDER BY a.applied_date DESC
            ''')

            applications = []
            for row in cursor.fetchall():
                app_id, title, company, url, status, applied_date, notes = row

                # Calculate days since application
                try:
                    applied = datetime.strptime(applied_date, "%Y-%m-%d")
                    days_since = (datetime.now() - applied).days
                except (ValueError, TypeError):
                    days_since = 0

                applications.append({
                    "id": app_id,
                    "title": title or "Unknown Position",
                    "company": company or "Unknown Company",
                    "url": url or "",
                    "status": status,
                    "applied_date": applied_date,
                    "days_since_application": days_since,
                    "notes": notes or "",
                    "needs_follow_up": days_since >= 7 and status == "applied"
                })

            # Get status summary
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM applications
                GROUP BY status
            ''')

            status_summary = {row[0]: row[1] for row in cursor.fetchall()}

        # Identify actions needed
        follow_up_needed = [app for app in applications if app["needs_follow_up"]]
        recent_applications = [app for app in applications if app["days_since_application"] <= 7]

        # Calculate success metrics safely
        total_apps = len(applications)
        responded_apps = len([app for app in applications if app['status'] != 'applied'])
        interview_apps = len([app for app in applications if 'interview' in app['status']])

        # Calculate average response time for responded applications
        if responded_apps > 0:
            avg_response_time = sum(app['days_since_application'] for app in applications if app['status'] != 'applied') / responded_apps
        else:
            avg_response_time = 0

        return {
            "total_applications": total_apps,
            "status_breakdown": status_summary,
            "recent_applications": recent_applications,
            "follow_up_needed": follow_up_needed,
            "applications_by_company": {
                company: len([app for app in applications if app["company"] == company])
                for company in {app["company"] for app in applications}
            },
            "success_metrics": {
                "response_rate": f"{responded_apps} / {total_apps} responses",
                "interview_rate": f"{interview_apps} / {total_apps} interviews",
                "average_response_time": f"{avg_response_time:.1f} days",
            },
            "recommendations": [
                f"Follow up on {len(follow_up_needed)} applications that haven't received responses",
                "Continue applying to maintain pipeline momentum",
                "Analyze successful applications to improve strategy",
                "Network with employees at companies of interest",
                "Keep detailed notes on all interactions for future reference",
            ],
        }

    except Exception as e:
        return {"error": f"Failed to get application summary: {str(e)}"}


@mcp.tool()
async def generate_application_templates(
    job_title: str,
    company_name: str,
    job_description: str,
    user_background: str
) -> dict[str, Any]:
    """
    Generate structured templates for job applications that Claude can customize.

    Provides frameworks for CVs, cover letters, and interview prep without
    requiring external AI API calls.

    Parameters:
    - job_title: The position being applied for
    - company_name: Name of the hiring company
    - job_description: Full job posting text
    - user_background: Brief summary of candidate's background
    """
    try:
        # Validate parameters
        if not all([job_title, company_name, job_description, user_background]):
            return {"error": "All parameters are required"}

        # Extract key info from job description
        description_lower = job_description.lower()

        # Common benefits and perks
        benefits_found = []
        benefit_keywords = {
            "health_insurance": ["health", "medical", "dental", "vision"],
            "flexible_hours": ["flexible", "hours", "work-life balance"],
            "remote_work": ["remote", "work from home", "hybrid"],
            "learning_budget": ["learning", "training", "courses", "development"],
            "pension": ["pension", "401k", "retirement"],
            "stock_options": ["equity", "stock", "options", "shares"]
        }

        benefits_found.extend(
            benefit.replace("_", " ").title()
            for benefit, keywords in benefit_keywords.items()
            if any(keyword in description_lower for keyword in keywords)
        )

        # CV optimization template
        cv_template = {
            "summary_section": f"""
            Template: "[X] years of experience in [relevant field] with expertise in [key skills from job description].
            Proven track record of [relevant achievements]. Seeking to leverage [specific skills] to contribute to {company_name}'s [relevant company goal/mission]."

            Customization notes:
            - Replace bracketed placeholders with specific details
            - Highlight skills that match job requirements exactly
            - Mention company-specific goals if known
            """,
            "key_skills_section": {
                "technical_skills": "List skills mentioned in job description first",
                "soft_skills": "Include leadership, communication, problem-solving as relevant",
                "tools_technologies": "Match tools/technologies mentioned in job posting",
            },
            "experience_bullets": {
                "template": "• [Action verb] [what you did] [how/tools used] resulting in [quantified impact]",
                "examples": [
                    "• Developed scalable web applications using Python and Django, serving 10,000+ users daily",
                    "• Led cross-functional team of 5 developers to deliver features 20% ahead of schedule",
                    "• Optimized database queries reducing response time by 40% and improving user experience",
                ],
                "customization_tips": [
                    "Use action verbs that match job description language",
                    "Quantify achievements with specific numbers/percentages",
                    "Highlight technologies mentioned in job posting",
                    "Focus on results and business impact",
                ],
            },
        }

        # Cover letter template
        cover_letter_template = {
            "opening_paragraph": f"""
            Template: "I am writing to express my strong interest in the {job_title} position at {company_name}.
            With [X years] of experience in [relevant field] and expertise in [key skills from job],
            I am excited about the opportunity to contribute to [specific company goal/project mentioned in job]."
            """,

            "body_paragraphs": {
                "experience_paragraph": "Highlight 2-3 most relevant experiences that directly match job requirements",
                "skills_paragraph": "Demonstrate specific technical skills mentioned in job posting with examples",
                "company_paragraph": "Show knowledge of company and why you want to work there specifically"
            },

            "closing_paragraph": f"""
            Template: "I would welcome the opportunity to discuss how my background in [relevant area]
            and passion for [relevant field/mission] can contribute to {company_name}'s continued success.
            Thank you for considering my application."
            """
        }

        # Interview preparation framework
        interview_prep = {
            "likely_technical_questions": [
                "Tell me about your experience with [technologies mentioned in job description]",
                "How would you approach [specific challenge mentioned in job responsibilities]?",
                "Describe a project where you [key responsibility from job posting]",
                "Walk me through your problem-solving process for [relevant technical scenario]",
            ],
            "behavioral_questions": [
                "Tell me about a time you overcame a significant technical challenge",
                "Describe a situation where you had to work with a difficult team member",
                "How do you prioritize tasks when everything seems urgent?",
                "Give an example of when you had to learn a new technology quickly",
            ],
            "company_specific_questions": [
                f"Why do you want to work at {company_name}?",
                f"How do you see yourself contributing to {company_name}'s mission?",
                "What do you know about our recent developments/products?",
                "What attracts you to this particular role/team?",
            ],
            "questions_to_ask": [
                "What does success look like in this role after 6 months?",
                "What are the biggest challenges facing the team right now?",
                "How does the company support professional development?",
                "What's the team structure and collaboration style?",
                "What technologies is the team excited about adopting?",
            ],
        }

        return {
            "cv_optimization": cv_template,
            "cover_letter": cover_letter_template,
            "interview_preparation": interview_prep,
            "application_strategy": {
                "priority_level": "Analyze job competitiveness and your fit to determine application urgency",
                "follow_up_timeline": "Apply within 48 hours, follow up after 1 week if no response",
                "networking_approach": "Research hiring manager and team members on LinkedIn",
                "portfolio_preparation": "Prepare 2-3 relevant project examples that demonstrate required skills"
            },
            "customization_checklist": [
                "✓ Tailor CV to include keywords from job description",
                "✓ Research company recent news and developments",
                "✓ Prepare specific examples that match job requirements",
                "✓ Practice explaining technical concepts clearly",
                "✓ Prepare questions about role and company culture"
            ]
        }

    except Exception as e:
        return {"error": f"Failed to generate application templates: {str(e)}"}

@mcp.tool()
async def analyze_job_market_data(
    location: str = "London",
    job_category: str = "Technology",
    timeframe_days: int = 30
) -> dict[str, Any]:
    """
    Analyze job market trends using stored search data and provide insights.

    This tool analyzes job search patterns and provides market intelligence
    without requiring external API calls.

    Parameters:
    - location: Geographic area to analyze
    - job_category: Industry/job category
    - timeframe_days: Number of days to look back for analysis
    """
    try:
        # Analyze stored job search data
        with sqlite3.connect(db.db_path, timeout=10) as conn:
            cursor = conn.cursor()

            # Get recent search patterns
            cursor.execute(f'''
                SELECT query, COUNT(*) as search_count, AVG(results_count) as avg_results
                FROM job_searches
                WHERE search_date > datetime('now', '-{timeframe_days} days')
                GROUP BY query
                ORDER BY search_count DESC
                LIMIT 10
            ''')

            popular_searches = [
                {"query": row[0], "search_count": row[1], "avg_results": row[2]}
                for row in cursor.fetchall()
            ]

            # Get job data trends
            cursor.execute(f'''
                SELECT company, COUNT(*) as job_count
                FROM jobs
                WHERE created_at > datetime('now', '-{timeframe_days} days')
                GROUP BY company
                ORDER BY job_count DESC
                LIMIT 10
            ''')

            top_hiring_companies = [
                {"company": row[0], "job_count": row[1]}
                for row in cursor.fetchall()
            ]

            # Application tracking insights
            cursor.execute(f'''
                SELECT status, COUNT(*) as count
                FROM applications
                WHERE applied_date > date('now', '-{timeframe_days} days')
                GROUP BY status
            ''')

            application_stats = {row[0]: row[1] for row in cursor.fetchall()}

        # Market insights based on common patterns
        market_insights = {
            "demand_indicators": {
                "high_demand_skills": [
                    "Python", "JavaScript", "React", "AWS", "Docker", "Kubernetes",
                    "SQL", "Machine Learning", "Data Analysis", "DevOps"
                ],
                "emerging_skills": [
                    "AI/ML", "Cloud Computing", "Cybersecurity", "Blockchain",
                    "Data Engineering", "Site Reliability Engineering"
                ],
                "skill_trends": "Based on job descriptions, cloud technologies and AI/ML skills show increasing demand"
            },
            "salary_patterns": {
                "entry_level": {"min": 35000, "max": 50000, "average": 42500},
                "mid_level": {"min": 50000, "max": 80000, "average": 65000},
                "senior_level": {"min": 80000, "max": 120000, "average": 95000},
                "lead_level": {"min": 100000, "max": 150000, "average": 125000},
                "note": "Salaries vary significantly by company size, industry, and specific skills"
            },
            "remote_work_trends": {
                "fully_remote": "25-30% of tech positions",
                "hybrid": "50-60% of tech positions",
                "onsite_only": "15-20% of tech positions",
                "trend": "Hybrid work arrangements becoming the standard"
            },
            "hiring_patterns": {
                "peak_hiring_months": ["January", "February", "September", "October"],
                "slow_periods": ["December", "July", "August"],
                "application_response_time": "1-2 weeks for initial response, 3-4 weeks for full process"
            }
        }

        return {
            "analysis_period": f"Last {timeframe_days} days",
            "location": location,
            "popular_searches": popular_searches,
            "top_hiring_companies": top_hiring_companies,
            "application_statistics": application_stats,
            "market_insights": market_insights,
            "recommendations": [
                "Focus on in-demand skills like cloud technologies and AI/ML",
                "Target hybrid/remote positions for better work-life balance",
                "Apply during peak hiring months for better response rates",
                "Research company-specific benefits and culture",
                "Network actively on LinkedIn and attend tech meetups",
                "Keep skills updated with online courses and certifications"
            ],
            "job_search_strategy": {
                "application_volume": "Apply to 10-15 relevant positions per week",
                "quality_over_quantity": "Tailor each application to specific role requirements",
                "follow_up_timeline": "Follow up after 1 week if no initial response",
                "networking_importance": "40% of jobs are filled through networking",
                "skill_development": "Continuous learning is essential in tech roles"
            }
        }

    except Exception as e:
        return {"error": f"Failed to analyze job market data: {str(e)}"}

@mcp.tool()
async def create_career_progression_framework(
    current_role: str,
    target_roles: list[str],
    current_skills: list[str],
    timeline_months: int = 24
) -> dict[str, Any]:
    """
    Create a structured career progression framework that Claude can use to provide guidance.

    This tool provides comprehensive career planning templates without requiring
    external AI API calls.

    Parameters:
    - current_role: Current job title/position
    - target_roles: List of desired future roles
    - current_skills: List of current technical and soft skills
    - timeline_months: Target timeline for progression (default: 24 months)
    """
    try:
        # Validate parameters
        if not current_role or not target_roles or not current_skills:
            return {"error": "All parameters are required"}

        if not isinstance(target_roles, list) or not isinstance(current_skills, list):
            return {"error": "target_roles and current_skills must be lists"}

        timeline_months = max(6, min(timeline_months, 120))

        # Skill categories and progressions
        skill_progressions = {
            "software_engineer": {
                "junior_to_mid": {
                    "technical": ["Advanced debugging", "Code review skills", "Testing frameworks", "CI/CD"],
                    "soft": ["Communication", "Time management", "Basic mentoring"],
                    "timeline": "12-18 months"
                },
                "mid_to_senior": {
                    "technical": ["System design", "Architecture patterns", "Performance optimization", "Security"],
                    "soft": ["Leadership", "Technical mentoring", "Project planning"],
                    "timeline": "18-36 months"
                },
                "senior_to_lead": {
                    "technical": ["Large-scale systems", "Technology strategy", "Cross-team collaboration"],
                    "soft": ["Team leadership", "Strategic thinking", "Stakeholder management"],
                    "timeline": "24-48 months"
                }
            },
            "data_scientist": {
                "junior_to_mid": {
                    "technical": ["Advanced SQL", "Machine learning algorithms", "Data visualization", "Statistical analysis"],
                    "soft": ["Business acumen", "Presentation skills", "Problem-solving"],
                    "timeline": "12-24 months"
                },
                "mid_to_senior": {
                    "technical": ["MLOps", "Deep learning", "Big data technologies", "Model deployment"],
                    "soft": ["Cross-functional collaboration", "Technical communication", "Project leadership"],
                    "timeline": "18-36 months"
                }
            },
            "product_manager": {
                "junior_to_mid": {
                    "technical": ["User research", "Data analysis", "Product analytics", "A/B testing"],
                    "soft": ["Stakeholder management", "Communication", "Priority setting"],
                    "timeline": "12-18 months"
                },
                "mid_to_senior": {
                    "technical": ["Product strategy", "Market analysis", "Technical understanding", "Metrics definition"],
                    "soft": ["Leadership", "Vision setting", "Cross-team collaboration"],
                    "timeline": "18-30 months"
                }
            }
        }

        # Career path templates
        career_paths = []
        for target_role in target_roles:

            # Determine progression path
            role_lower = target_role.lower()
            if "senior" in role_lower or "lead" in role_lower:
                if ("engineer" in role_lower or "developer" in role_lower) and "data" not in role_lower and "product" not in role_lower:
                    progression = skill_progressions["software_engineer"]["mid_to_senior"]
                elif "data" in role_lower:
                    progression = skill_progressions["data_scientist"]["mid_to_senior"]
                else:
                    progression = skill_progressions["product_manager"]["mid_to_senior"]
            elif ("engineer" in role_lower or "developer" in role_lower) and "data" not in role_lower and "product" not in role_lower:
                progression = skill_progressions["software_engineer"]["junior_to_mid"]
            elif "data" in role_lower:
                progression = skill_progressions["data_scientist"]["junior_to_mid"]
            else:
                progression = skill_progressions["product_manager"]["junior_to_mid"]

            # Calculate skill gaps
            required_technical = progression["technical"]
            required_soft = progression["soft"]

            missing_technical = [skill for skill in required_technical if skill not in current_skills]
            missing_soft = [skill for skill in required_soft if skill not in current_skills]

            # Create learning roadmap
            learning_roadmap = {
                "immediate_focus": missing_technical[:2] + missing_soft[:1],
                "medium_term": missing_technical[2:] + missing_soft[1:],
                "learning_resources": {
                    "online_courses": ["Coursera", "Udemy", "Pluralsight", "LinkedIn Learning"],
                    "certifications": ["AWS", "Google Cloud", "Microsoft Azure", "Kubernetes"],
                    "books": ["System Design Interview", "Clean Code", "Designing Data-Intensive Applications"],
                    "practice": ["LeetCode", "HackerRank", "Personal projects", "Open source contributions"]
                }
            }

            career_path = {
                "target_role": target_role,
                "estimated_timeline": progression["timeline"],
                "skill_requirements": {
                    "technical": required_technical,
                    "soft_skills": required_soft
                },
                "skill_gaps": {
                    "technical": missing_technical,
                    "soft_skills": missing_soft,
                    "gap_percentage": (len(missing_technical) + len(missing_soft)) / (len(required_technical) + len(required_soft)) * 100 if (len(required_technical) + len(required_soft)) > 0 else 0
                },
                "learning_roadmap": learning_roadmap,
                "intermediate_steps": [
                    f"Gain proficiency in {missing_technical[0] if missing_technical else 'advanced concepts'}",
                    f"Develop {missing_soft[0] if missing_soft else 'leadership'} skills",
                    f"Take on projects involving {target_role.lower()} responsibilities",
                    f"Seek mentorship from current {target_role}s",
                    f"Apply for {target_role} positions when 70% ready"
                ]
            }

            career_paths.append(career_path)

        # Action plan framework
        action_plan = {
            "month_1_3": [
                "Assess current skill level against target roles",
                "Start learning highest-priority missing skills",
                "Identify potential mentors in target roles",
                "Update LinkedIn profile with career goals",
                "Begin networking in target role communities"
            ],
            "month_4_12": [
                "Complete 2-3 relevant online courses or certifications",
                "Start taking on responsibilities that align with target role",
                "Build portfolio projects demonstrating required skills",
                "Attend industry meetups and conferences",
                "Seek feedback from managers on progression goals"
            ],
            "month_13_24": [
                "Apply for target roles when 70% skill-ready",
                "Seek internal promotion opportunities",
                "Complete advanced certifications",
                "Mentor others to develop leadership skills",
                "Build industry presence through content/speaking"
            ]
        }

        return {
            "current_position": current_role,
            "target_roles": target_roles,
            "timeline": f"{timeline_months} months",
            "career_paths": career_paths,
            "action_plan": action_plan,
            "success_metrics": {
                "skill_development": "Complete X courses/certifications per quarter",
                "networking": "Connect with X professionals in target roles monthly",
                "experience": "Take on X projects involving target role responsibilities",
                "recognition": "Receive positive feedback on target role competencies",
                "applications": "Apply to X target role positions when ready"
            },
            "risk_mitigation": {
                "backup_plans": "Identify alternative career paths if primary path stalls",
                "skill_verification": "Get feedback from professionals in target roles",
                "market_changes": "Stay updated on industry trends and skill demands",
                "timeline_flexibility": "Adjust timeline based on learning pace and opportunities"
            },
            "resources": {
                "learning_platforms": ["Coursera", "Udemy", "Pluralsight", "edX"],
                "networking": ["LinkedIn", "Industry meetups", "Professional associations"],
                "mentorship": ["Company mentoring programs", "Industry mentors", "Online communities"],
                "skill_assessment": ["Technical interviews", "Peer feedback", "Project reviews"]
            }
        }

    except Exception as e:
        return {"error": f"Failed to create career progression framework: {str(e)}"}

# =============================================================================
# Entry Point for Claude Desktop
# =============================================================================

def main():
    """Entry point for the MCP server."""
    try:
        print("Starting Claude Job Search Agent...")
        mcp.run()
    except KeyboardInterrupt:
        print("\nShutting down Claude Job Search Agent...")
    except Exception as e:
        print(f"Error running MCP server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
