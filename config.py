"""
Non-secret configuration. Edit freely.
Secrets live in environment variables (see .env.example).

This file is a template — replace the placeholder values with your own search.
"""

# --- Search ---
# Each query gets fanned out against the location. Keep this list tight (~8) — token cost scales with results.
# Example queries below; replace with the titles you actually want to see.
QUERIES = [
    "Senior Software Engineer",
    "Staff Software Engineer",
    "Principal Engineer",
]

# Primary location string used for the SerpAPI google_jobs engine.
# Format: "City, State, Country" works well.
LOCATION = "Austin, Texas, United States"

# We run a second pass for fully-remote roles by appending "remote" to each query.
INCLUDE_REMOTE_PASS = True

# How far back to look. SerpAPI's chips filter is monthly; this is a secondary client-side filter.
DAYS_AGO = 14

# --- Excluded companies ---
# Case-insensitive substring match against company_name. Add competitors / past employers / etc. as needed.
EXCLUDED_COMPANIES = [
    # "your current employer",
]

# --- Preferred companies (whitelist) ---
# If a posting matches one of these AND clears all hard disqualifiers in RUBRIC.md,
# Claude should surface it in Tier 1 regardless of softer fit signals.
PREFERRED_COMPANIES = [
    # "dream company",
]

# --- Salary floor ---
# If a job posting explicitly mentions salary below this, it's auto-excluded.
# Postings without salary info are scored on fit alone.
SALARY_FLOOR_USD = 150_000

# --- Claude model ---
CLAUDE_MODEL = "claude-sonnet-4-6"

# --- Google Form ---
# Fill these in after completing FORM_SETUP.md.
# FORM_BASE_URL ends with /formResponse (not /viewform).
FORM_BASE_URL = "https://docs.google.com/forms/d/e/REPLACE_WITH_YOUR_FORM_ID/formResponse"
FORM_FIELDS = {
    "job_id": "entry.REPLACE",
    "title": "entry.REPLACE",
    "company": "entry.REPLACE",
    "feedback": "entry.REPLACE",
    "reason": "entry.REPLACE",
}

# --- Files ---
SENT_JOBS_FILE = "sent_jobs.json"
RUBRIC_FILE = "RUBRIC.md"

# --- Cap on context to Claude ---
# Truncate descriptions before sending to Claude (saves tokens, descriptions are usually padded).
DESCRIPTION_CHAR_LIMIT = 1500
