from dataclasses import dataclass
from typing import Optional


@dataclass
class Job:
    title: str
    company: str
    location: str
    salary: Optional[str]
    description: str
    url: str
    source: str
    match_score: float = 0.0

