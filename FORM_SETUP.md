# Google Form + Sheet Setup

You need a Google Form (for the Applied/Passed feedback buttons in each email)
and a Google Sheet linked to that form (so the script can read your past
decisions and feed them to Claude on the next run). This takes ~10 minutes.

---

## 1. Create the Google Form

1. Go to https://forms.google.com → **Blank form**.
2. Name it something like **"Job Search Feedback"**.
3. Add these 5 questions, in this order:

   | # | Question | Type | Required? |
   |---|----------|------|-----------|
   | 1 | Job ID | Short answer | Yes |
   | 2 | Job Title | Short answer | Yes |
   | 3 | Company | Short answer | Yes |
   | 4 | Did you apply? | Multiple choice — options: `Applied ✅` and `Passed ❌` | Yes |
   | 5 | Why did you apply or pass? (Optional — helps improve recommendations) | Paragraph | No |

4. Click **Send** in the top right → copy the form's public URL. You won't paste this whole URL into the config — you just need the `formResponse` version, which you'll grab in step 2.

## 2. Get the field entry IDs

The script needs the `entry.XXXXXXX` ID for each question so it can pre-fill submissions when you click the Applied / Passed buttons in your email.

1. From the Form editor, click the three dots (⋮) in the top right → **Get pre-filled link**.
2. Fill in placeholder values for each field:
   - Job ID: `TEST_ID`
   - Job Title: `TEST_TITLE`
   - Company: `TEST_COMPANY`
   - Did you apply?: select `Applied ✅`
3. Click **Get link** at the bottom → **Copy link**.
4. The URL will look like:
   ```
   https://docs.google.com/forms/d/e/1FAIpQLS.../viewform?usp=pp_url&entry.1234567890=TEST_ID&entry.987654321=TEST_TITLE&entry.555555555=TEST_COMPANY&entry.111222333=Applied+%E2%9C%85
   ```
5. From this URL, pull out:
   - The **form ID** — the long string between `/e/` and `/viewform`. You'll build the `FORM_BASE_URL` as `https://docs.google.com/forms/d/e/<FORM_ID>/formResponse` (note the `formResponse` at the end, not `viewform`).
   - The **5 `entry.XXXXXXX` numbers**, in the order they appear, mapping to: job_id, title, company, feedback, reason. (The "reason" field doesn't appear in the pre-filled link since you left it blank, but you can find its `entry.` ID by inspecting the form in DevTools, or by filling in a dummy value when generating the pre-filled link.)

Paste these into `config.py`:

```python
FORM_BASE_URL = "https://docs.google.com/forms/d/e/YOUR_FORM_ID/formResponse"
FORM_FIELDS = {
    "job_id": "entry.1234567890",
    "title": "entry.987654321",
    "company": "entry.555555555",
    "feedback": "entry.111222333",
    "reason": "entry.444555666",
}
```

## 3. Link the Form to a Sheet

1. In the Form editor, click the **Responses** tab.
2. Click the green Sheets icon → **Create a new spreadsheet**.
3. Copy the Sheet's ID from the URL: `https://docs.google.com/spreadsheets/d/THIS_PART/edit` → that's the `GOOGLE_SHEET_ID` you'll add as a GitHub secret.

## 4. Service account for read/write access

The script reads your past feedback from the Sheet and writes Tier 1/Tier 2 job details to a `Job_Details` tab. Both need a Google service account.

1. Go to https://console.cloud.google.com → create a new project (or pick an existing one).
2. **APIs & Services** → **Library** → enable **Google Sheets API** and **Google Drive API**.
3. **APIs & Services** → **Credentials** → **Create credentials** → **Service account**.
4. Skip the optional steps; click **Done**.
5. Open the new service account → **Keys** tab → **Add key** → **Create new key** → **JSON**. Save the JSON file somewhere safe and **do not commit it** to your repo.
6. Open your Sheet from step 3 → **Share** (top right) → paste the service account's email (looks like `something@your-project.iam.gserviceaccount.com`) → give it **Editor** access (not just Viewer — the script needs to write the `Job_Details` tab).

## 5. What you need for GitHub secrets

By the end of this setup, you should have:

- `FORM_BASE_URL` and 5 `entry.*` field IDs → paste into `config.py`
- `GOOGLE_SHEET_ID` → GitHub Actions secret
- `GOOGLE_SHEETS_CREDENTIALS` → paste the entire contents of the service account JSON as a single GitHub Actions secret value

That's it. The rest of the secrets (`SERPAPI_KEY`, `ANTHROPIC_API_KEY`, `EMAIL_*`) are independent of this setup — see the main README for those.
