import logging
import smtplib
import os
import re
from collections import OrderedDict
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
from typing import List

from jinja2 import Environment, FileSystemLoader

import config
from scraper.base import JobDict

logger = logging.getLogger(__name__)

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

SOURCE_LABELS = {
    "naukri": "Naukri",
    "linkedin": "LinkedIn",
    "indeed": "Other Job Portals & Company Boards",
    "amazon": "Other Job Portals & Company Boards",
    "ashby": "Other Job Portals & Company Boards",
}


def _city_bucket(location: str) -> str:
    loc = (location or "").lower()
    if "pune" in loc:
        return "Pune"
    if any(kw in loc for kw in ("remote", "work from home", "wfh", "home office")):
        return "Remote"
    return "Other"


def _extract_matched_skills(job: JobDict) -> List[str]:
    title_lower = job.get("title", "").lower()
    desc_lower = job.get("description", "").lower()
    text = f"{title_lower} {desc_lower}"

    matched = []
    for kw in config.KEYWORD_BONUS.keys():
        # Match as word boundaries to prevent matching "aws" inside "laws"
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text):
            # Format nicely
            formatted = kw.upper() if kw in ("aws", "ci/cd", "k8s", "ecs", "eks") else kw.title()
            matched.append(formatted)
    return sorted(list(set(matched)))


def _group_by_source(jobs: List[JobDict]) -> OrderedDict:
    groups = OrderedDict(
        [
            ("Naukri", OrderedDict()),
            ("LinkedIn", OrderedDict()),
            ("Other Job Portals & Company Boards", OrderedDict()),
        ]
    )
    for job in jobs:
        source_label = SOURCE_LABELS.get(job.get("source", "").lower(), "Other Job Portals & Company Boards")
        if source_label not in groups:
            groups[source_label] = OrderedDict()
        city = _city_bucket(job.get("location", ""))
        if city not in groups[source_label]:
            groups[source_label][city] = []
        groups[source_label][city].append(job)
    return groups


def render_html_report(jobs: List[JobDict], date_str: str) -> str:
    # Inject matched skills into each job
    for job in jobs:
        job["matched_skills"] = _extract_matched_skills(job)

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("report.html")
    groups = _group_by_source(jobs)
    source_stats = OrderedDict()
    total = 0
    for src_label, city_groups in groups.items():
        src_total = sum(len(j) for j in city_groups.values())
        if src_total:
            source_stats[src_label] = src_total
            total += src_total
    source_totals = {
        src: sum(len(j) for j in city_groups.values())
        for src, city_groups in groups.items()
    }
    html = template.render(
        date=date_str,
        total_jobs=total,
        groups=groups,
        source_stats=source_stats,
        source_totals=source_totals,
        CITY_ORDER=["Pune", "Remote", "Other"],
    )
    logger.info("HTML report rendered: %d total jobs", len(jobs))
    return html


def send_email(
    html_body: str,
    csv_path: str,
    date_str: str,
    recipient: str = "",
    username: str = "",
    password: str = "",
) -> bool:
    recipient = recipient or config.RECIPIENT_EMAIL
    username = username or config.GMAIL_USERNAME
    password = password or config.GMAIL_APP_PASSWORD

    if not all([recipient, username, password]):
        logger.warning("Email config incomplete; skipping send")
        return False

    msg = MIMEMultipart("mixed")
    msg["From"] = username
    msg["To"] = recipient
    msg["Subject"] = f"Daily DevOps Job Report - {date_str}"
    msg["Date"] = formatdate(localtime=True)

    msg_alt = MIMEMultipart("alternative")
    msg.attach(msg_alt)

    text_part = MIMEText(
        f"Daily DevOps Job Report - {date_str}\n\n"
        f"Total jobs: {len(html_body.split('<tr>')) - html_body.count('<tr><th>')}\n\n"
        "Open this email in an HTML-compatible client to view the formatted report.\n",
        "plain",
        "utf-8",
    )
    msg_alt.attach(text_part)

    html_part = MIMEText(html_body, "html", "utf-8")
    msg_alt.attach(html_part)

    if csv_path and os.path.exists(csv_path):
        with open(csv_path, "rb") as f:
            attachment = MIMEBase("text", "csv")
            attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(csv_path),
        )
        msg.attach(attachment)

    try:
        server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        logger.info("Email sent successfully to %s", recipient)
        return True
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False
