import logging
from datetime import datetime, timezone
from typing import List, Optional

from config import GREENHOUSE_BOARDS, SEARCH_KEYWORDS
from scraper.base import BaseScraper, JobDict

logger = logging.getLogger(__name__)


class GreenhouseScraper(BaseScraper):
    def __init__(self):
        super().__init__("greenhouse")

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        seen_urls: set = set()

        for company, board_token in GREENHOUSE_BOARDS.items():
            url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
            logger.info(
                "Greenhouse: fetching jobs for %s (board: %s)", company, board_token
            )
            resp = self.fetch(url, params={"content": "true"})
            if resp is None:
                continue

            try:
                data = resp.json()
            except Exception as e:
                logger.error("Greenhouse: JSON parse error for %s: %s", company, e)
                continue

            for job in data.get("jobs", []):
                title = job.get("title", "")
                if not self._matches_keywords(title):
                    continue
                apply_url = self._get_apply_url(job, board_token)
                if apply_url in seen_urls:
                    continue
                seen_urls.add(apply_url)
                location = (
                    job.get("office", {}).get("name", "")
                    or job.get("location", {}).get("name", "")
                    or "India"
                )
                metadata = job.get("metadata", [])
                posted = self._extract_posted_date(job, metadata)
                description = job.get("content", "") or ""
                jobs.append(
                    self.normalize(
                        title=title,
                        company=company,
                        location=location,
                        apply_url=apply_url,
                        posted_date=posted,
                        description=description,
                    )
                )

        logger.info("Greenhouse: found %d jobs", len(jobs))
        return jobs

    def _matches_keywords(self, title: str) -> bool:
        t = title.lower()
        for kw in SEARCH_KEYWORDS:
            if kw.lower() in t:
                return True
        return False

    def _get_apply_url(self, job: dict, board_token: str) -> str:
        urls = job.get("absolute_url", "") or ""
        if urls:
            return urls
        job_id = job.get("id", "")
        return f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}"

    def _extract_posted_date(self, job: dict, metadata: list) -> Optional[datetime]:
        updated_at = job.get("updated_at", "")
        if updated_at:
            try:
                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                return dt
            except (ValueError, TypeError):
                pass
        for meta in metadata:
            if meta.get("name", "").lower() in ("date posted", "posted date", "date"):
                val = meta.get("value", "")
                if val:
                    try:
                        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                        return dt
                    except (ValueError, TypeError):
                        pass
        return None
