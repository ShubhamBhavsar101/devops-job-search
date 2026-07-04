import logging
from datetime import datetime, timezone
from typing import List, Optional

from config import ASHBY_BOARDS, SEARCH_KEYWORDS
from scraper.base import BaseScraper, JobDict

logger = logging.getLogger(__name__)


class AshbyScraper(BaseScraper):
    def __init__(self):
        super().__init__("ashby")

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        seen_urls: set = set()

        for board in ASHBY_BOARDS:
            url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
            logger.info("Ashby: fetching jobs for %s", board)
            resp = self.fetch(url)
            if resp is None:
                continue

            try:
                data = resp.json()
            except Exception as e:
                logger.error("Ashby: JSON parse error for %s: %s", board, e)
                continue

            for job in data.get("jobs", []):
                title = job.get("title", "")
                if not self._matches_keywords(title):
                    continue
                apply_url = job.get("applyUrl", "") or ""
                if apply_url in seen_urls:
                    continue
                seen_urls.add(apply_url)
                location = job.get("location", "") or "India"
                description = (
                    job.get("descriptionHtml", "") or job.get("description", "") or ""
                )
                posted = self._extract_date(job)
                jobs.append(
                    self.normalize(
                        title=title,
                        company=board,
                        location=location,
                        apply_url=apply_url,
                        posted_date=posted,
                        description=description,
                    )
                )

        logger.info("Ashby: found %d jobs", len(jobs))
        return jobs

    def _matches_keywords(self, title: str) -> bool:
        t = title.lower()
        for kw in SEARCH_KEYWORDS:
            if kw.lower() in t:
                return True
        return False

    def _extract_date(self, job: dict) -> Optional[datetime]:
        ts = job.get("postedAt", None)
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return dt
            except (ValueError, TypeError):
                try:
                    dt = datetime.fromtimestamp(ts / 1000)
                    return dt
                except (ValueError, TypeError, OverflowError):
                    pass
        return None
