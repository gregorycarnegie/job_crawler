import logging
import re
from typing import Any, List

from job import Job
from user_profile import UserProfile

logger = logging.getLogger("param-job-agent")


class ParamJobAgent:
    """Simplified job agent that works without external dependencies."""

    def __init__(self) -> None:
        self.user_profile = UserProfile(skills=[], experience=[], qualifications=[])
        # Basic fintech keywords for relevance
        self.fintech_keywords = [
            "fintech",
            "payments",
            "banking",
            "trading",
            "investment",
        ]

    def set_user_profile(self, profile_data: dict[str, Any]) -> None:
        """Update the in-memory user profile."""
        if "skills" in profile_data:
            self.user_profile.skills = list(profile_data["skills"])
        if "experience" in profile_data:
            self.user_profile.experience = list(profile_data["experience"])
        if "qualifications" in profile_data:
            self.user_profile.qualifications = list(profile_data["qualifications"])
        if "min_salary" in profile_data:
            self.user_profile.min_salary = int(profile_data["min_salary"])

    @staticmethod
    def extract_salary_amount(salary_text: str) -> int:
        """Extract a numeric salary amount from a string."""
        if not salary_text:
            return 0
        match = re.search(r"(\d{2,6})", salary_text.replace(",", ""))
        return int(match.group(1)) if match else 0

    def calculate_match_score(self, job: Job) -> float:
        """Calculate how well a job matches the user profile."""
        score = 0.0
        job_text = f"{job.title} {job.description}".lower()

        # Fintech relevance
        score += sum(k in job_text for k in self.fintech_keywords) * 10

        # Skill matches
        score += sum(s.lower() in job_text for s in self.user_profile.skills) * 15

        # Experience matches
        score += sum(e.lower() in job_text for e in self.user_profile.experience) * 12

        # Qualification matches
        score += sum(q.lower() in job_text for q in self.user_profile.qualifications) * 8

        if job.salary and self.extract_salary_amount(job.salary) >= self.user_profile.min_salary:
            score += 20

        return min(score, 100.0)

    async def search_fintech_jobs(self, limit: int = 20) -> List[Job]:
        """Return a static list of sample jobs ordered by match score."""
        sample_jobs = [
            Job(
                title="Senior Python Developer",
                company="FinTech Stars",
                location="London",
                salary="60000",
                description="Work on cutting edge payment platforms using Python and AWS.",
                url="https://example.com/job1",
                source="sample",
            ),
            Job(
                title="Backend Engineer",
                company="Payments Inc",
                location="Remote",
                salary="55000",
                description="Develop scalable APIs for our banking partners.",
                url="https://example.com/job2",
                source="sample",
            ),
            Job(
                title="DevOps Specialist",
                company="Trading Solutions",
                location="Manchester",
                salary="50000",
                description="Maintain cloud infrastructure for high frequency trading.",
                url="https://example.com/job3",
                source="sample",
            ),
        ]

        for job in sample_jobs:
            job.match_score = self.calculate_match_score(job)

        sample_jobs.sort(key=lambda j: j.match_score, reverse=True)
        return sample_jobs[:limit]

