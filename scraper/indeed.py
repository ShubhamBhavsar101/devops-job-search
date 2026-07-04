import logging
from datetime import datetime, timezone
from typing import List, Optional

import feedparser

from config import SEARCH_KEYWORDS, LOCATIONS
from scraper.base import BaseScraper, JobDict

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    def __init__(self):
        super().__init__("indeed")

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        seen_urls: set = set()

        for keyword in SEARCH_KEYWORDS:
            for location in LOCATIONS:
                loc_short = location.split(",")[0].strip()
                url = (
                    "https://rss.indeed.com/rss"
                    f"?q={keyword}"
                    f"&l={loc_short},+India"
                    "&sort=date"
                )
                logger.info("Indeed: fetching RSS for '%s' in '%s'", keyword, loc_short)
                resp = self.fetch(url)
                if resp is None:
                    continue

                feed = feedparser.parse(resp.text)
                for entry in feed.entries:
                    link = entry.get("link", "")
                    if link in seen_urls:
                        continue
                    title = entry.get("title", "")
                    if not self._matches_keywords(title):
                        continue
                    summary = entry.get("summary", "")
                    company = self._extract_company(entry)
                    location_raw = self._extract_location(entry, summary)
                    posted = self._parse_date(entry.get("published", ""))
                    seen_urls.add(link)
                    jobs.append(
                        self.normalize(
                            title=title,
                            company=company,
                            location=location_raw,
                            apply_url=link,
                            posted_date=posted,
                            description=summary,
                        )
                    )

        logger.info("Indeed: found %d jobs", len(jobs))
        return jobs

    def _matches_keywords(self, title: str) -> bool:
        t = title.lower()
        for kw in SEARCH_KEYWORDS:
            if kw.lower() in t:
                return True
        return False

    def _extract_company(self, entry) -> str:
        source = entry.get("source", {})
        if isinstance(source, dict):
            return source.get("value", "") or source.get("content", "")
        return str(source) if source else ""

    def _extract_location(self, entry, summary: str) -> str:
        loc = getattr(entry, "geoiz_place", None) or ""
        if not loc:
            loc = getattr(entry, "location", None) or ""
        if not loc:
            for line in summary.split("<br")[0:3]:
                cleaned = line.strip().replace("\n", "")
                if "location" in cleaned.lower():
                    parts = cleaned.split(":", 1)
                    if len(parts) > 1:
                        loc = parts[1].strip()
                        break
        return loc or "India"

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
            return dt
        except (ValueError, TypeError):
            try:
                dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
                return dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                return None
