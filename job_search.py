"""
Scheduled job-search digest.

- Reads scoring rubric from RUBRIC.md (edit freely without touching code)
- Salary-floor pre-filter
- Excluded-companies pre-filter (current employer, etc.)
- Remote-pass option in addition to geo search
- Claude Sonnet 4.6 by default
- Config split out of code
"""

import json
import os
import re
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote

import gspread
import requests
from anthropic import Anthropic
from oauth2client.service_account import ServiceAccountCredentials

import config

# --- Secrets from env ---
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")


# --- Rubric ---
def load_rubric() -> str:
    """Read the markdown rubric so you can edit it without touching code."""
    if not os.path.exists(config.RUBRIC_FILE):
        raise FileNotFoundError(
            f"{config.RUBRIC_FILE} not found. This file is required — it's the source of truth "
            "for your profile and scoring criteria."
        )
    with open(config.RUBRIC_FILE, "r", encoding="utf-8") as f:
        return f.read()


# --- Sent-jobs dedup (simple JSON file, committed back by GH Actions) ---
def load_sent_jobs() -> list:
    if os.path.exists(config.SENT_JOBS_FILE):
        with open(config.SENT_JOBS_FILE, "r") as f:
            return json.load(f)
    return []


def save_sent_jobs(sent_jobs: list) -> None:
    with open(config.SENT_JOBS_FILE, "w") as f:
        json.dump(sent_jobs, f, indent=2)


# --- Feedback loop ---
def get_feedback_from_sheets() -> dict:
    """Read recent Applied/Passed responses so Claude can learn from them."""
    feedback = {"applied": [], "passed": []}
    if not GOOGLE_SHEETS_CREDENTIALS or not GOOGLE_SHEET_ID:
        print("Sheets not configured; skipping feedback load.")
        return feedback
    try:
        creds_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        records = sheet.get_all_records()

        for record in records:
            entry = {
                "title": record.get("Job Title", ""),
                "company": record.get("Company", ""),
                "reason": record.get(
                    "Why did you apply or pass? (Optional - helps improve recommendations)",
                    "",
                ),
            }
            answer = record.get("Did you apply?", "")
            if "Applied" in answer:
                feedback["applied"].append(entry)
            elif "Passed" in answer:
                feedback["passed"].append(entry)

        feedback["applied"] = feedback["applied"][-15:]
        feedback["passed"] = feedback["passed"][-15:]
        print(
            f"Loaded feedback: {len(feedback['applied'])} applied, "
            f"{len(feedback['passed'])} passed"
        )
    except Exception as e:
        print(f"Error loading feedback from sheets: {e}")
    return feedback


def write_job_details_to_sheet(scored_jobs: list, all_jobs: list) -> None:
    """
    Write Tier 1 and Tier 2 jobs to a 'Job_Details' tab in the Sheet so you can
    share the Sheet with Claude at the start of a session and work through applications.
    Columns: Timestamp, Job ID, Job Title, Company, Score, Tier, Salary, Location Note,
             Apply URL, Description (truncated), Signals, Flag
    Creates the tab if it doesn't exist.
    """
    if not GOOGLE_SHEETS_CREDENTIALS or not GOOGLE_SHEET_ID:
        print("Sheets not configured; skipping job details write.")
        return
    try:
        creds_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        # Get or create the Job_Details tab
        try:
            detail_sheet = spreadsheet.worksheet("Job_Details")
        except Exception:
            detail_sheet = spreadsheet.add_worksheet(title="Job_Details", rows=500, cols=12)
            detail_sheet.append_row([
                "Timestamp", "Job ID", "Job Title", "Company", "Score", "Tier",
                "Salary", "Location Note", "Apply URL", "Description", "Signals", "Flag"
            ])

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        rows_to_write = []

        for match in scored_jobs:
            idx = match["job_number"] - 1
            if idx >= len(all_jobs):
                continue
            job = all_jobs[idx]
            apply_url = (job.get("apply_options") or [{}])[0].get("link", "")
            description = (job.get("description") or "")[:800].strip()
            signals = " | ".join(match.get("signals") or [])
            rows_to_write.append([
                timestamp,
                job.get("job_id", ""),
                job.get("title", ""),
                job.get("company_name", ""),
                match.get("score", ""),
                match.get("tier", ""),
                match.get("salary_display", "Not listed"),
                match.get("location_note", ""),
                apply_url,
                description,
                signals,
                match.get("flag", ""),
            ])

        if rows_to_write:
            detail_sheet.append_rows(rows_to_write)
            print(f"Wrote {len(rows_to_write)} jobs to Job_Details sheet.")

    except Exception as e:
        print(f"Error writing job details to sheet: {e}")


def create_feedback_url(job: dict, feedback_type: str) -> str:
    """Pre-filled formResponse URL — clicking submits without showing the form."""
    params = {
        config.FORM_FIELDS["job_id"]: job.get("job_id", "unknown"),
        config.FORM_FIELDS["title"]: job.get("title", "Unknown Title"),
        config.FORM_FIELDS["company"]: job.get("company_name", "Unknown Company"),
        config.FORM_FIELDS["feedback"]: feedback_type,
    }
    query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    return f"{config.FORM_BASE_URL}?{query}"


# --- Pre-filters ---
def is_within_days(posted_text: str, days_ago: int) -> bool:
    posted_lower = (posted_text or "").lower()
    if any(x in posted_lower for x in ["just posted", "today", "hour"]):
        return True
    if "day" in posted_lower:
        try:
            return int(posted_lower.split()[0]) <= days_ago
        except Exception:
            return True
    if "week" in posted_lower:
        try:
            return int(posted_lower.split()[0]) * 7 <= days_ago
        except Exception:
            return True
    if "month" in posted_lower:
        return days_ago >= 30
    return True


def excluded_company(company_name: str) -> bool:
    if not company_name:
        return False
    name = company_name.lower()
    return any(blocked.lower() in name for blocked in config.EXCLUDED_COMPANIES)


_SALARY_RE = re.compile(
    r"\$\s?(?P<n1>\d{1,3}(?:,\d{3})+|\d{2,7})\s?(?P<k1>[kK])?"
    r"(?:\s*-\s*\$?\s?(?P<n2>\d{1,3}(?:,\d{3})+|\d{2,7})\s?(?P<k2>[kK])?)?"
)


def extract_max_salary(text: str) -> int | None:
    """
    Pull the highest dollar figure that looks like an annual salary out of a posting.
    Returns None if nothing salary-shaped is found. Heuristic, not perfect — but tuned
    to skip hourly rates ($45-$60/hr) and small dollar amounts ($5,000 sign-on).
    """
    if not text:
        return None
    candidates: list[int] = []
    for match in _SALARY_RE.finditer(text):
        for num_key, k_key in [("n1", "k1"), ("n2", "k2")]:
            raw = match.group(num_key)
            if not raw:
                continue
            value = int(raw.replace(",", ""))
            has_k_suffix = match.group(k_key) is not None
            if has_k_suffix:
                value *= 1000
            elif value < 1000:
                # No K suffix and value < 1000 — likely hourly rate or small amount.
                continue
            if 30_000 <= value <= 1_000_000:
                candidates.append(value)
    return max(candidates) if candidates else None


def passes_pre_filters(job: dict) -> tuple[bool, str]:
    """Cheap deterministic checks before paying Claude tokens. Returns (ok, reason_if_not)."""
    company = job.get("company_name", "")
    if excluded_company(company):
        return False, f"excluded company: {company}"
    description = job.get("description", "") or ""
    salary = extract_max_salary(description)
    if salary is not None and salary < config.SALARY_FLOOR_USD:
        return False, f"salary ${salary:,} below floor ${config.SALARY_FLOOR_USD:,}"
    return True, ""


# --- SerpAPI ---
def search_google_jobs(query: str, location: str | None, days_ago: int) -> list:
    params = {
        "engine": "google_jobs",
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": "en",
        "gl": "us",
        "chips": "date_posted:month",
    }
    if location:
        params["location"] = location
        params["lrad"] = 50
    response = requests.get("https://serpapi.com/search", params=params, timeout=30)
    if response.status_code != 200:
        print(f"  SerpAPI error {response.status_code}: {response.text[:200]}")
        return []
    jobs = response.json().get("jobs_results", [])
    filtered = [
        j
        for j in jobs
        if is_within_days(j.get("detected_extensions", {}).get("posted_at", ""), days_ago)
    ]
    print(f"  '{query}' @ {location or 'remote'}: {len(jobs)} → {len(filtered)} after recency filter")
    return filtered


# --- Claude scoring ---
def score_jobs_with_claude(jobs: list, feedback: dict, rubric: str) -> dict:
    if not jobs:
        return {"recommended": [], "worth_reviewing": [], "all": []}

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    jobs_text = "\n\n---\n\n".join(
        f"JOB {i+1}:\n"
        f"Title: {job.get('title')}\n"
        f"Company: {job.get('company_name')}\n"
        f"Location: {job.get('location')}\n"
        f"Posted: {job.get('detected_extensions', {}).get('posted_at', 'Unknown')}\n"
        f"Description: {(job.get('description') or '')[:config.DESCRIPTION_CHAR_LIMIT]}"
        for i, job in enumerate(jobs)
    )

    feedback_section = ""
    if len(feedback["applied"]) >= 3 or len(feedback["passed"]) >= 3:
        feedback_section = "\n\n## LEARNING FROM PAST DECISIONS\n\n"
        if feedback["applied"]:
            feedback_section += "Jobs the candidate APPLIED to (positive examples):\n"
            for i, j in enumerate(feedback["applied"][:10], 1):
                feedback_section += f"{i}. {j['title']} at {j['company']}\n"
                if j.get("reason"):
                    feedback_section += f"   Why: {j['reason']}\n"
        if feedback["passed"]:
            feedback_section += "\nJobs the candidate PASSED on (negative examples):\n"
            for i, j in enumerate(feedback["passed"][:10], 1):
                feedback_section += f"{i}. {j['title']} at {j['company']}\n"
                if j.get("reason"):
                    feedback_section += f"   Why: {j['reason']}\n"
        feedback_section += (
            "\nUse these to calibrate. Jobs similar to applied → score higher. "
            "Jobs similar to passed → score lower.\n"
        )

    prompt = f"""You are filtering job postings for a candidate. Use the rubric below as the authoritative
guide to their profile and scoring criteria.

{rubric}
{feedback_section}

## OUTPUT

Return ONLY a JSON array. Include every job scoring 6 or higher. Format:

[{{"job_number": 1, "score": 8, "tier": "recommended", "reason": "...", "location_note": "..."}}]

Tiers: "recommended" (8-10), "worth_reviewing" (6-7). Drop everything ≤5 (do not include).

Jobs to evaluate:

{jobs_text}
"""

    message = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        response_text = message.content[0].text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        scored = json.loads(response_text.strip())
    except Exception as e:
        print(f"Error parsing Claude response: {e}")
        print(f"Response: {message.content[0].text[:500]}")
        return {"recommended": [], "worth_reviewing": [], "all": []}

    return {
        "recommended": [j for j in scored if j.get("tier") == "recommended"],
        "worth_reviewing": [j for j in scored if j.get("tier") == "worth_reviewing"],
        "all": scored,
    }


# --- Email ---
def send_email(filtered: dict, all_jobs: list) -> None:
    recommended = filtered["recommended"]
    worth_reviewing = filtered["worth_reviewing"]
    today = datetime.now().strftime("%B %d, %Y")

    if not recommended and not worth_reviewing:
        html = f"""
        <html><body>
        <h2>Job Digest — {today}</h2>
        <p>Searched {len(all_jobs)} jobs. No new matches above threshold.</p>
        <p>Next run is in two days.</p>
        </body></html>
        """
        subject = f"Job Digest — no new matches ({today})"
    else:
        sections = ""
        if recommended:
            sections += '<h3 style="color:#2E7D32;border-bottom:2px solid #2E7D32;padding-bottom:5px;">⭐ RECOMMENDED</h3>'
            sections += render_jobs(recommended, all_jobs, accent="#4CAF50", bg="#f1f8f4")
        if worth_reviewing:
            sections += '<h3 style="color:#F57C00;border-bottom:2px solid #F57C00;padding-bottom:5px;">💡 WORTH REVIEWING</h3>'
            sections += render_jobs(worth_reviewing, all_jobs, accent="#FF9800", bg="#fff8f0")

        html = f"""
        <html><body>
        <h2>Job Digest — {today}</h2>
        <p><strong>{len(recommended)} Recommended</strong> · {len(worth_reviewing)} Worth Reviewing · {len(all_jobs)} Searched</p>
        <p style="font-size:12px;color:#666;">Click ✅ Applied or ❌ Passed to teach Claude what fits.</p>
        {sections}
        </body></html>
        """
        subject = f"Job Digest — {len(recommended)} Recommended, {len(worth_reviewing)} More"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"Email sent: {len(recommended)} recommended, {len(worth_reviewing)} worth reviewing")
    except Exception as e:
        print(f"Error sending email: {e}")


def render_jobs(matches: list, all_jobs: list, accent: str, bg: str) -> str:
    chunks = []
    for match in matches:
        idx = match["job_number"] - 1
        if idx >= len(all_jobs):
            continue
        job = all_jobs[idx]
        apply_link = (job.get("apply_options") or [{}])[0].get("link", "#")
        posted = job.get("detected_extensions", {}).get("posted_at", "Unknown")
        applied_url = create_feedback_url(job, "Applied ✅")
        passed_url = create_feedback_url(job, "Passed ❌")

        # Salary display
        salary = match.get("salary_display", "Not listed")
        salary_color = "#333" if salary != "Not listed" else "#999"

        # Signals: render as inline tags
        signals = match.get("signals") or []
        signals_html = " ".join(
            f'<span style="display:inline-block;margin:2px 4px 2px 0;padding:2px 8px;'
            f'border-radius:12px;font-size:11px;background:#fff;border:1px solid #ddd;">{s}</span>'
            for s in signals
        )

        # Flag: honest watch-out, shown in a subtle yellow band
        flag = match.get("flag", "")
        flag_html = (
            f'<p style="margin:10px 0 0 0;padding:8px 10px;background:#fffbea;'
            f'border-left:3px solid #f0c040;font-size:12px;color:#555;">'
            f'<strong>Flag:</strong> {flag}</p>'
        ) if flag else ""

        chunks.append(
            f"""
        <div style="border:2px solid {accent};padding:15px;margin:15px 0;border-radius:5px;background-color:{bg};">
            <h4 style="margin-top:0;">{job.get('title')} — {job.get('company_name')}</h4>
            <p style="margin:4px 0;">
                <strong>📍</strong> {job.get('location')} <em>({match.get('location_note', '')})</em>
                &nbsp;·&nbsp;
                <strong>💰</strong> <span style="color:{salary_color};">{salary}</span>
                &nbsp;·&nbsp;
                <strong>📅</strong> {posted}
                &nbsp;·&nbsp;
                <strong>⭐</strong> {match['score']}/10
            </p>
            <p style="margin:10px 0 6px 0;">{signals_html}</p>
            <p style="margin:10px 0;">{match['reason']}</p>
            {flag_html}
            <p style="margin:14px 0 4px 0;">
                <a href="{apply_link}" style="background-color:{accent};color:white;padding:10px 20px;text-decoration:none;border-radius:3px;display:inline-block;font-weight:bold;">View / Apply</a>
            </p>
            <p style="font-size:12px;margin:6px 0 0 0;">
                <a href="{applied_url}" style="color:#4CAF50;text-decoration:none;">✅ Applied</a> ·
                <a href="{passed_url}" style="color:#999;text-decoration:none;">❌ Passed</a>
            </p>
        </div>
            """
        )
    return "".join(chunks)


# --- Pipeline ---
def main() -> None:
    print(f"Job search starting at {datetime.now().isoformat()}")

    # Sanity: required env vars
    required = ["SERPAPI_KEY", "ANTHROPIC_API_KEY", "EMAIL_FROM", "EMAIL_TO", "EMAIL_PASSWORD"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"Missing required env vars: {missing}")
        sys.exit(1)

    rubric = load_rubric()
    feedback = get_feedback_from_sheets()
    sent_ids = load_sent_jobs()
    print(f"Already sent {len(sent_ids)} jobs in past runs.")

    all_jobs: list = []

    # Pass 1: geo
    for query in config.QUERIES:
        all_jobs.extend(search_google_jobs(query, config.LOCATION, config.DAYS_AGO))

    # Pass 2: explicit remote
    if config.INCLUDE_REMOTE_PASS:
        for query in config.QUERIES:
            all_jobs.extend(search_google_jobs(f"{query} remote", None, config.DAYS_AGO))

    # Dedup by job_id
    unique = {job.get("job_id", f"_idx_{i}"): job for i, job in enumerate(all_jobs)}
    all_jobs = list(unique.values())
    print(f"Unique jobs after dedup: {len(all_jobs)}")

    # Drop previously sent
    fresh = [j for j in all_jobs if j.get("job_id") not in sent_ids]
    print(f"New (not previously sent): {len(fresh)}")

    # Cheap pre-filters (excluded companies, salary floor)
    survivors = []
    for job in fresh:
        ok, why = passes_pre_filters(job)
        if ok:
            survivors.append(job)
        else:
            print(f"  Filtered out: {job.get('title')} @ {job.get('company_name')} — {why}")
    print(f"After pre-filters: {len(survivors)}")

    if not survivors:
        # Still send a "no matches" email so the user knows the pipeline ran
        send_email({"recommended": [], "worth_reviewing": [], "all": []}, fresh)
        # Mark fresh jobs as sent so we don't re-evaluate later
        sent_ids.extend(j.get("job_id") for j in fresh if j.get("job_id"))
        save_sent_jobs(sent_ids[-1500:])
        return

    print("Scoring with Claude...")
    scored = score_jobs_with_claude(survivors, feedback, rubric)
    print(
        f"Scored: {len(scored['recommended'])} recommended, "
        f"{len(scored['worth_reviewing'])} worth reviewing"
    )

    send_email(scored, survivors)

    # Write Tier 1 + Tier 2 job details to Sheet for Claude session queue
    all_surfaced = scored["recommended"] + scored["worth_reviewing"]
    write_job_details_to_sheet(all_surfaced, survivors)

    # Update sent list with everything we evaluated
    sent_ids.extend(j.get("job_id") for j in fresh if j.get("job_id"))
    save_sent_jobs(sent_ids[-1500:])
    print("Done.")


if __name__ == "__main__":
    main()
