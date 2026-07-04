import logging
import smtplib
import os
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from typing import List

from jinja2 import Environment, FileSystemLoader

import config
from scraper.base import JobDict
from scraper.ranking import separate_by_location

logger = logging.getLogger(__name__)

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


def render_html_report(jobs: List[JobDict], date_str: str) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("report.html")
    pune_jobs, remote_jobs, other_jobs = separate_by_location(jobs)
    total = len(jobs)
    html = template.render(
        date=date_str,
        total_jobs=total,
        pune_count=len(pune_jobs),
        remote_count=len(remote_jobs),
        other_count=len(other_jobs),
        pune_jobs=pune_jobs,
        remote_jobs=remote_jobs,
        other_jobs=other_jobs,
    )
    logger.info("HTML report rendered: %d total jobs", total)
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
        f"Total jobs: {html_body.count('<tr>') - 1}\n\n"
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
        from email import encoders

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
