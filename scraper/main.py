import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
from scraper.amazon import AmazonScraper
from scraper.ashby import AshbyScraper
from scraper.email_template import render_html_report, send_email
from scraper.exporter import jobs_to_csv
from scraper.indeed import IndeedScraper
from scraper.linkedin import LinkedInScraper
from scraper.naukri import NaukriScraper
from scraper.ranking import deduplicate, rank_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def run_scraper(scraper) -> list:
    name = scraper.source_name
    logger.info("Starting scraper: %s", name)
    try:
        start = time.time()
        jobs = scraper.scrape()
        elapsed = time.time() - start
        logger.info("Scraper %s: %d jobs in %.1fs", name, len(jobs), elapsed)
        return jobs
    except Exception as e:
        logger.error("Scraper %s failed: %s", name, e, exc_info=True)
        return []


def main():
    logger.info("=" * 60)
    logger.info("Daily DevOps Job Finder - Starting")
    logger.info("=" * 60)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    scrapers = [
        IndeedScraper(),
        AshbyScraper(),
        AmazonScraper(),
        NaukriScraper(),
        LinkedInScraper(),
    ]

    all_jobs = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {executor.submit(run_scraper, s): s for s in scrapers}
        for future in as_completed(future_map):
            scraper_name = future_map[future].source_name
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error("Unhandled error from %s: %s", scraper_name, e)

    logger.info("Total raw jobs collected: %d", len(all_jobs))

    all_jobs = deduplicate(all_jobs)
    all_jobs = rank_jobs(all_jobs)

    logger.info("Jobs after dedup + ranking: %d", len(all_jobs))

    # Filter out jobs below the minimum score threshold
    pre_filter_count = len(all_jobs)
    all_jobs = [j for j in all_jobs if j.get("score", 0) >= config.MIN_SCORE_THRESHOLD]
    logger.info(
        "Jobs after score filtering (threshold >= %d): %d (filtered out %d low-relevance jobs)",
        config.MIN_SCORE_THRESHOLD,
        len(all_jobs),
        pre_filter_count - len(all_jobs)
    )

    output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
    os.makedirs(output_dir, exist_ok=True)

    csv_path = os.path.join(output_dir, config.CSV_FILENAME.format(date=date_str))
    jobs_to_csv(all_jobs, csv_path)

    html_body = render_html_report(all_jobs, today)

    # Save an HTML preview file for easy local viewing
    html_path = os.path.join(output_dir, f"devops_jobs_report_{date_str}.html")
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_body)
        logger.info("HTML preview saved to %s", html_path)
    except Exception as e:
        logger.error("Failed to save HTML preview: %s", e)

    email_sent = send_email(
        html_body=html_body,
        csv_path=csv_path,
        date_str=today,
    )

    logger.info("=" * 60)
    logger.info(
        "Summary: %d jobs | CSV: %s | HTML: %s | Email sent: %s",
        len(all_jobs),
        csv_path,
        html_path,
        email_sent,
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
