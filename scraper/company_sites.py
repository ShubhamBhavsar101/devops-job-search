import json
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

from bs4 import BeautifulSoup

from config import SEARCH_KEYWORDS
from scraper.base import BaseScraper, JobDict

logger = logging.getLogger(__name__)


class GoogleCareersScraper(BaseScraper):
    def __init__(self):
        super().__init__("google_careers")
        self.session.headers.update(
            {
                "Accept": "application/json, text/plain, */*",
            }
        )

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        url = "https://careers.google.com/api/v3/search"
        params = {
            "employment_type": "FULL_TIME",
            "page_size": 50,
        }
        resp = self.fetch(url, params=params)
        if resp is None:
            return jobs
        try:
            data = resp.json()
        except Exception as e:
            logger.error("Google Careers: JSON parse error: %s", e)
            return jobs

        for job in data.get("jobs", []) or data.get("searchResults", []):
            title = job.get("title", "")
            if not self._matches_keywords(title):
                continue
            locations = job.get("locations", [])
            location = (
                ", ".join(l.get("display", "") for l in locations)
                if locations
                else "India"
            )
            apply_url = job.get("applyUrl", "") or job.get("url", "") or ""
            company = "Google"
            posted = self._parse_date(job)
            description = job.get("description", "") or ""
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
        logger.info("Google Careers: found %d jobs", len(jobs))
        return jobs

    def _matches_keywords(self, title: str) -> bool:
        t = title.lower()
        for kw in SEARCH_KEYWORDS:
            if kw.lower() in t:
                return True
        return False

    def _parse_date(self, job: dict) -> Optional[datetime]:
        ts = job.get("createTime", None) or job.get("publishTime", None)
        if ts:
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass
        return None


class MicrosoftCareersScraper(BaseScraper):
    def __init__(self):
        super().__init__("microsoft_careers")
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        url = "https://gcsservices.careers.microsoft.com/search/api/v1/search"
        for keyword in SEARCH_KEYWORDS:
            payload = {
                "q": keyword,
                "l": "en_US",
                "pg": 1,
                "pgSize": 50,
            }
            resp = self._fetch_post(url, payload)
            if resp is None:
                continue
            try:
                data = resp.json()
            except Exception as e:
                logger.error("Microsoft Careers: JSON parse error: %s", e)
                continue
            result = data.get("operationResult", {}).get("result", {})
            for job in result.get("jobs", []):
                title = job.get("title", "")
                if not self._matches_keywords(title):
                    continue
                apply_url = (
                    job.get("applyUrl", "")
                    or f"https://careers.microsoft.com/us/en/job/{job.get('jobId', '')}"
                )
                company = "Microsoft"
                locs = job.get("properties", {}).get("locations", [])
                location = ", ".join(locs) if locs else "India"
                posted = self._parse_date(job)
                description = job.get("description", "") or ""
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
        logger.info("Microsoft Careers: found %d jobs", len(jobs))
        return jobs

    def _matches_keywords(self, title: str) -> bool:
        t = title.lower()
        for kw in SEARCH_KEYWORDS:
            if kw.lower() in t:
                return True
        return False

    def _parse_date(self, job: dict) -> Optional[datetime]:
        ts = job.get("postingDate", None) or job.get("postedDate", None)
        if ts:
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                try:
                    return datetime.fromtimestamp(ts / 1000)
                except (ValueError, TypeError, OverflowError):
                    pass
        return None

    def _fetch_post(self, url: str, payload: dict) -> Optional[object]:
        import requests

        for attempt in range(1, 4):
            try:
                resp = self.session.post(
                    url,
                    json=payload,
                    timeout=15,
                )
                if resp.status_code == 429:
                    import time, random

                    time.sleep(2**attempt + random.uniform(0, 1))
                    continue
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                if attempt < 3:
                    import time, random

                    time.sleep(2**attempt + random.uniform(0, 1))
                else:
                    logger.error("Microsoft Careers POST failed: %s", e)
        return None


class AmazonCareersScraper(BaseScraper):
    def __init__(self):
        super().__init__("amazon_careers")
        self.session.headers.update(
            {
                "Accept": "application/json",
            }
        )

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        for keyword in SEARCH_KEYWORDS:
            url = "https://www.amazon.jobs/en-gb/search.json"
            params = {
                "base_query": keyword,
                "loc_query": "India",
                "country": "IND",
                "sort": "recent",
                "page_size": 50,
            }
            resp = self.fetch(url, params=params)
            if resp is None:
                continue
            try:
                data = resp.json()
            except Exception as e:
                logger.error("Amazon Careers: JSON parse error: %s", e)
                continue
            for job in data.get("jobs", []):
                title = job.get("title", "")
                if not self._matches_keywords(title):
                    continue
                job_path = job.get("url", "") or job.get("job_path", "") or ""
                if job_path and not job_path.startswith("http"):
                    job_path = f"https://www.amazon.jobs{job_path}"
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
        logger.info("Amazon Careers: found %d jobs", len(jobs))
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


class OracleCareersScraper(BaseScraper):
    def __init__(self):
        super().__init__("oracle_careers")
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        url = "https://oracle.wd5.myworkdayjobs.com/wday/cxs/oracle/OracleCareers/jobs"
        for keyword in SEARCH_KEYWORDS:
            payload = {
                "limit": 50,
                "offset": 0,
                "searchText": keyword,
                "filters": {"locationCountry": ["bc33aa3152ec42d4995f4791a106ed09"]},
            }
            resp = self._fetch_post(url, payload)
            if resp is None:
                continue
            try:
                data = resp.json()
            except Exception as e:
                logger.error("Oracle Careers: JSON parse error: %s", e)
                continue
            for job in data.get("jobs", []):
                title = job.get("title", "")
                if not self._matches_keywords(title):
                    continue
                ext_path = (
                    job.get("externalPath", "")
                    or job.get("bulletFields", [None])[0]
                    or ""
                )
                apply_url = (
                    job.get("applyUrl", "")
                    or f"https://oracle.wd5.myworkdayjobs.com/en-US/OracleCareers{ext_path}"
                )
                company = "Oracle"
                location = (
                    job.get("locationsText", "") or job.get("location", "") or "India"
                )
                posted = self._parse_date(job)
                description = (
                    job.get("description", "") or job.get("jobDescription", "") or ""
                )
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
        logger.info("Oracle Careers: found %d jobs", len(jobs))
        return jobs

    def _matches_keywords(self, title: str) -> bool:
        t = title.lower()
        for kw in SEARCH_KEYWORDS:
            if kw.lower() in t:
                return True
        return False

    def _parse_date(self, job: dict) -> Optional[datetime]:
        ts = job.get("postedDate", None) or job.get("publicationDate", None)
        if ts:
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                try:
                    return datetime.fromtimestamp(ts / 1000)
                except (ValueError, TypeError, OverflowError):
                    pass
        return None

    def _fetch_post(self, url: str, payload: dict) -> Optional[object]:
        import requests

        for attempt in range(1, 4):
            try:
                resp = self.session.post(
                    url,
                    json=payload,
                    timeout=15,
                )
                if resp.status_code == 429:
                    import time, random

                    time.sleep(2**attempt + random.uniform(0, 1))
                    continue
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                if attempt < 3:
                    import time, random

                    time.sleep(2**attempt + random.uniform(0, 1))
                else:
                    logger.error("Oracle Careers POST failed: %s", e)
        return None
