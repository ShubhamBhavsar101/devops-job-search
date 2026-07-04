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
    "Bangalore": "102333199",
    "Hyderabad": "102333200",
    "Chennai": "102333197",
    "Delhi": "102333203",
    "India": "102713980",
}


class LinkedInScraper(BaseScraper):
    def __init__(self):
        super().__init__("linkedin")

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        seen_ids: set = set()

        for keyword in SEARCH_KEYWORDS:
            for location in LOCATIONS:
                loc_short = location.split(",")[0].strip()
                geo = GEO_IDS.get(loc_short, GEO_IDS.get("India"))
                jobs_found = self._search_keyword(keyword, geo, seen_ids)
                jobs.extend(jobs_found)
                time.sleep(random.uniform(1.0, 2.5))

        logger.info("LinkedIn: found %d jobs total", len(jobs))
        return jobs

    def _search_keyword(
        self, keyword: str, geo_id: str, seen_ids: set
    ) -> List[JobDict]:
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

        job_ids = self._extract_job_ids(resp.text)
        logger.info("LinkedIn: found %d job IDs for '%s'", len(job_ids), keyword)

        for idx, job_id in enumerate(job_ids):
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            detail_url = (
                f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
            )
            time.sleep(random.uniform(0.5, 1.5))
            detail_resp = self.fetch(detail_url)
            if detail_resp is None:
                continue
            job = self._parse_job_detail(detail_resp.text, keyword)
            if job:
                found.append(job)
            if len(found) >= 25:
                break

        return found

    def _extract_job_ids(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "lxml")
        ids = set()
        for link in soup.find_all("a", href=True):
            m = re.search(r"/jobs/view/(\d+)", link["href"])
            if m:
                ids.add(m.group(1))
        for div in soup.find_all("div", {"data-job-id": re.compile(r"\d+")}):
            ids.add(div["data-job-id"])
        for li in soup.find_all("li", {"data-entity-job-id": re.compile(r"\d+")}):
            ids.add(li["data-entity-job-id"])
        return list(ids)

    def _parse_job_detail(self, html: str, keyword: str) -> Optional[JobDict]:
        soup = BeautifulSoup(html, "lxml")
        title_el = soup.find("h1") or soup.find(
            class_=re.compile(r"top-card-layout__title", re.I)
        )
        title = title_el.get_text(strip=True) if title_el else ""

        if not title or not self._matches_keywords(title):
            return None

        company_el = (
            soup.find(class_=re.compile(r"topcard__org-name-link", re.I))
            or soup.find(class_=re.compile(r"top-card-layout__second-subline", re.I))
            or soup.find(
                "a", {"data-tracking-control-name": re.compile(r"public_jobs.*company")}
            )
        )
        company = company_el.get_text(strip=True) if company_el else ""

        loc_el = soup.find(
            class_=re.compile(r"topcard__flavor--bullet", re.I)
        ) or soup.find(class_=re.compile(r"top-card-layout__first-subline", re.I))
        location = loc_el.get_text(strip=True) if loc_el else "India"

        desc_el = soup.find(class_=re.compile(r"description__text", re.I)) or soup.find(
            class_=re.compile(r"show-more-less-html", re.I)
        )
        description = desc_el.get_text(strip=True)[:500] if desc_el else ""

        posted_text = ""
        posted_el = soup.find(class_=re.compile(r"posted-time-ago", re.I)) or soup.find(
            class_=re.compile(r"topcard__flavor--metadata-posted", re.I)
        )
        if posted_el:
            posted_text = posted_el.get_text(strip=True)

        posted_date = self._parse_relative_date(posted_text)

        apply_url = ""
        apply_el = soup.find("a", {"data-job-id": re.compile(r"\d+")}, href=True)
        if apply_el:
            apply_url = apply_el["href"]
        if not apply_url:
            apply_el = soup.find(
                "a", class_=re.compile(r"apply-button", re.I), href=True
            )
            if apply_el:
                apply_url = apply_el["href"]

        return self.normalize(
            title=title,
            company=company,
            location=location,
            apply_url=apply_url,
            posted_date=posted_date,
            description=description,
        )

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
        m = re.search(r"(\d+)\s*(minutes|hours|days|weeks|months)\s*ago", text)
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
        if "just posted" in text or "moments ago" in text or "recently" in text:
            return now - timedelta(hours=1)
        if "today" in text:
            return now - timedelta(hours=6)
        return None
