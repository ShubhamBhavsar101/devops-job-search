import csv
import logging
import os
from datetime import datetime
from typing import List

from scraper.base import JobDict

logger = logging.getLogger(__name__)


def jobs_to_csv(jobs: List[JobDict], filepath: str) -> str:
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    fieldnames = [
        "Company",
        "Role",
        "Location",
        "Source",
        "Posted",
        "Apply URL",
        "Score",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for job in jobs:
            posted = job.get("posted_date")
            if posted and isinstance(posted, datetime):
                posted_str = posted.strftime("%Y-%m-%d %H:%M")
            elif posted:
                posted_str = str(posted)
            else:
                posted_str = ""
            writer.writerow(
                {
                    "Company": job.get("company", ""),
                    "Role": job.get("title", ""),
                    "Location": job.get("location", ""),
                    "Source": job.get("source", ""),
                    "Posted": posted_str,
                    "Apply URL": job.get("apply_url", ""),
                    "Score": job.get("score", 0),
                }
            )
    logger.info("CSV exported to %s (%d rows)", filepath, len(jobs))
    return filepath
