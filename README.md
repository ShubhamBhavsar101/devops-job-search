# Daily DevOps Job Finder

Automatically searches for DevOps, Cloud, SRE, Platform, and Infrastructure engineering jobs in India every morning and emails a well-formatted HTML report with a CSV attachment.

## How It Works

1. Runs daily at **9:00 AM IST** via GitHub Actions (`schedule` trigger)
2. Searches 13+ job sources using public APIs, RSS feeds, and HTML parsing
3. Filters jobs posted within the last 24 hours
4. Deduplicates identical listings across sources
5. Ranks by location priority + keyword relevance
6. Generates an HTML email report (Pune / Remote / Other sections)
7. Attaches a CSV with all job details
8. Uploads CSV, HTML, and logs as workflow artifacts

## Job Sources

| Source | Method | Reliability |
|---|---|---|
| Indeed | RSS feed | High |
| Greenhouse (150+ companies) | Public API | High |
| Lever (50+ companies) | Public API | High |
| Ashby | Public API | High |
| Naukri | HTML + JSON | Medium |
| LinkedIn | Guest API | Low (rate-limited from GHA) |
| Google Careers | JSON API | Medium |
| Microsoft Careers | JSON API | Medium |
| Amazon Careers | JSON API | Medium |
| Oracle Careers | Workday API | Medium |

Adding a new source: create a class extending `BaseScraper` in `scraper/` and register it in `scraper/main.py`.

## Search Keywords

DevOps Engineer, AWS Engineer, AWS Cloud Engineer, Cloud Engineer, Platform Engineer, Site Reliability Engineer, SRE, Infrastructure Engineer, Kubernetes Engineer, Terraform Engineer, Cloud DevOps Engineer, CI/CD Engineer, Release Engineer.

## Locations (prioritized)

1. Pune (+100)
2. Remote India (+80)
3. Mumbai / Bengaluru / Hyderabad (+60)
4. Chennai / Delhi NCR (+50)
5. Anywhere in India (+20)

Keyword bonuses: AWS, Kubernetes (+20), Terraform, Docker, CI/CD, GitHub Actions (+15), GitLab (+5), and more.

## Setup

### 1. Fork / Clone

```bash
git clone <your-repo-url>
cd devops-job-finder
```

### 2. Configure GitHub Secrets

In your repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `GMAIL_USERNAME` | Your Gmail address (e.g., `you@gmail.com`) |
| `GMAIL_APP_PASSWORD` | Gmail App Password (see below) |
| `RECIPIENT_EMAIL` | Where to send the report |

### 3. Generate Gmail App Password

1. Go to https://myaccount.google.com/security
2. Enable **2-Step Verification** if not already enabled
3. Go to **App passwords** (search in Google Account settings)
4. Select **Mail** and your device, then **Generate**
5. Copy the 16-character password — use this as `GMAIL_APP_PASSWORD`

### 4. Enable the Workflow

The workflow is disabled by default on forks. Go to **Actions** tab and enable it.

### 5. Manual Test Run

Go to **Actions → Daily DevOps Job Search → Run workflow** (dropdown) to trigger an immediate run.

## Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Test without email:
python scraper/main.py
```

Set environment variables for email:
```bash
export GMAIL_USERNAME="your@gmail.com"
export GMAIL_APP_PASSWORD="your-app-password"
export RECIPIENT_EMAIL="you@example.com"
```

## Output

- **Email**: Beautiful HTML report with tables per location section
- **CSV**: Full job data attached to the email
- **Artifacts**: CSV + HTML + logs available in GitHub Actions run summary

### Sample CSV Columns

Company, Role, Location, Source, Posted, Apply URL, Score

## Project Structure

```
.
├── .github/workflows/daily-job-search.yml
├── scraper/
│   ├── base.py              # Abstract base scraper
│   ├── indeed.py            # Indeed RSS feed
│   ├── greenhouse.py        # Greenhouse API (150+ companies)
│   ├── lever.py             # Lever API
│   ├── ashby.py             # Ashby API
│   ├── naukri.py            # Naukri.com
│   ├── linkedin.py          # LinkedIn guest API
│   ├── company_sites.py     # Google, Microsoft, Amazon, Oracle
│   ├── ranking.py           # Scoring + dedup
│   ├── exporter.py          # CSV generation
│   ├── email_template.py    # HTML rendering + SMTP
│   └── main.py              # Orchestrator
├── templates/
│   └── report.html          # Jinja2 HTML email template
├── config.py                # Central configuration
├── requirements.txt
└── README.md
```

## Adding New Sources

1. Create `scraper/mysource.py` with a class extending `BaseScraper`
2. Implement the `scrape()` method returning `List[JobDict]`
3. Add the scraper to the list in `scraper/main.py`
4. Optionally add API keys / config to `config.py`

## Notes

- LinkedIn scraping from GitHub Actions datacenter IPs is unreliable due to rate limiting — it will try and gracefully fail
- Naukri uses HTML parsing which may break if their markup changes
- Greenhouse covers 150+ companies through their shared ATS (Datadog, HashiCorp, Snowflake, CrowdStrike, etc.)

## License

MIT
