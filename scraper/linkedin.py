import logging
import random
import re
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from config import LOCATIONS, SEARCH_KEYWORDS
from scraper.base import BaseScraper, JobDict

logger = logging.getLogger(__name__)

GEO_IDS = {
    "Pune": "102333196",
    "Mumbai": "102333198",
    "Bengaluru": "102333199",
    "Hyderabad": "102333200",
    "Chennai": "102333197",
    "Delhi NCR": "102333203",
    "India": "102713980",
}


COOKIE_DOMAIN = ".linkedin.com"


class LinkedInScraper(BaseScraper):
    def __init__(self):
        super().__init__("linkedin")
        self._init_session()

    def _init_session(self):
        self.session.cookies.set("lang", "v=2&lang=en-us", domain=COOKIE_DOMAIN)
        self.session.cookies.set("JSESSIONID", "ajax:123456789", domain=COOKIE_DOMAIN)
        self.session.cookies.set("bcookie", '"v=2&abc123"', domain=COOKIE_DOMAIN)
        self.session.headers["Accept-Encoding"] = "gzip, deflate"

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        seen_ids: set = set()

        for keyword in SEARCH_KEYWORDS:
            for location in LOCATIONS:
                loc_short = location.split(",")[0].strip()
                geo = GEO_IDS.get(loc_short, "102713980")
                found = self._search(keyword, geo, seen_ids)
                jobs.extend(found)
                time.sleep(random.uniform(0.5, 1.0))

        logger.info("LinkedIn: found %d jobs total", len(jobs))
        return jobs

    def _search(self, keyword: str, geo_id: str, seen_ids: set) -> List[JobDict]:
        found: List[JobDict] = []
        params = {
            "keywords": keyword,
            "location": "India",
            "geoId": geo_id,
            "f_TPR": "r86400",
            "start": 0,
            "sort": "DD",
        }
        url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        full_url = f"{url}?{urlencode(params)}"
        logger.info("LinkedIn: searching '%s' geo=%s", keyword, geo_id)
        resp = self.fetch(full_url)
        if resp is None:
            return found

        jobs_data = self._parse_search_results(resp.text, seen_ids)
        found.extend(jobs_data)
        logger.info(
            "LinkedIn: found %d jobs for '%s' geo=%s", len(jobs_data), keyword, geo_id
        )
        return found

    def _parse_search_results(self, html: str, seen_ids: set) -> List[JobDict]:
        found: List[JobDict] = []
        soup = BeautifulSoup(html, "lxml")

        cards = soup.find_all(
            "div", class_=re.compile(r"base-search-card", re.I)
        ) or soup.find_all("li", class_=re.compile(r"job-search-card", re.I))

        for card in cards:
            try:
                entity_urn = card.get("data-entity-urn", "") or card.get(
                    "data-entity-job-id", ""
                )
                job_id = ""
                m = re.search(r"jobPosting:(\d+)", str(entity_urn))
                if m:
                    job_id = m.group(1)
                if not job_id:
                    m = re.search(r"/jobs/view/(\d+)", str(card))
                    if m:
                        job_id = m.group(1)
                if not job_id:
                    continue
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title_el = card.find(
                    "h3", class_=re.compile(r"base-search-card__title", re.I)
                ) or card.find("a", class_=re.compile(r"base-card__full-link", re.I))
                title = title_el.get_text(strip=True) if title_el else ""

                if not title or not self._matches_keywords(title):
                    continue

                subtitle_el = card.find(
                    "h4", class_=re.compile(r"base-search-card__subtitle", re.I)
                ) or card.find(
                    "span", class_=re.compile(r"base-search-card__subtitle", re.I)
                )
                company = subtitle_el.get_text(strip=True) if subtitle_el else ""

                loc_el = card.find(
                    "span", class_=re.compile(r"job-search-card__location", re.I)
                ) or card.find(
                    "span", class_=re.compile(r"base-search-card__metadata", re.I)
                )
                location = loc_el.get_text(strip=True) if loc_el else "India"

                apply_url = f"https://www.linkedin.com/jobs/view/{job_id}/"

                time_el = card.find("time") or card.find(
                    "span", class_=re.compile(r"listed-date", re.I)
                )
                posted_text = (
                    time_el.get("datetime", "")
                    if time_el and time_el.name == "time"
                    else (time_el.get_text(strip=True) if time_el else "")
                )
                if posted_text and not re.search(r"\d", posted_text):
                    posted_text = ""
                posted = self._parse_relative_date(posted_text) if posted_text else None

                desc_snippet = card.get_text(" ", strip=True)[:300]

                found.append(
                    self.normalize(
                        title=title,
                        company=company,
                        location=location,
                        apply_url=apply_url,
                        posted_date=posted,
                        description=desc_snippet,
                    )
                )
            except Exception as e:
                logger.warning("LinkedIn: error parsing card: %s", e)
                continue

        return found

    def _matches_keywords(self, title: str) -> bool:
        t = title.lower()
        for kw in SEARCH_KEYWORDS:
            if kw.lower() in t:
                return True
        return False

    def _parse_relative_date(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.lower().strip()
        now = datetime.now(timezone.utc)
        m = re.search(r"(\d+)\s*(minute|hour|day|week|month)s?\s*ago", text)
        if m:
            num = int(m.group(1))
            unit = m.group(2)
            if "minute" in unit:
                return now - timedelta(minutes=num)
            elif "hour" in unit:
                return now - timedelta(hours=num)
            elif "day" in unit:
                return now - timedelta(days=num)
            elif "week" in unit:
                return now - timedelta(weeks=num)
            elif "month" in unit:
                return now - timedelta(days=num * 30)
        if "just posted" in text or "moments ago" in text:
            return now - timedelta(hours=1)
        if "today" in text:
            return now - timedelta(hours=6)
        if "hours ago" in text or "hour ago" in text:
            m = re.search(r"(\d+)", text)
            if m:
                return now - timedelta(hours=int(m.group(1)))
        return None
