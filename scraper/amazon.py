import logging
from datetime import datetime
from typing import List, Optional

from config import SEARCH_KEYWORDS
from scraper.base import BaseScraper, JobDict

logger = logging.getLogger(__name__)


class AmazonScraper(BaseScraper):
    def __init__(self):
        super().__init__("amazon")

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        seen_urls: set = set()

        for keyword in SEARCH_KEYWORDS:
            url = "https://www.amazon.jobs/en-gb/search.json"
            params = {
                "base_query": keyword,
                "loc_query": "India",
                "country": "IND",
                "sort": "recent",
                "page_size": 50,
            }
            logger.info("Amazon: searching '%s'", keyword)
            resp = self.fetch(url, params=params)
            if resp is None:
                continue
            try:
                data = resp.json()
            except Exception as e:
                logger.error("Amazon: JSON parse error: %s", e)
                continue
            for job in data.get("jobs", []):
                title = job.get("title", "")
                if not self._matches_keywords(title):
                    continue
                job_path = job.get("url", "") or job.get("job_path", "") or ""
                if job_path and not job_path.startswith("http"):
                    job_path = f"https://www.amazon.jobs{job_path}"
                if job_path in seen_urls:
                    continue
                seen_urls.add(job_path)
                company = "Amazon"
                location = job.get("location", "") or "India"
                posted = self._parse_date(job)
                description = (
                    job.get("description", "") or job.get("description_short", "") or ""
                )
                jobs.append(
                    self.normalize(
                        title=title,
                        company=company,
                        location=location,
                        apply_url=job_path,
                        posted_date=posted,
                        description=description,
                    )
                )

        logger.info("Amazon: found %d jobs", len(jobs))
        return jobs

    def _matches_keywords(self, title: str) -> bool:
        t = title.lower()
        for kw in SEARCH_KEYWORDS:
            if kw.lower() in t:
                return True
        return False

    def _parse_date(self, job: dict) -> Optional[datetime]:
        ts = job.get("posted_date", None) or job.get("published_date", None)
        if ts:
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass
        return None
