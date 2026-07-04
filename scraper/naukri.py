import base64
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from curl_cffi import requests as curl_requests

import config
from config import SEARCH_KEYWORDS, LOCATIONS
from scraper.base import BaseScraper, JobDict

logger = logging.getLogger(__name__)

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALrlQ+djR0RjJwBF1xuisHmdFv334MIm
K6LgzJhmLhN7B5yuEyaKoasgXQk3+OQglsOaBxEJ0j5PcTL3nbOvt80CAwEAAQ==
-----END PUBLIC KEY-----"""


def _generate_nkparam(page_type: str = "srp") -> str:
    key = RSA.import_key(PUBLIC_KEY)
    cipher = PKCS1_v1_5.new(key)
    ts = int(time.time() * 1000)
    plaintext = f"v0|{ts}|121_{page_type}"
    encrypted = cipher.encrypt(plaintext.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def _extract_city(cityfield: str) -> str:
    if not cityfield:
        return "India"
    lower = cityfield.lower()
    for location in config.LOCATIONS:
        loc_short = location.split(",")[0].strip()
        if loc_short.lower() in lower:
            return loc_short
    if "remote" in lower or "work from home" in lower or "wfh" in lower:
        return "Remote"
    parts = re.split(r"[,/]", cityfield)
    for part in parts:
        part = part.strip()
        if (
            part
            and len(part) > 2
            and part != "india"
            and not part.startswith("anywhere")
        ):
            return part.title()
    return "India"


class NaukriScraper(BaseScraper):
    def __init__(self):
        super().__init__("naukri")
        self._curl_session = curl_requests.Session(impersonate="chrome")

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        seen_urls: set = set()

        for keyword in SEARCH_KEYWORDS:
            for location in LOCATIONS:
                loc_short = location.split(",")[0].strip()
                logger.info("Naukri: searching '%s' in '%s'", keyword, loc_short)
                found = self._search(keyword, loc_short, seen_urls)
                jobs.extend(found)
                time.sleep(0.5)

        logger.info("Naukri: found %d jobs total", len(jobs))
        return jobs

    def _search(self, keyword: str, location: str, seen_urls: set) -> List[JobDict]:
        found: List[JobDict] = []

        params = {
            "keyword": keyword,
            "location": location,
            "pageNo": 1,
            "noOfResults": config.MAX_JOBS_PER_SOURCE,
        }

        headers = {
            "accept": "application/json",
            "appid": "109",
            "systemid": "Naukri",
            "nkparam": _generate_nkparam("srp"),
        }

        try:
            resp = self._curl_session.get(
                "https://www.naukri.com/jobapi/v1/search",
                params=params,
                headers=headers,
                timeout=config.REQUEST_TIMEOUT,
            )
        except Exception as e:
            logger.warning(
                "Naukri: request failed for '%s' in '%s': %s", keyword, location, e
            )
            return found

        if resp.status_code != 200:
            logger.warning(
                "Naukri: %d for '%s' in '%s': %s",
                resp.status_code,
                keyword,
                location,
                resp.text[:200],
            )
            return found

        try:
            data = resp.json()
        except Exception as e:
            logger.error("Naukri: JSON parse error: %s", e)
            return found

        for job in data.get("list", []):
            title = job.get("post") or ""
            if not title or not self._matches_keywords(title):
                continue

            company = job.get("companyName") or ""
            apply_url = job.get("urlStr") or ""
            if not apply_url:
                continue
            if apply_url in seen_urls:
                continue
            seen_urls.add(apply_url)

            location_raw = _extract_city(job.get("cityfield") or "")

            description = job.get("jobDesc") or ""
            if job.get("keywords"):
                description = f"{description}\nSkills: {job['keywords']}"

            posted_raw = job.get("addDate") or ""
            posted = self._parse_posted(posted_raw)

            found.append(
                self.normalize(
                    title=title,
                    company=company,
                    location=location_raw,
                    apply_url=apply_url,
                    posted_date=posted,
                    description=description,
                )
            )

        return found

    def _matches_keywords(self, title: str) -> bool:
        t = title.lower()
        for kw in SEARCH_KEYWORDS:
            if kw.lower() in t:
                return True
        return False

    def _parse_posted(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        text = text.lower().strip()
        now = datetime.now(timezone.utc)

        m = re.search(
            r"(\d+)\s*(day|days|hour|hours|min|mins|minute|minutes|week|weeks|month|months)\s*ago",
            text,
        )
        if m:
            num = int(m.group(1))
            unit = m.group(2)
            if unit.startswith("min"):
                return now - timedelta(minutes=num)
            elif unit.startswith("hour"):
                return now - timedelta(hours=num)
            elif unit.startswith("day"):
                return now - timedelta(days=num)
            elif unit.startswith("week"):
                return now - timedelta(weeks=num)
            elif unit.startswith("month"):
                return now - timedelta(days=num * 30)
        if "today" in text:
            return now - timedelta(hours=6)
        if "just now" in text or "moments" in text:
            return now - timedelta(minutes=5)
        if "yesterday" in text:
            return now - timedelta(days=1)

        try:
            parsed = datetime.strptime(text, "%d %b")
            parsed = parsed.replace(year=now.year, tzinfo=timezone.utc)
            days_ago = (now - parsed).days
            if days_ago > 0:
                return now - timedelta(days=days_ago)
            return now - timedelta(hours=6)
        except (ValueError, TypeError):
            pass

        return None
