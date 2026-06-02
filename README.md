# LOBO AI Leads

A cloud-based AI lead ingestion platform for LOBO Systems. It watches a Google
Drive folder for LinkedIn exports, cleans and de-duplicates the leads, scores
and prioritises them, then writes the results back to Google Drive — **with no
reliance on local storage**, so it runs cleanly on Railway, Render, or Docker.

> **Build status:** Core pipeline complete (Stages 1–6). Drop a LinkedIn
> export into `01_RAW_LINKEDIN_EXPORTS` and the system parses, cleans,
> de-duplicates, scores, exports to `02_CLEANED_LEADS`, archives the raw file
> to `03_PROCESSED_LEADS`, and writes an audit trail to `06_LOGS` (created
> automatically). Future work: the `integrations/` connectors.

---

## Pipeline (target architecture)

```
Google Drive
  ↓ Folder Watcher        (poll 01_RAW_LINKEDIN_EXPORTS)
  ↓ Lead Ingestion        (ZIP / CSV / XLSX)
  ↓ LinkedIn Parsing
  ↓ Cleaning + Validation
  ↓ Suppression           (drop do-not-contact / existing customers)
  ↓ Deduplication
  ↓ Lead Scoring
  ↓ Export Clean Leads    (→ 02_CLEANED_LEADS)
  ↓ Archive Imports       (→ 03_PROCESSED_LEADS)
  ↓ Logging + Audit Trail
```

## Project layout

```
app/
  main.py              # entry point
  config/              # settings + constants + do_not_contact.txt (suppression list)
  drive/               # Google Drive auth + client (+ watcher/file_manager later)
  ingestion/           # zip/csv/linkedin parsing (later stages)
  cleaning/            # normalize / validators / suppression / dedupe
  scoring/             # lead scoring + priority engine (later stages)
  exports/             # export + upload cleaned leads (later stages)
  logs/                # logger + audit trail (later stages)
  integrations/        # dynamics / sheets / ai_calling / email (future)
scripts/
  test_connection.py   # Stage 1 smoke test
```

---

## Stage 1 — Google Drive setup

You need a Google service account that can see your `LOBO_AI_LEADS` Drive
folder. Follow these steps once.

### 1. Create a Google Cloud project
1. Go to <https://console.cloud.google.com/>.
2. Click the project dropdown → **New Project** → name it (e.g. `lobo-ai-leads`)
   → **Create**.

### 2. Enable the Google Drive API
1. In that project, open **APIs & Services → Library**.
2. Search for **Google Drive API** → **Enable**.

### 3. Create a service account
1. **APIs & Services → Credentials → Create Credentials → Service account**.
2. Give it a name (e.g. `lobo-drive-bot`) → **Create and continue** → **Done**.
   (No project roles are required — access is granted by sharing the folder.)

### 4. Create a JSON key
1. Open the service account → **Keys** tab → **Add key → Create new key**.
2. Choose **JSON** → **Create**. A `.json` file downloads.
3. Save it to `secrets/service_account.json` in this project (this path is
   git-ignored). For cloud hosts that only allow env vars, paste the file's
   contents into `GOOGLE_SERVICE_ACCOUNT_JSON` instead.

### 5. Share the Drive folder with the service account
This is the step people most often miss.

1. Open `service_account.json` and copy the `"client_email"` value
   (looks like `lobo-drive-bot@your-project.iam.gserviceaccount.com`).
2. In Google Drive, right-click the **`LOBO_AI_LEADS`** folder → **Share**.
3. Paste the service account email, give it **Editor** access, **Send**.

Because the folder is shared, the service account can now see it and all of its
subfolders — no folder IDs are hardcoded anywhere.

---

## Configure & run

```bash
# 1. Install dependencies (use a virtualenv)
pip install -r requirements.txt

# 2. Create your local env file and fill it in
cp .env.example .env
#    -> set GOOGLE_SERVICE_ACCOUNT_FILE (or GOOGLE_SERVICE_ACCOUNT_JSON)

# 3. Run the Stage 1 connection test
python -m scripts.test_connection
```

To run the whole system (watch + process continuously):

```bash
python -m app.main
```

You can also exercise each stage offline (no Drive needed):

```bash
python -m scripts.test_parser      # Stage 3: parsing
python -m scripts.test_cleaning    # Stage 4: normalize/validate/dedupe
python -m scripts.test_suppression # do-not-contact / existing-customer filter
python -m scripts.test_scoring     # Stage 5: scoring/priority
python -m scripts.test_pipeline    # Stage 6: full pipeline (fake Drive)
```

---

## Do-not-contact (existing-customer) suppression

Leads at companies we already work with — existing customers, or accounts
owned by another salesperson — are filtered out automatically during cleaning
so they never reach the cleaned leads or the call lists. The list lives in a
plain-text file you can edit:

```
app/config/do_not_contact.txt   # one company per line, '#' comments allowed
```

Add a line any time you win an account; the next import is filtered — no need
to clear leads by hand. Matching is deliberately forgiving (see
`app/cleaning/suppression.py`):

- case-, accent- and punctuation-insensitive (`Nestlé` = `nestle`),
- generic suffixes are ignored (`Ltd`, `Plc`, `Inc`, `Group`, `Company`, …),
- an entry matches when **every word of the entry** appears in the company, so
  use the shortest distinctive form:
  - `Kerry` → matches `Kerry`, `Kerry Foods`, `Kerry Group Plc`
  - `Coors` → matches `Molson Coors Beverage Company`

Whole-word matching keeps it precise: `Ford` won't match `Bradford`, and
`SSI Schaefer` won't match the prospect `Schaeffler`. Suppressed rows are
written to a `<run>_suppressed.csv` in `06_LOGS` (and counted in the run
summary) so you can always see exactly who was filtered and why. Point
`DO_NOT_CONTACT_FILE` at a different path to override the default list.

A successful connection test prints the authenticated service-account email
and confirms the root folder plus all five subfolders are reachable. If it
fails:

| Error | Likely cause |
|-------|--------------|
| `No Google credentials found` | `.env` path/JSON not set, or file missing |
| `Root folder '...' not found` | Folder not **shared** with the service account email |
| `Subfolder '...' not found` | Subfolder name in `.env` doesn't match Drive |

---

## Deployment

The app is stateless and config-driven, so it deploys cleanly to Railway,
Render, or any Docker host. Provide credentials via `GOOGLE_SERVICE_ACCOUNT_JSON`
(env var) or a mounted secret file, and set the folder-name variables from
`.env.example`.

### Docker
```bash
docker build -f dockerfile -t lobo-ai-leads .
docker run --rm \
  -e GOOGLE_SERVICE_ACCOUNT_JSON="$(cat secrets/service_account.json)" \
  -e DRIVE_ROOT_FOLDER_NAME=LOBO_AI_LEADS \
  lobo-ai-leads
```
Credentials are never baked into the image — pass them at runtime.

### Railway / Render
- Deploy from the repo; the platform builds the `dockerfile` automatically.
- Add the env vars from `.env.example` in the dashboard. Use
  `GOOGLE_SERVICE_ACCOUNT_JSON` (paste the whole JSON) since these hosts favour
  env vars over mounted files.
- The process runs `python -m app.main` and polls Drive on `WATCH_INTERVAL_SECONDS`.

## Future integrations

`app/integrations/` contains a shared `LeadIntegration` base class plus stub
connectors for **Dynamics**, **Google Sheets**, **AI calling**, and **email**.
Each is disabled (`enabled = False`) and logs intent without sending, so the
seam exists and is testable. Implement `send_leads()` and flip `enabled` to
activate one.
