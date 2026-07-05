import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from curl_cffi import requests as curl_requests

import config
from config import SEARCH_KEYWORDS, LOCATIONS
from scraper.base import BaseScraper, JobDict

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    def __init__(self):
        super().__init__("indeed")
        self._curl_session = curl_requests.Session(impersonate="chrome")

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        seen_urls: set = set()

        days = max(1, config.LOOKBACK_HOURS // 24)

        for keyword in SEARCH_KEYWORDS:
            for location in LOCATIONS:
                loc_short = location.split(",")[0].strip()
                logger.info("Indeed: searching '%s' in '%s'", keyword, loc_short)
                found = self._search(keyword, loc_short, days, seen_urls)
                jobs.extend(found)
                time.sleep(0.3)

        logger.info("Indeed: found %d jobs total", len(jobs))
        return jobs

    def _search(
        self, keyword: str, location: str, days: int, seen_urls: set
    ) -> List[JobDict]:
        found: List[JobDict] = []

        params = {"q": keyword, "l": location, "fromage": days}

        try:
            target_url = "https://in.indeed.com/jobs"
            if config.SCRAPERAPI_KEY:
                logger.info("Indeed: Using ScraperAPI proxy")
                from urllib.parse import urlencode
                actual_url = target_url + "?" + urlencode(params)
                resp = self._curl_session.get(
                    "http://api.scraperapi.com",
                    params={"api_key": config.SCRAPERAPI_KEY, "url": actual_url},
                    timeout=60,
                )
            else:
                logger.info("Indeed: Using direct connection (No ScraperAPI key found)")
                resp = self._curl_session.get(
                    target_url,
                    params=params,
                    timeout=60,
                )
        except Exception as e:
            logger.warning(
                "Indeed: request failed for '%s' in '%s': %s", keyword, location, e
            )
            return found

        if resp.status_code != 200:
            logger.warning(
                "Indeed: %d for '%s' in '%s'", resp.status_code, keyword, location
            )
            return found

        jobs_data = self._extract_jobs_json(resp.text)
        if not jobs_data:
            logger.warning(
                "Indeed: no job cards found for '%s' in '%s'", keyword, location
            )
            return found

        for job in jobs_data:
            title = self._get_field(job, ("title",))
            if not title or not self._matches_keywords(title):
                continue

            company = self._get_field(job, ("company", "companyName")) or ""
            loc_str = (
                self._get_field(
                    job, ("location", "companyLocation", "formattedLocation")
                )
                or ""
            )
            location_raw = self._extract_city(loc_str)

            url_path = (
                self._get_field(job, ("viewJobLink", "link", "url", "jobLink")) or ""
            )
            if not url_path:
                continue
            apply_url = (
                f"https://in.indeed.com{url_path}"
                if url_path.startswith("/")
                else url_path
            )

            if apply_url in seen_urls:
                continue
            seen_urls.add(apply_url)

            posted_raw = (
                self._get_field(
                    job,
                    ("formattedRelativeTime", "formattedRelativeDate", "postedDate"),
                )
                or ""
            )
            posted = self._parse_posted(posted_raw)

            snippet = (
                self._get_field(job, ("snippet", "description", "jobDescription")) or ""
            )

            found.append(
                self.normalize(
                    title=title,
                    company=company,
                    location=location_raw,
                    apply_url=apply_url,
                    posted_date=posted,
                    description=snippet,
                )
            )

        return found

    def _extract_jobs_json(self, html: str) -> Optional[List[dict]]:
        pattern = r'window\.mosaic\.providerData\[["\']mosaic-provider-jobcards["\']\]\s*=\s*(\{.+?\});'
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

        results = None
        for path in (
            ["metaData", "mosaicProviderJobCardsModel", "results"],
            ["metaData", "mosaicProviderJobCardsModel", "jobCards"],
            ["results"],
        ):
            cur = data
            for key in path:
                cur = cur.get(key) if isinstance(cur, dict) else None
                if cur is None:
                    break
            if isinstance(cur, list):
                results = cur
                break

        if not isinstance(results, list) or not results:
            return None

        extracted = []
        for item in results:
            job = item.get("job") if isinstance(item, dict) and "job" in item else item
            if isinstance(job, dict):
                extracted.append(job)
        return extracted or None

    def _get_field(self, job: dict, keys: tuple) -> str:
        for key in keys:
            val = job.get(key)
            if val:
                return str(val).strip()
        return ""

    def _matches_keywords(self, title: str) -> bool:
        t = title.lower()
        for kw in SEARCH_KEYWORDS:
            if kw.lower() in t:
                return True
        return False

    def _extract_city(self, location_raw: str) -> str:
        if not location_raw:
            return "India"
        lower = location_raw.lower()
        for location in LOCATIONS:
            loc_short = location.split(",")[0].strip()
            if loc_short.lower() in lower:
                return loc_short
        if "remote" in lower or "work from home" in lower or "wfh" in lower:
            return "Remote"
        return location_raw.strip()

    def _parse_posted(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.lower().strip()
        now = datetime.now(timezone.utc)

        if "just posted" in text:
            return now - timedelta(hours=2)
        if "today" in text:
            return now - timedelta(hours=6)
        if "yesterday" in text:
            return now - timedelta(days=1)

        m = re.search(r"(\d+)\s*\+?\s*(day|days|hour|hours)\s*ago", text)
        if m:
            num = int(m.group(1))
            unit = m.group(2)
            if unit.startswith("hour"):
                return now - timedelta(hours=num)
            return now - timedelta(days=num)

        m = re.search(r"30\+ days", text)
        if m:
            return now - timedelta(days=30)

        return None
