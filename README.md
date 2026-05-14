# Job Search with Claude

Twice a week, this thing wakes up, searches for jobs that match a profile you wrote, has Claude score each one against your own rubric, and emails you a short tiered list. Then it learns from your apply / pass decisions and gets sharper over time.

> **Heads up:** Setting this up takes ~45 minutes and requires accounts at SerpAPI, Anthropic, Google, and GitHub. Once it's running, it costs roughly $0–$5/month (Anthropic API usage; SerpAPI has a free tier that fits this workload).

> **⚠️ Make your copy private.** Your `RUBRIC.md` and `config.py` will contain personal information — salary floor, current role, current employer, career history. GitHub defaults new repos to **Public**; set it to **Private** on the "Use this template" page *before* clicking Create. (API keys live in GitHub Secrets and never end up in the repo — but your profile *will*.)

> **One thing to know.** Each run sends your rubric and the job listings to Anthropic so Claude can score them — that's just how it works. Your salary and career history go through their servers. Anthropic says they don't train on API data, and I have no reason to doubt them, but I figured it was worth being upfront. Same caveat applies to whatever AI you use for resumes, cover letters, or anything else job-search related.

**My best advice:** Don't set this up alone. Open the repo in [Claude](https://claude.ai) or [Claude Code](https://claude.com/claude-code) and ask it to walk you through setup. The hardest part of this whole thing is writing a sharp rubric for *yourself* — a 20-minute conversation with an AI that can read the template and edit your files beats a solo afternoon. Claude handles the editing; you make the decisions.

(Don't prefer Claude? You should. But any modern code-capable AI — ChatGPT, Gemini, Cursor — works fine for this too.)

## Why use this instead of scrolling LinkedIn

LinkedIn's job feed is optimized for engagement, not for you. You wade through expired postings, roles three levels below where you are, "I'm humbled to announce" posts between every other card, and an algorithm that surfaces whatever it thinks will keep you scrolling. By the time you've filtered all that out in your head, you've burned 40 minutes and applied to nothing.

This pipeline does the filtering before the email lands:

- **It scores against *your* rubric, not a generic algorithm.** You write a markdown file describing your title, level, salary floor, geography, deal-breakers, and what makes a role exciting to you. Claude reads it for every job. The "algorithm" is yours — you can edit it whenever your search shifts, and the next run picks up the change.
- **It learns from your feedback.** Every time you click Applied or Passed in the digest, the reason gets fed back into the next run as positive or negative examples. So if Claude keeps surfacing data-analyst roles when you want research roles, two or three "Passed — too analyst-leaning" clicks fix it. No retraining, no settings menu.
- **It explains itself.** Every job comes with a score, a tier, 3–5 specific signals (quant-heavy / qual-only / posting is 11 days old), and one honest "watch out" sentence — even on the recommended ones. You're triaging with context, not vibes.
- **It filters out the noise you don't want to think about.** Salary below your floor → gone. Current employer → gone. Junior or downlevel titles → gone. Postings older than two weeks → gone. Duplicates from previous digests → gone.
- **It's a digest, not a feed.** Two emails a week, ~5–15 jobs each, sorted into "Recommended" and "Worth Reviewing." When you're done reading, you're done. There's no infinite scroll and nothing to come back to.
- **No influencer posts. No ads. No "open to work" green ring.** Just jobs.

## How it works (plain version)

Every Tuesday and Friday morning (you can change which days and times — see Tuning), a small program runs on GitHub's servers. It searches Google Jobs for the titles you care about in your area (and remote), throws out anything that fails your hard rules, hands the survivors to Claude with your rubric attached, and Claude returns a ranked list with reasons. The program turns that list into an email with **Apply** and **Pass** buttons next to each job. Your clicks save to a Google Sheet, which the next run reads to learn what you actually want.

You set this up once. After that, the only thing you ever touch is your rubric — and only when you want to.

## How it works (technical version)

```
Tue/Fri 9am  →  GitHub Actions  →  job_search.py
                                       │
                                       ├── SerpAPI — runs your queries × your location + remote
                                       ├── Pre-filters: excluded companies, salary floor, recency, dedup
                                       ├── Claude — scores each job against YOUR rubric + past feedback
                                       ├── Gmail — sends an HTML digest with apply / pass buttons
                                       └── Google Form/Sheet — your feedback loops back next run
```

## Files

| File | Purpose |
|------|---------|
| `job_search.py` | Main pipeline. |
| `config.py` | Non-secret config (queries, location, salary floor, model, form IDs). **Edit this.** |
| `RUBRIC.md` | Your profile + scoring criteria. **Edit this freely.** Re-run to apply changes. |
| `FORM_SETUP.md` | One-time Google Form/Sheet setup walkthrough. |
| `requirements.txt` | Python dependencies. |
| `.github/workflows/job_search.yml` | The GitHub Actions schedule + auto-commit step. |
| `sent_jobs.json` | Created on first run. Tracks job IDs to avoid re-sending. Committed back by the workflow. |

## What you'll need before starting

| | Where to get it | Cost |
|---|---|---|
| GitHub account | https://github.com | Free |
| SerpAPI key | https://serpapi.com | Free tier (100 searches/mo) is enough |
| Anthropic API key | https://console.anthropic.com | Pay-per-use, ~$0.10–$1/run |
| A Gmail account with 2FA on | https://myaccount.google.com/security | Free |
| A Google Cloud project (for a service account) | https://console.cloud.google.com | Free |

## Setup

### 1. Use as a template

Click **Use this template** at the top of this repo → **Create a new repository from template**.

**Set visibility to Private.** This one matters — your rubric will hold your salary floor, current employer, and personal job-search criteria, and the default is Public. Don't skip it.

Name it something like `my-job-search`, then clone it locally.

### 2. Write *your* rubric

Open `RUBRIC.md`. This is the most important file — it tells Claude how to score jobs for **you**. Replace the placeholder profile with your own: current role, geo preference, salary floor, target titles, hard disqualifiers, positive signals, preferred companies. Take your time here; this is the difference between a noisy inbox and a sharp one.

### 3. Edit `config.py`

Replace the placeholder values:
- `QUERIES` — the job titles you want to search for
- `LOCATION` — your city/state
- `SALARY_FLOOR_USD`
- `EXCLUDED_COMPANIES` — your current employer, etc.
- `PREFERRED_COMPANIES` — companies you'd take regardless of softer fit

Leave `FORM_BASE_URL` and `FORM_FIELDS` empty for now — you'll fill them in after step 4.

### 4. Set up the Google Form + Sheet

Follow `FORM_SETUP.md` end-to-end. You'll come out with:
- A Form URL + 5 `entry.*` field IDs (paste these into `config.py`)
- A Sheet ID
- A service account JSON file (keep this — do **not** commit it)
- A service-account email with **Editor** access to your Sheet

### 5. Push and add secrets

Push your repo to GitHub. Then go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|---|---|
| `SERPAPI_KEY` | from serpapi.com |
| `ANTHROPIC_API_KEY` | from console.anthropic.com |
| `EMAIL_FROM` | the Gmail you'll send from |
| `EMAIL_TO` | the inbox where you want the digest |
| `EMAIL_PASSWORD` | a Gmail **app password** (not your real password) — https://myaccount.google.com/apppasswords |
| `GOOGLE_SHEETS_CREDENTIALS` | the full contents of the service account JSON, on one line |
| `GOOGLE_SHEET_ID` | from the Sheet URL |

### 6. First run

**Actions tab → Job Search Digest → Run workflow**. Watch the log. If you see `Email sent: N recommended, M worth reviewing`, check your inbox. After that, it'll run automatically Tue/Fri at 9am ET (edit the cron in `.github/workflows/job_search.yml` to change).

## Tuning

- **Too noisy?** Tighten queries in `config.py` or raise the threshold in `RUBRIC.md`.
- **Missing good roles?** Add queries or loosen disqualifiers.
- **Different schedule?** Edit the cron in `.github/workflows/job_search.yml`.
- **Want to exclude a company?** Add it to `EXCLUDED_COMPANIES` in `config.py`.
- **Different model?** Change `CLAUDE_MODEL` in `config.py`.

## Local dev

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # fill in
set -a; source .env; set +a  # Windows: load env vars however you do
python job_search.py
```

## License

MIT. Use it, fork it, change it, ship it. No warranty.
