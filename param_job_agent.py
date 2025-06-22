import asyncio
import logging
import re
from typing import Optional, Any
from urllib.parse import urljoin, urlencode

import aiohttp
from bs4 import BeautifulSoup

from job import Job
from job_site import JobSite
from user_profile import UserProfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("param-job-agent")

class ParamJobAgent:
    def __init__(self):
        self.user_profile = UserProfile(skills=[], experience=[], qualifications=[])

        # Job sites configuration
        self.job_sites = [
            JobSite("Indeed UK", "https://uk.indeed.com", "/jobs"),
            JobSite("Reed", "https://www.reed.co.uk", "/jobs"),
            JobSite("Totaljobs", "https://www.totaljobs.com", "/jobs"),
        ]

        # Fintech keywords for relevance scoring
        self.fintech_keywords = [
            'fintech', 'financial technology', 'banking', 'payments', 'cryptocurrency',
            'blockchain', 'trading', 'investment', 'wealth management', 'insurtech',
            'regtech', 'digital banking', 'mobile payments', 'peer-to-peer',
            'robo-advisor', 'algorithmic trading', 'risk management', 'financial services',
            'payment processing', 'open banking', 'neobank', 'digital wallet'
        ]

    def set_user_profile(self, profile_data: dict[str, Any]) -> None:
        """Update user profile with new data"""
        if 'skills' in profile_data:
            self.user_profile.skills = profile_data['skills']
        if 'experience' in profile_data:
            self.user_profile.experience = profile_data['experience']
        if 'qualifications' in profile_data:
            self.user_profile.qualifications = profile_data['qualifications']
        if 'min_salary' in profile_data:
            self.user_profile.min_salary = profile_data['min_salary']

    @staticmethod
    async def fetch_page(session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Fetch a web page with proper headers and error handling"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

        try:
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    @staticmethod
    def parse_indeed_jobs(html: str, base_url: str) -> list[Job]:
        """Parse Indeed UK job listings"""
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []

        # Indeed's job cards
        job_cards = soup.find_all('div', class_='job_seen_beacon') or soup.find_all('div', {'data-testid': 'job-result'})

        for card in job_cards:
            try:
                # Title and URL
                title_elem = card.find('h2') or card.find('a', {'data-testid': 'job-title'})
                if not title_elem:
                    continue

                link_elem = title_elem.find('a') or title_elem
                title = link_elem.get_text(strip=True) if link_elem else ""
                job_url = urljoin(base_url, link_elem.get('href', '')) if link_elem.get('href') else ""

                # Company
                company_elem = card.find('span', {'data-testid': 'company-name'}) or card.find('span', class_='companyName')
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"

                # Location
                location_elem = card.find('div', {'data-testid': 'job-location'}) or card.find('div', class_='companyLocation')
                location = location_elem.get_text(strip=True) if location_elem else "UK"

                # Salary
                salary_elem = card.find('span', class_='salary-snippet') or card.find('div', class_='salary-snippet-container')
                salary = salary_elem.get_text(strip=True) if salary_elem else None

                # Description
                desc_elem = card.find('div', class_='job-snippet') or card.find('div', {'data-testid': 'job-snippet'})
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                if title and company:
                    job = Job(
                        title=title,
                        company=company,
                        location=location,
                        salary=salary,
                        description=description,
                        url=job_url,
                        source="Indeed UK"
                    )
                    jobs.append(job)

            except Exception as e:
                logger.error(f"Error parsing Indeed job card: {e}")
                continue

        return jobs

    @staticmethod
    def parse_reed_jobs(html: str, base_url: str) -> list[Job]:
        """Parse Reed.co.uk job listings"""
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []

        job_cards = soup.find_all('article', class_='job-result') or soup.find_all('div', class_='job-result')

        for card in job_cards:
            try:
                # Title and URL
                title_elem = card.find('h3') or card.find('h2')
                if not title_elem:
                    continue

                link_elem = title_elem.find('a')
                title = link_elem.get_text(strip=True) if link_elem else title_elem.get_text(strip=True)
                job_url = urljoin(base_url, link_elem.get('href', '')) if link_elem and link_elem.get('href') else ""

                # Company
                company_elem = card.find('a', class_='gtmJobListingPostedBy') or card.find('div', class_='job-result-heading__company')
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"

                # Location
                location_elem = card.find('li', class_='job-metadata__item--location') or card.find('div', class_='job-metadata')
                location = location_elem.get_text(strip=True) if location_elem else "UK"

                # Salary
                salary_elem = card.find('li', class_='job-metadata__item--salary')
                salary = salary_elem.get_text(strip=True) if salary_elem else None

                # Description
                desc_elem = card.find('p', class_='job-result-description__details')
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                if title and company:
                    job = Job(
                        title=title,
                        company=company,
                        location=location,
                        salary=salary,
                        description=description,
                        url=job_url,
                        source="Reed"
                    )
                    jobs.append(job)

            except Exception as e:
                logger.error(f"Error parsing Reed job card: {e}")
                continue

        return jobs

    async def crawl_job_site(self, session: aiohttp.ClientSession, site: JobSite, query: str) -> list[Job]:
        """Crawl a specific job site for fintech positions"""
        try:
            # Build search URL
            if site.name == "Indeed UK":
                params = {
                    'q': f"{query} fintech",
                    'l': 'United Kingdom',
                    'fromage': '14',  # Last 2 weeks
                    'salary': '50000'
                }
                search_url = f"{site.base_url}{site.search_path}?{urlencode(params)}"

            elif site.name == "Reed":
                params = {
                    'keywords': f"{query} fintech",
                    'location': 'UK',
                    'salaryfrom': '50000'
                }
                search_url = f"{site.base_url}{site.search_path}?{urlencode(params)}"

            elif site.name == "Totaljobs":
                params = {
                    'Keywords': f"{query} fintech",
                    'Location': 'UK',
                    'Salary': '50000'
                }
                search_url = f"{site.base_url}{site.search_path}?{urlencode(params)}"
            else:
                return []

            logger.info(f"Crawling {site.name}: {search_url}")

            # Fetch the page
            html = await self.fetch_page(session, search_url)
            if not html:
                return []

            # Parse based on site
            if site.name == "Indeed UK":
                return self.parse_indeed_jobs(html, site.base_url)
            elif site.name == "Reed":
                return self.parse_reed_jobs(html, site.base_url)
            else:
                return []

        except Exception as e:
            logger.error(f"Error crawling {site.name}: {e}")
            return []

    @staticmethod
    def extract_salary_amount(salary_text: str) -> int:
        """Extract numeric salary from text"""
        if not salary_text:
            return 0

        # Look for £ amounts
        matches = re.findall(r'£([\d,]+)', salary_text.replace(' ', ''))
        if matches:
            try:
                return int(matches[0].replace(',', ''))
            except ValueError:
                pass

        # Look for numeric ranges
        numbers = re.findall(r'(\d{2,6})', salary_text.replace(',', ''))
        if numbers:
            try:
                return int(numbers[0])
            except ValueError:
                pass

        return 0

    def calculate_match_score(self, job: Job) -> float:
        """Calculate how well a job matches the user profile"""
        score = 0.0
        job_text = f"{job.title} {job.description}".lower()

        # Fintech relevance (base score)
        fintech_matches = sum(1 for keyword in self.fintech_keywords
                              if keyword.lower() in job_text)
        score += fintech_matches * 10

        # Skills matching
        skill_matches = sum(1 for skill in self.user_profile.skills
                            if skill.lower() in job_text)
        score += skill_matches * 15

        # Experience matching
        exp_matches = sum(1 for exp in self.user_profile.experience
                          if exp.lower() in job_text)
        score += exp_matches * 12

        # Qualifications matching
        qual_matches = sum(1 for qual in self.user_profile.qualifications
                           if qual.lower() in job_text)
        score += qual_matches * 8

        # Salary bonus
        if job.salary and self.extract_salary_amount(job.salary) >= self.user_profile.min_salary:
            score += 20

        # Title relevance bonus
        if any(keyword in job.title.lower() for keyword in ['senior', 'lead', 'principal']):
            score += 10

        return min(score, 100.0)  # Cap at 100

    async def search_fintech_jobs(self, limit: int = 20) -> list[Job]:
        """Search for fintech jobs across all configured sites"""
        all_jobs = []

        # Search queries to try
        search_queries = [
            "software engineer",
            "python developer",
            "backend developer",
            "full stack developer",
            "data engineer",
            "DevOps engineer"
        ]

        async with aiohttp.ClientSession() as session:
            for query in search_queries:
                for site in self.job_sites:
                    jobs = await self.crawl_job_site(session, site, query)
                    all_jobs.extend(jobs)

                    # Small delay to be respectful
                    await asyncio.sleep(1)

        # Remove duplicates based on URL
        unique_jobs = []
        seen_urls = set()
        for job in all_jobs:
            if job.url and job.url not in seen_urls:
                seen_urls.add(job.url)
                unique_jobs.append(job)

        # Calculate match scores
        for job in unique_jobs:
            job.match_score = self.calculate_match_score(job)

        # Filter and sort
        relevant_jobs = [job for job in unique_jobs if job.match_score > 20]
        relevant_jobs.sort(key=lambda x: x.match_score, reverse=True)

        return relevant_jobs[:limit]
