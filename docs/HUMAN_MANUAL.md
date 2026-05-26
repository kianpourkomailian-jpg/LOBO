# LOBO AI Leads — Human Operator Manual

This is the day-to-day "how do I use it" guide. No code knowledge needed.
If something here doesn't match what you see, ping whoever maintains the
codebase — the README has the technical detail.

---

## 1. What this system does, in one paragraph

You drop a LinkedIn export (or any LinkedIn-format CSV/XLSX) into a Google
Drive folder. The system notices the file within ~1 minute, downloads it,
removes blanks/duplicates/bad records, scores each lead, and writes a clean
CSV back to Drive. The original file is moved to an "already processed"
folder so you can see what's been handled. Every run also drops a small
audit report into a logs folder so you can see exactly what was kept or
dropped, and why.

## 2. The Drive folders you need to know

In Google Drive, inside `LOBO_AI_LEADS/`:

| Folder | What it's for | Who writes to it |
|---|---|---|
| `01_RAW_LINKEDIN_EXPORTS` | **You drop files here.** | You |
| `02_CLEANED_LEADS` | Clean, scored CSV output. | The system |
| `03_PROCESSED_LEADS` | The original files, after the system finished with them. | The system |
| `04_CALL_HISTORY` | Reserved for future call-system integration. | (future) |
| `05_DONOT_CONTACT` | Reserved for the do-not-contact list. | You / future |
| `06_LOGS` | Audit reports (created automatically on the first run). | The system |

You only ever need to interact with **`01_RAW_LINKEDIN_EXPORTS`** to add
work, and **`02_CLEANED_LEADS`** to get results.

## 3. How to add leads

### Option A — LinkedIn export (the normal path)
1. On LinkedIn: **Me → Settings & Privacy → Data Privacy → Get a copy of
   your data → Connections** → request and download the `.zip`.
2. Drop the `.zip` (or just `Connections.csv` from inside it) into
   `01_RAW_LINKEDIN_EXPORTS`.
3. Wait ~1 minute. Done.

### Option B — A spreadsheet you built yourself
The columns the system understands are: **First Name, Last Name, URL, Email
Address, Company, Position, Connected On, Location, Notes**. Anything else
is ignored. Save as `.csv` or `.xlsx` and drop it into the same folder.

> **Tip.** You don't need every column filled. Anything blank stays blank.
> A row is only rejected if it has NO name AND NO company AND NO email.

## 4. How to read the output

In `02_CLEANED_LEADS` you'll find a file named like:

```
cleaned_<original-name>_20260526_143000.csv
```

The columns, in order:

| Column | What it is |
|---|---|
| `full_name` | Combined first + last name |
| `first_name`, `last_name` | Self-explanatory |
| `company` | Tidy-cased company name |
| `role` | Job title |
| `email` | Lower-cased + trimmed |
| `linkedin_profile` | The LinkedIn URL |
| `location` | If LinkedIn provided one |
| `connection_date` | Re-formatted as `YYYY-MM-DD` |
| `lead_score` | A number 0–100 (higher = better fit) |
| `lead_priority` | `HIGH`, `MEDIUM`, or `LOW` (filter on this) |
| `notes` | Notes column from the source, if any |

**Quick way to use it:** open the CSV, sort by `lead_priority = HIGH`, and
work that list first.

## 5. What the score is based on

Higher scores are awarded for:

- **High-value job titles**: maintenance manager, engineering manager,
  operations manager, plant manager, maintenance supervisor, director of
  operations, head of engineering. *(One-off bonus: 50 points.)*
- **High-value industries** in the company or role text: manufacturing,
  industrial, engineering, utilities, logistics, food production.
  *(15 points each.)*
- **Decision-maker keywords** in the role: manager, director, head of,
  supervisor, operations, engineering. *(10 points each.)*

Scores are capped at 100. Priority buckets:

| Priority | Score |
|---|---|
| HIGH | 70+ |
| MEDIUM | 40–69 |
| LOW | below 40 |

If you ever want to retune these, ask the maintainer — they live in one
file (`app/config/constants.py`) and only need numbers tweaked, no code.

## 6. The audit folder (`06_LOGS`)

For every file processed you'll see three artifacts, all timestamped:

- `<ts>_<source>_summary.json` — counts at a glance: how many were parsed,
  how many valid, how many dropped, how many duplicates, how many exported.
- `<ts>_<source>_duplicates.csv` — the rows the system treated as duplicates
  (only created if there were any). Includes a `duplicate_reason` column.
- `<ts>_<source>_invalid.csv` — the rows that failed validation
  (`blank_row`, `invalid_email`, or `invalid_linkedin_url`).

If a number ever surprises you (e.g. "I uploaded 500 and only see 300"),
open the latest `summary.json` and the two CSVs. You'll see exactly where
the missing rows went.

## 7. What "duplicate" means here

The system marks two rows as the same lead when:

- They share a non-empty **email** address, OR
- They share a non-empty **LinkedIn URL**, OR
- Their **names are very similar AND their companies are similar** (this
  catches "Acme Mfg" vs "Acme Manufacturing" for the same person).

It is deliberately careful not to merge two different people who simply
work at the same company.

## 8. What can go wrong

| Symptom | What it usually means | Fix |
|---|---|---|
| File sits in `01_RAW_…` and nothing happens | Service isn't running, OR you uploaded an unsupported type | Check `.csv`/`.xlsx`/`.zip`; ask maintainer if the watcher is up |
| File processed but **no** cleaned output | Every row was blank/invalid | Open the `_invalid.csv` in `06_LOGS` |
| Cleaned file has fewer rows than expected | Duplicates removed | Open the `_duplicates.csv` in `06_LOGS` |
| `connection_date` is blank | The source date wasn't a format the parser understood | Safe to ignore; the lead is still valid |
| Whole scoring feels off | Weights or thresholds need tuning for your market | Ask maintainer to edit `app/config/constants.py` |

## 9. Adding leads to Airtable manually

If you spot a one-off lead outside the LinkedIn flow, you can just ask the
assistant (or whoever maintains this system) to add it to Airtable. Example
phrasing that works well:

> "Add `http://example.com/` Jane Doe — Maintenance Manager — to Airtable."

The assistant will create a record in the `LOBO Outbound System` base,
`Active Leads` table.

## 10. Do-not-contact

Drop a CSV with at least an `email` column (or `linkedin_profile` column)
into `05_DONOT_CONTACT`. **Note:** the suppression step is on the roadmap
but not yet enforced by the pipeline — for now this folder is the source
of truth, and the maintainer can wire it in.

## 11. Who to ask

- **"Something isn't running"** → maintainer / engineer.
- **"I want to change scoring"** → maintainer (one-line edits).
- **"How do I get more leads in"** → just drop more files into
  `01_RAW_LINKEDIN_EXPORTS`. The system handles concurrency fine.
- **"Can it push to CRM / Sheets / email / call platform?"** → yes, those
  integrations are scaffolded; the engineer needs to enable them.
