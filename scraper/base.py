import logging
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

import config

logger = logging.getLogger(__name__)

JobDict = Dict[str, Any]


class BaseScraper(ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": random.choice(config.USER_AGENTS),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

    @abstractmethod
    def scrape(self) -> List[JobDict]:
        pass

    def fetch(
        self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None
    ) -> Optional[requests.Response]:
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                req_headers = self.session.headers.copy()
                if headers:
                    req_headers.update(headers)
                resp = self.session.get(
                    url,
                    params=params,
                    headers=req_headers,
                    timeout=config.REQUEST_TIMEOUT,
                )
                if resp.status_code == 429:
                    wait = config.BACKOFF_BASE * (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        "%s: rate limited (429) on %s, retrying in %.1fs (attempt %d/%d)",
                        self.source_name,
                        url,
                        wait,
                        attempt,
                        config.MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                if attempt < config.MAX_RETRIES:
                    wait = config.BACKOFF_BASE * (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        "%s: error fetching %s: %s, retrying in %.1fs (attempt %d/%d)",
                        self.source_name,
                        url,
                        e,
                        wait,
                        attempt,
                        config.MAX_RETRIES,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "%s: failed to fetch %s after %d attempts: %s",
                        self.source_name,
                        url,
                        config.MAX_RETRIES,
                        e,
                    )
        return None

    def normalize(
        self,
        title: str,
        company: str,
        location: str,
        apply_url: str,
        posted_date: Optional[datetime] = None,
        description: str = "",
    ) -> JobDict:
        return {
            "title": (title or "").strip(),
            "company": (company or "").strip(),
            "location": (location or "India").strip(),
            "source": self.source_name,
            "posted_date": posted_date,
            "apply_url": (apply_url or "").strip(),
            "description": (description or "")[:500],
            "score": 0,
        }

    def is_recent(self, posted_date: Optional[datetime]) -> bool:
        if posted_date is None:
            return True
        delta = datetime.now(posted_date.tzinfo) - posted_date
        return delta.total_seconds() <= config.LOOKBACK_HOURS * 3600
