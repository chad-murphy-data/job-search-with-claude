# Job-Search Scoring Rubric

This is the source of truth for how Claude scores incoming jobs.
**Edit anything here and re-run; the script reads this file directly.**

> 👋 This is a template. Replace every `[bracketed placeholder]` and rewrite the
> sections to match your own search. The structure (Profile → Hard disqualifiers
> → Positive signals → Preferred companies → Tier definitions → Scoring
> instructions) is what Claude expects, so keep the headings but fill them with
> your truth.

---

## Profile

**Current role:** [Your title at your current company, plus how long]
**Location:** [City, State]
**Geo preference:** [Where you'd take a hybrid role, OR remote, OR both. Be specific. E.g., "Hybrid in Austin metro, OR fully remote. On-site only = disqualify."]
**Salary floor:** $[N]. Below that = disqualify.
**Currently employed:** [Yes / No — passive vs. active search matters for how aggressively to surface borderline jobs.]

### Trajectory

[List 3–6 of your most recent or most relevant roles, newest first. Include company + dates + 1-line scope. Claude uses this to calibrate "what level is this person at."]

- [Role, Company, Years] — [1 line of scope]
- [Role, Company, Years] — [1 line of scope]
- ...

### Methods + tools

[The skills and tools you actually use. The more specific, the better the matching. E.g., "SQL, Python (pandas), causal inference, A/B testing, survey design." Avoid the kitchen-sink resume version.]

### Differentiators

[1–3 things that set you apart from a generic candidate at your level. These are the signals Claude will use to push borderline-but-interesting jobs into Tier 1. E.g., "Built three multi-agent AI research simulators" or "Published author on supply-chain optimization."]

### Domain breadth

[Industries / domains you have real stories from. E.g., "Fintech · Social platforms · Healthcare." If a job is in one of these, it scores higher.]

### Education

[Degrees + institutions. Mention publications, awards, or relevant honors if they matter to the level of roles you're targeting.]

---

## Hard disqualifiers (auto-fail, score ≤ 3)

These are the things you don't want to see in the digest at all. Be ruthless — every disqualifier here saves you reading time. Examples:

- **Salary explicitly below $[your floor].**
- [Title patterns that are downlevel for you, e.g., "Junior", "Associate", "Mid-Level"]
- [Role types you don't want — e.g., "Pure data-analyst roles with no strategy component"]
- [Required tools you don't have and won't learn — e.g., "Roles requiring Figma as a stated requirement"]
- **On-site only** (no hybrid or remote option), unless you'd actually move.
- Roles requiring [security clearance / certifications / specific licenses] you don't have.
- **Company = [your current employer]** (you don't need to be reminded your own employer is hiring).

## Title guidance

[Optional but useful. Some titles read junior at small companies but senior at big ones. Tell Claude how to handle ambiguity. Example below — rewrite or delete:]

**Do not auto-disqualify based on title alone if salary is at floor.** At large tech companies, titles like "[Researcher / Engineer / PM]" without a seniority prefix are often senior IC roles — evaluate by scope, salary, and required experience, not the title string.

**Years of experience as a signal:** If a posting requires 10+ years, treat it as appropriately leveled for [your level]. If it requires 3–5 years, treat it as likely downlevel — Tier 2 at best, exclude if other signals are weak.

## Strong positive signals (boost)

Things that should push a borderline job toward Tier 1. Examples — rewrite for your search:

- **Title** includes [Senior / Staff / Principal / Lead / Director / Head of …].
- [Methodology you specialize in — e.g., "Causal inference, RCTs, experimentation"]. +1
- [Framing or values that match yours — e.g., "Behavioral science / decision science framing"].
- [Hot area where you have unusual experience — e.g., "AI-adjacent roles"].
- Industries: [list].
- [Location preference — e.g., "Triangle-based or fully remote"].
- [Team-size or scope preference — e.g., "Smaller-team leadership over giant-org politics"].

## Preferred companies (whitelist)

If a posting is at one of these companies AND clears the hard disqualifiers
*that aren't about location* (salary floor, downlevel title, missing skills,
clearance, etc.), score it in Tier 1 regardless of softer fit signals.
Always surface them.

- [Dream company 1]
- [Dream company 2]

(Or delete this section entirely if you don't have a whitelist.)

## Tier definitions

**Tier 1 — Recommended (8–10):**
[Describe your sweet spot in 1–2 sentences. E.g., "Senior / Staff / Director title at right level, your core methodology, remote or in-region, at floor or above, in a domain you have strong stories for."]

**Tier 2 — Worth Reviewing (6–7):**
[Decent match but slightly off. Could be lateral comp, could be quant-light, could be a stretch in domain, could have a flag worth thinking about. Still worth a look.]

**Exclude (1–5):**
Hits any hard disqualifier, or is too far from the profile to be a realistic conversation.

## Scoring instructions for Claude

For each job, return the following fields:

- `job_number` — index from the input list
- `score` — integer 1–10
- `tier` — "recommended", "worth_reviewing", or "exclude"
- `reason` — 2–3 sentences on why this scored where it did
- `location_note` — e.g., "Remote", "Austin — 20 min commute", "Hybrid 2x/wk NYC"
- `salary_display` — the salary or range as written in the posting, or "Not listed" if absent
- `signals` — a short array of callout strings (3–5 items) flagging the specific rubric signals that drove the score. Use ✅ for positive signals and ⚠️ for cautions. Examples:
  - "✅ [strong positive signal from your rubric]"
  - "✅ Remote / [your region] hybrid"
  - "⚠️ Posting is 11 days old"
  - "⚠️ [common watch-out you want flagged]"
- `flag` — one honest "watch out" sentence, even for Tier 1 jobs. Surface the single thing most likely to give you pause. If there's genuinely nothing concerning, say so briefly.

### Additional rules

- Include all jobs scoring 6 or higher.
- If salary is mentioned and below the floor, exclude regardless of fit.
- If salary is not mentioned, score on fit and let the digest surface it.
- Prefer postings within the last 7 days; older postings get a small penalty.
- When in doubt between Tier 1 and Tier 2, lean Tier 2 — better to miss a borderline than wade through noise.
