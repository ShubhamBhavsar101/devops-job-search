import logging
from datetime import datetime
from typing import List, Optional

from config import LEVER_SLUGS, SEARCH_KEYWORDS
from scraper.base import BaseScraper, JobDict

logger = logging.getLogger(__name__)


class LeverScraper(BaseScraper):
    def __init__(self):
        super().__init__("lever")

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        seen_urls: set = set()

        for slug in LEVER_SLUGS:
            url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
            logger.info("Lever: fetching jobs for %s", slug)
            resp = self.fetch(url)
            if resp is None:
                continue

            try:
                data = resp.json()
            except Exception as e:
                logger.error("Lever: JSON parse error for %s: %s", slug, e)
                continue

            postings = data if isinstance(data, list) else []
            for job in postings:
                title = job.get("text", "") or job.get("title", "")
                if not self._matches_keywords(title):
                    continue
                apply_url = job.get("hostedUrl", "") or job.get("applyUrl", "") or ""
                if apply_url in seen_urls:
                    continue
                seen_urls.add(apply_url)
                company = job.get("country", slug) if slug else slug
                categories = job.get("categories", {}) or {}
                location = (
                    categories.get("location", "") or job.get("location", "") or "India"
                )
                description = (
                    job.get("description", "") or job.get("descriptionText", "") or ""
                )
                posted = self._parse_date(job)
                jobs.append(
                    self.normalize(
                        title=title,
                        company=slug,
                        location=location,
                        apply_url=apply_url,
                        posted_date=posted,
                        description=description,
                    )
                )

        logger.info("Lever: found %d jobs", len(jobs))
        return jobs

    def _matches_keywords(self, title: str) -> bool:
        t = title.lower()
        for kw in SEARCH_KEYWORDS:
            if kw.lower() in t:
                return True
        return False

    def _parse_date(self, job: dict) -> Optional[datetime]:
        ts = job.get("createdAt", None)
        if ts:
            try:
                dt = datetime.fromtimestamp(ts / 1000)
                return dt
            except (ValueError, TypeError, OverflowError):
                pass
        return None
