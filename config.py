import os
from typing import Dict, List

SEARCH_KEYWORDS: List[str] = [
    "DevOps Engineer",
    "Cloud Engineer",
    "Site Reliability Engineer",
    "Platform Engineer",
]

LOCATIONS: List[str] = [
    "Pune, India",
    "Remote, India",
    "Mumbai, India",
    "Bengaluru, India",
]

LOCATION_PRIORITY: Dict[str, int] = {
    "pune": 100,
    "remote": 80,
    "mumbai": 60,
    "bengaluru": 60,
    "bangalore": 60,
    "hyderabad": 60,
    "chennai": 50,
    "delhi ncr": 50,
    "delhi": 50,
    "gurgaon": 50,
    "noida": 50,
    "india": 20,
}

KEYWORD_BONUS: Dict[str, int] = {
    "aws": 20,
    "kubernetes": 20,
    "k8s": 20,
    "terraform": 15,
    "github actions": 15,
    "docker": 15,
    "ecs": 15,
    "eks": 15,
    "ci/cd": 10,
    "gitlab": 5,
    "ansible": 10,
    "jenkins": 10,
    "helm": 10,
    "prometheus": 10,
    "grafana": 10,
    "pulumi": 10,
    "argocd": 10,
}

REQUEST_TIMEOUT: int = 15
MAX_RETRIES: int = 3
BACKOFF_BASE: float = 1.0

ASHBY_BOARDS: List[str] = [
    "ashby",
]

SMTP_HOST: str = "smtp.gmail.com"
SMTP_PORT: int = 587

GMAIL_USERNAME: str = os.environ.get("GMAIL_USERNAME", "")
GMAIL_APP_PASSWORD: str = os.environ.get("GMAIL_APP_PASSWORD", "")
RECIPIENT_EMAIL: str = os.environ.get("RECIPIENT_EMAIL", "")

CSV_FILENAME: str = "devops_jobs_report_{date}.csv"

USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

MAX_JOBS_PER_SOURCE: int = 50
LOOKBACK_HOURS: int = 24
