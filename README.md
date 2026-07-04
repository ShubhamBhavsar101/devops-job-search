# Daily DevOps Job Finder

Automatically searches for DevOps, Cloud, SRE, Platform, and Infrastructure engineering jobs in India every morning and emails a well-formatted HTML report with a CSV attachment.

## How It Works

1. Runs daily at **9:00 AM IST** via GitHub Actions
2. Searches 4 job sources for keywords matching DevOps roles
3. Filters jobs posted within the last 24 hours
4. Deduplicates identical listings across sources
5. Ranks by location priority + keyword relevance
6. Generates an HTML email report (Pune / Remote / Other sections)
7. Attaches CSV with all job details

## Job Sources

| Source | Method | Reliability |
|---|---|---|
| **Amazon Jobs** | JSON API | ✅ Working |
| **Ashby** (Anthropic, Linear, Raycast) | Public API | ✅ Working |
| **Naukri** | HTML parsing | ⚠️ Best-effort (anti-bot) |
| **LinkedIn** | Guest API | ⚠️ Best-effort (rate-limited) |

### About Naukri & LinkedIn

Naukri and LinkedIn employ aggressive anti-bot measures (CAPTCHAs, rate-limiting) that block server-side scrapers from GitHub Actions datacenter IPs. The scraper will attempt them every run and gracefully move on — they may produce results from residential IPs if run locally.

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
git clone https://github.com/ShubhamBhavsar101/devops-job-search
cd devops-job-search
```

### 2. Configure GitHub Secrets

In your repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `GMAIL_USERNAME` | Your Gmail address (e.g., `you@gmail.com`) |
| `GMAIL_APP_PASSWORD` | Gmail App Password (16 chars) |
| `RECIPIENT_EMAIL` | Where to send the report |

### 3. Generate Gmail App Password

1. Enable **2-Step Verification** at https://myaccount.google.com/security
2. Go to https://myaccount.google.com/apppasswords
3. Select **Mail** → **Other** → name it `devops-job-finder` → **Generate**
4. Copy the 16-character password

### 4. Manual Test Run

Go to **Actions → Daily DevOps Job Search → Run workflow** to trigger immediately.

## Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export GMAIL_USERNAME="your@gmail.com"
export GMAIL_APP_PASSWORD="your-app-password"
export RECIPIENT_EMAIL="you@example.com"
python scraper/main.py
```

## Output

- **Email**: HTML report with location-section tables + CSV attachment
- **Artifacts**: CSV available in GitHub Actions run summary

## Project Structure

```
├── .github/workflows/daily-job-search.yml
├── scraper/
│   ├── base.py              # Abstract base scraper (retry, timeout, normalize)
│   ├── ashby.py             # Ashby public API
│   ├── amazon.py            # Amazon Jobs JSON API
│   ├── naukri.py            # Naukri (best-effort)
│   ├── linkedin.py          # LinkedIn guest API (best-effort)
│   ├── ranking.py           # Scoring + dedup algorithm
│   ├── exporter.py          # CSV export
│   ├── email_template.py    # HTML rendering + SMTP send
│   └── main.py              # Orchestrator
├── templates/report.html    # Jinja2 HTML email template
├── config.py                # Central configuration
├── requirements.txt
└── README.md
```

## Adding New Sources

1. Create `scraper/mysource.py` with a class extending `BaseScraper`
2. Implement `scrape()` returning `List[JobDict]`
3. Add it to the list in `scraper/main.py`

## License

MIT
