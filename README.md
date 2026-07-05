# 🚀 Daily DevOps Job Finder

Automatically searches for DevOps, SRE, Cloud, and Platform engineering jobs every morning, dedupes and scores listings by relevance, and emails a visually stunning HTML dashboard report card (complete with skill badges and location tags) alongside a raw CSV attachment.

---

## 🎨 HTML Email Visual Preview

The report replaces plain spreadsheets with a premium dashboard cards layout:
* **Metrics Header**: Highlights Total Jobs found, Naukri roles, LinkedIn roles, and others in a clean, single-row responsive table.
* **Source Grouping**: Prioritizes Naukri and LinkedIn sections at the top, grouping other sources under a unified list.
* **City Badges**: Color-coded badges instantly highlight target locations (e.g., **Pune** in green, **Remote** in blue, **Other** in grey).
* **Skill Badges**: Extracted skills (e.g. `AWS`, `Kubernetes`, `Terraform`, `CI/CD`) appear as violet pills on each job card.
* **White-label Apply Buttons**: High-contrast buttons align on the right for instant, one-click applications.

---

## 🛠️ Key Features

* Concurrently crawls 5 job portals:
  * **LinkedIn** (Guest search API)
  * **Naukri** (Official RSA jobapi endpoint with auto-generated parameters)
  * **Indeed** (Page parsing engine)
  * **Ashby Boards** (Crawls boards of top companies like Anthropic, Linear, Raycast, Sentry, and Vercel)
  * **Amazon Jobs API**
* **Deduplication Engine**: Automatically filters out identical listings across sources.
* **ATS-Style Scoring**: Ranks jobs based on location match and target skill keywords.
* **Clutter Filter**: Drops jobs below a score threshold and filters out international restricted remote postings (e.g. US/EU only remote) that don't apply to India.
* **Local Previews**: Automatically saves an HTML file of the email layout in the `output/` directory for checking visuals.

---

## ⚙️ Customization via Environment Variables

No need to modify Python scripts to change search keywords or locations! Set the following environment variables (locally or via GitHub Secrets):

| Variable | Description | Default Example |
|---|---|---|
| `SEARCH_KEYWORDS` | Comma-separated list of titles | `DevOps Engineer, SRE, Platform Engineer` |
| `LOCATIONS` | Comma-separated list of target cities | `Pune, India, Remote, India, Bengaluru` |
| `MIN_SCORE_THRESHOLD` | Discard jobs below this matching score | `50` |
| `JOB_FRESHNESS_DAYS` | Lookback window for jobs | `1` |

---

## 🚀 Setup & Deployment

### 1. Fork and Configure GitHub Secrets
Fork this repository, then head to **Settings → Secrets and variables → Actions → New repository secret** and configure:

| Secret Name | Description |
|---|---|
| `GMAIL_USERNAME` | Your Gmail address (e.g., `you@gmail.com`) |
| `GMAIL_APP_PASSWORD` | 16-character Gmail App Password (see security settings) |
| `RECIPIENT_EMAIL` | Destination email where report is sent |

### 2. Custom Search Setup (Optional)
Add variables like `SEARCH_KEYWORDS` and `LOCATIONS` to your **Actions Secrets** to customize searches when running serverless on GitHub Actions.

### 3. Automated Runs
* The workflow runs automatically every morning at **9:30 AM IST** (3:30 AM UTC) via GitHub Actions schedule cron.
* **Push to Main**: The scraper also triggers automatically whenever you push edits to the `main` branch.
* **Manual Run**: Go to **Actions → Daily DevOps Job Search → Run workflow** to run it immediately.

---

## 💻 Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/devops-job-search
   cd devops-job-search
   ```

2. **Create a virtual environment & install requirements**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure local environment variables**:
   Export the variables in your shell before running:
   ```bash
   export GMAIL_USERNAME="your-email@gmail.com"
   export GMAIL_APP_PASSWORD="your-gmail-app-password"
   export RECIPIENT_EMAIL="destination-email@gmail.com"
   export SEARCH_KEYWORDS="DevOps, SRE, Cloud Engineer"
   export LOCATIONS="Pune, India, Remote, India"
   ```

4. **Run the script**:
   ```bash
   python scraper/main.py
   ```
   *Note: This will output local previews in the `output/` directory.*

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

