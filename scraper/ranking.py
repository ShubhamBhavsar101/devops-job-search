import hashlib
import logging
from typing import List

from config import KEYWORD_BONUS, LOCATION_PRIORITY, EXCLUDED_LOCATION_KEYWORDS
from scraper.base import JobDict

logger = logging.getLogger(__name__)


def calculate_score(job: JobDict) -> int:
    score = 0
    title_lower = job.get("title", "").lower()
    location_lower = job.get("location", "").lower()
    description_lower = job.get("description", "").lower()
    text = f"{title_lower} {description_lower}"

    # Verify if location contains any international restricted remote keywords
    # but allow it if it also explicitly mentions India
    has_excluded = False
    for ex_key in EXCLUDED_LOCATION_KEYWORDS:
        if ex_key in location_lower:
            if "india" not in location_lower:
                has_excluded = True
                break

    if has_excluded:
        job["score"] = -100
        return -100

    for loc_key, points in LOCATION_PRIORITY.items():
        if loc_key in location_lower:
            score += points
            break

    for kw, points in KEYWORD_BONUS.items():
        if kw in text:
            score += points

    job["score"] = score
    return score


def rank_jobs(jobs: List[JobDict]) -> List[JobDict]:
    for job in jobs:
        calculate_score(job)
    return sorted(jobs, key=lambda j: j.get("score", 0), reverse=True)


def dedup_key(job: JobDict) -> str:
    raw = f"{job.get('title', '')}|{job.get('company', '')}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()


def deduplicate(jobs: List[JobDict]) -> List[JobDict]:
    seen: dict = {}
    for job in jobs:
        key = dedup_key(job)
        existing = seen.get(key)
        if existing is None:
            seen[key] = job
        else:
            calculate_score(job)
            calculate_score(existing)
            if job.get("score", 0) > existing.get("score", 0):
                seen[key] = job

    result = list(seen.values())
    logger.info(
        "Dedup: %d -> %d jobs after removing duplicates", len(jobs), len(result)
    )
    return result


def separate_by_location(jobs: List[JobDict]) -> tuple:
    pune = []
    remote = []
    other = []
    for job in jobs:
        loc = job.get("location", "").lower()
        if "pune" in loc:
            pune.append(job)
        elif any(
            kw in loc for kw in ("remote", "work from home", "wfh", "home office")
        ):
            remote.append(job)
        else:
            other.append(job)
    return pune, remote, other
