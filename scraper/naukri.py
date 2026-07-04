import logging
import math
import random
import re
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

import config
from config import SEARCH_KEYWORDS, LOCATIONS
from scraper.base import BaseScraper, JobDict

logger = logging.getLogger(__name__)


class NaukriScraper(BaseScraper):
    def __init__(self):
        super().__init__("naukri")
        self._init_session()

    def _init_session(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.naukri.com/",
        }
        self.session.headers.update(headers)
        self.session.get(
            "https://www.naukri.com/",
            timeout=config.REQUEST_TIMEOUT,
        )

    def scrape(self) -> List[JobDict]:
        jobs: List[JobDict] = []
        seen_urls: set = set()

        for keyword in SEARCH_KEYWORDS:
            for location in LOCATIONS:
                loc_short = location.split(",")[0].strip()
                logger.info("Naukri: searching '%s' in '%s'", keyword, loc_short)
                found = self._search_page(keyword, loc_short, seen_urls, page=1)
                jobs.extend(found)
                time.sleep(random.uniform(0.5, 1.0))

        logger.info("Naukri: found %d jobs total", len(jobs))
        return jobs

    def _search_page(
        self, keyword: str, location: str, seen_urls: set, page: int = 1
    ) -> List[JobDict]:
        found: List[JobDict] = []
        kw_encoded = quote(keyword)
        loc_encoded = quote(f"{location}, India")
        url = (
            f"https://www.naukri.com/{kw_encoded}-jobs-in-{loc_encoded}"
            f"?k={kw_encoded}&l={loc_encoded}"
            f"&ctcFilter=0&fromAge=1"
        )
        if page > 1:
            url += f"&pageNo={page}"

        resp = self.fetch(url)
        if resp is None:
            return found

        soup = BeautifulSoup(resp.text, "lxml")
        job_cards = (
            soup.find_all("div", class_=re.compile(r"jobTuple", re.I))
            or soup.find_all("article", class_=re.compile(r"job", re.I))
            or soup.find_all("div", class_=re.compile(r"cust-job-tuple", re.I))
        )

        if not job_cards:
            alt_data = self._extract_next_data(soup)
            if alt_data:
                return self._parse_next_data(alt_data, seen_urls)

        for card in job_cards:
            job = self._parse_card(card, keyword)
            if job and job["apply_url"] not in seen_urls:
                seen_urls.add(job["apply_url"])
                found.append(job)

        return found

    def _parse_card(self, card, keyword: str) -> Optional[JobDict]:
        try:
            title_el = card.find("a", class_=re.compile(r"title", re.I)) or card.find(
                "a", class_=re.compile(r"jobTitle", re.I)
            )
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or not self._matches_keywords(title):
                return None

            apply_url = title_el.get("href", "") if title_el else ""
            if apply_url and not apply_url.startswith("http"):
                apply_url = "https://www.naukri.com" + apply_url

            company_el = (
                card.find("a", class_=re.compile(r"subTitle", re.I))
                or card.find("a", class_=re.compile(r"company", re.I))
                or card.find("a", class_=re.compile(r"comp-name", re.I))
                or card.find("span", class_=re.compile(r"comp-name", re.I))
            )
            company = company_el.get_text(strip=True) if company_el else ""

            loc_el = (
                card.find("span", class_=re.compile(r"loc", re.I))
                or card.find("li", class_=re.compile(r"location", re.I))
                or card.find("span", class_=re.compile(r"location", re.I))
            )
            location = loc_el.get_text(strip=True) if loc_el else "India"

            desc_el = card.find(
                "div", class_=re.compile(r"job-desc", re.I)
            ) or card.find("span", class_=re.compile(r"desc", re.I))
            description = desc_el.get_text(strip=True)[:500] if desc_el else ""

            posted = self._parse_posted_date(card)
            return self.normalize(
                title=title,
                company=company,
                location=location,
                apply_url=apply_url,
                posted_date=posted,
                description=description,
            )
        except Exception as e:
            logger.warning("Naukri: error parsing card: %s", e)
            return None

    def _parse_posted_date(self, card) -> Optional[datetime]:
        for cls_pattern in ["posted", "time", "date", "ago", "day"]:
            el = card.find("span", class_=re.compile(cls_pattern, re.I))
            if el:
                text = el.get_text(strip=True)
                return self._parse_relative(text)
        return None

    def _parse_relative(self, text: str) -> Optional[datetime]:
        text = text.lower().strip()
        now = datetime.now(timezone.utc)
        m = re.search(
            r"(\d+)\s*(min|minute|minutes|hour|hours|day|days|week|weeks|month|months)\s*ago",
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
            return now - timedelta(minutes=10)
        if "yesterday" in text:
            return now - timedelta(days=1)
        return None

    def _matches_keywords(self, title: str) -> bool:
        t = title.lower()
        for kw in SEARCH_KEYWORDS:
            if kw.lower() in t:
                return True
        return False

    def _extract_next_data(self, soup) -> Optional[dict]:
        for script in soup.find_all("script"):
            if script.get("id") == "__NEXT_DATA__" or "__NEXT_DATA__" in (
                script.get("id") or ""
            ):
                try:
                    import json

                    return json.loads(script.string)
                except Exception:
                    pass
        return None

    def _parse_next_data(self, data: dict, seen_urls: set) -> List[JobDict]:
        found = []
        try:
            props = data.get("props", {}).get("pageProps", {})
            results = props.get("results", []) or props.get("searchResults", []) or []
            for item in results:
                title = item.get("title", "") or item.get("jobTitle", "")
                if not title or not self._matches_keywords(title):
                    continue
                apply_url = (
                    item.get("url", "")
                    or item.get("applyUrl", "")
                    or item.get("jdURL", "")
                )
                if apply_url in seen_urls:
                    continue
                company = item.get("company", "") or item.get("companyName", "")
                location = item.get("location", "") or item.get("place", "") or "India"
                description = item.get("description", "") or ""
                posted = None
                ts = item.get("createdDate", None) or item.get("postedOn", None)
                if ts:
                    try:
                        posted = datetime.fromtimestamp(ts / 1000)
                    except (ValueError, TypeError, OverflowError):
                        pass
                seen_urls.add(apply_url)
                found.append(
                    self.normalize(
                        title=title,
                        company=company,
                        location=location,
                        apply_url=apply_url,
                        posted_date=posted,
                        description=description,
                    )
                )
        except Exception as e:
            logger.warning("Naukri: error parsing __NEXT_DATA__: %s", e)
        return found
