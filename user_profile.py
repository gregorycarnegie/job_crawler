from dataclasses import dataclass


@dataclass
class UserProfile:
    skills: list[str]
    experience: list[str]
    qualifications: list[str]
    min_salary: int = 50000
