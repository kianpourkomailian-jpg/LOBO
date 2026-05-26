# LOBO AI Leads — AI Operator Manual

This is the brief for any AI assistant (Claude or otherwise) working in
this repository. Read it before making changes. It encodes the
architectural rules the project depends on; following them keeps changes
safe and reversible.

---

## 1. What the system is

A Google-Drive-native lead ingestion pipeline. A folder watcher detects
LinkedIn exports, the pipeline parses → normalizes → validates → dedupes →
scores → exports → archives → audits. Stages are decoupled and each is
independently testable offline.

## 2. Architectural rules (do not break these)

1. **No local persistence.** Every byte that moves lives in `io.BytesIO`.
   No temp files, no caches, no on-disk state. The container is ephemeral.
2. **No hardcoded Drive folder IDs.** Always resolve by name via
   `DriveClient.find_folder` / `get_subfolder` / `get_or_create_folder`.
   Folder names come from `app/config/settings.py` (env-driven).
3. **Credentials are runtime-only.** Never write them to git or bake them
   into the Docker image. The service account is provided either as a
   file path or as an inline JSON string env var.
4. **Schema is fixed.** Every processed lead has exactly the columns in
   `LEAD_SCHEMA` (`app/config/constants.py`), in that order. Add a column
   only by extending `LEAD_SCHEMA` and updating parsers to fill it.
5. **Stages are decoupled.** Parsing doesn't clean. Cleaning doesn't
   score. Scoring doesn't export. If you find yourself reaching across
   stages, stop and reconsider.
6. **Rules live in `constants.py`, logic lives in modules.** Scoring
   weights, keyword lists, priority thresholds, the LinkedIn column map,
   and `LEAD_SCHEMA` are all data. Editing data should never require
   editing logic.
7. **Each stage isolates failures.** A bad ZIP member doesn't kill the
   ZIP; a bad file doesn't kill the watcher; a parse error logs an audit
   record but does NOT move the raw file (so it can be inspected).

## 3. Repo map

```
app/
  main.py                      # entry: builds Drive client, pipeline, watcher
  pipeline.py                  # the conductor (download→…→archive→audit)
  config/
    settings.py                # env-driven (auto-loads .env)
    constants.py               # schema, mapping, scoring rules — EDIT HERE for tuning
  drive/
    auth.py                    # service-account credential loader
    drive_client.py            # folder lookup, list, get_or_create (no IDs hardcoded)
    file_manager.py            # in-memory download/upload/move
    folder_watcher.py          # APScheduler polling + dispatch
  ingestion/
    zip_handler.py             # extract CSV/XLSX from ZIP in memory
    csv_parser.py              # CSV/XLSX readers + header-row detection
    linkedin_parser.py         # LinkedIn columns → LEAD_SCHEMA
  cleaning/
    normalize.py               # trim, case, ISO dates, tidy URLs
    validators.py              # split valid/invalid (with reason)
    dedupe.py                  # exact (email/linkedin) + fuzzy (name+company)
  scoring/
    lead_scoring.py            # weighted points → lead_score
    priority_engine.py         # lead_score → HIGH/MEDIUM/LOW
  exports/
    export_clean_csv.py        # DataFrame → schema-ordered CSV bytes
    upload_cleaned.py          # bytes → 02_CLEANED_LEADS
  logs/
    logger.py                  # console logger (env-driven level)
    audit.py                   # per-run summary + duplicate/invalid CSVs → 06_LOGS
  integrations/
    base.py                    # LeadIntegration ABC (.send_leads(df))
    dynamics/  sheets/  ai_calling/  email/   # stubs awaiting implementation
scripts/                       # offline test scripts (no Drive needed)
dockerfile, .dockerignore      # container build
```

## 4. The control flow, end to end

`FolderWatcher.check_once()` lists files in `01_RAW_LINKEDIN_EXPORTS`,
filters by extension/MIME, and dispatches each new file dict to
`Pipeline.process_file(file)`, which:

1. `FileManager.download_to_memory(file_id)` → `BytesIO`
2. `linkedin_parser.parse(name, buffer)` → `DataFrame` (LEAD_SCHEMA shape)
3. `normalize.normalize(df)`
4. `validators.validate(df)` → `(valid, invalid)`
5. `dedupe.dedupe(valid)` → `(unique, duplicates)`
6. `lead_scoring.score_leads(unique)`
7. `priority_engine.assign_priority(...)`
8. `upload_cleaned(final, source_filename, file_manager)` → `02_CLEANED_LEADS`
9. `FileManager.move_file(file_id, processed_folder_id)`
10. `AuditLogger.log_run(name, counts, duplicates, invalid)` → `06_LOGS`

## 5. How to extend the system

### Add a new lead column
1. Add the name to `LEAD_SCHEMA` in `constants.py`.
2. Map it in `LINKEDIN_COLUMN_MAP` if it comes from a LinkedIn export.
3. Fill it in `linkedin_parser._map_to_schema` if it's computed.
4. `export_clean_csv.to_csv_bytes` will pick it up automatically (it
   reads from `LEAD_SCHEMA`).

### Retune scoring
Edit `constants.py`:
- `HIGH_VALUE_ROLES`, `HIGH_VALUE_INDUSTRIES`, `DECISION_MAKER_KEYWORDS`
- `SCORING_WEIGHTS` (per-match point values)
- `PRIORITY_THRESHOLDS` (HIGH/MEDIUM cutoffs)

No logic file should need changing.

### Add a new source format
1. Add a member-reader in `csv_parser.py` if the file type is new.
2. Add a parser sibling next to `linkedin_parser.py` that returns a
   LEAD_SCHEMA-shaped frame.
3. Dispatch on extension in `pipeline.process_file` (or generalise the
   parser registry — keep it simple until there's a third format).

### Implement an integration
1. Implement `send_leads(self, df)` in the stub
   (`app/integrations/<name>/<name>_client.py`).
2. Make `enabled` return `True` when its env vars are present.
3. Wire it into `Pipeline.process_file` after `upload_cleaned`, e.g.:
   ```python
   for integration in [DynamicsIntegration(), SheetsIntegration(), …]:
       if integration.enabled:
           integration.send_leads(final)
   ```
4. Add env vars to `.env.example` and the README deployment section.

### Add a new Drive folder
Add it to `.env.example`, expose it in `settings.py`, and access it via
`DriveClient.get_subfolder(settings.NEW_FOLDER_NAME)`. **Don't** introduce
folder IDs anywhere.

## 6. Testing

Every stage has an offline test in `scripts/` that runs with no Drive:

```
python -m scripts.test_connection   # Stage 1 — real Drive (needs creds)
python -m scripts.test_watcher      # Stage 2 — real Drive (one scan)
python -m scripts.test_parser       # Stage 3 — fully offline
python -m scripts.test_cleaning     # Stage 4 — fully offline
python -m scripts.test_scoring      # Stage 5 — fully offline
python -m scripts.test_pipeline     # Stage 6 — fully offline (fake Drive)
```

When you add behaviour, add or update one of these. The fake-Drive
pattern in `test_pipeline.py` is the template for any new pipeline test:
implement just the `FakeClient`/`FakeFileManager` methods that your code
path touches.

## 7. Conventions to follow

- **Imports**: grouped stdlib / third-party / local; absolute (`from app.…`).
- **Logging**: `from app.logs.logger import get_logger; log = get_logger(__name__)`.
  Don't use `print` outside `scripts/`.
- **Errors**: catch broadly (`except Exception`) only at stage seams (a
  ZIP member, a single file in the watcher, a parse step). Everywhere
  else, let exceptions propagate so issues surface.
- **DataFrames**: pass copies, not views (`df = df.copy()` at the top of
  functions that mutate). Always assume input columns may be missing.
- **No comments that restate the code.** Comments should explain *why*,
  not *what*. Prefer clear names.
- **No new top-level dependencies** without adding them to
  `requirements.txt` with a pinned version.
- **Never** import `os.getenv` outside `settings.py`. All configuration
  flows through that module.

## 8. Things that look tempting but are wrong

- "I'll write parsing output to `/tmp` so I can inspect it." → **No.**
  Add a one-off `scripts/` test instead.
- "I'll cache folder IDs as constants for speed." → **No.** Folder names
  may change between deployments; lookups are cheap.
- "I'll merge two records aggressively if names are similar." → **No.**
  Dedupe requires similarity on both name AND company. Aggressive merging
  is the worst silent failure mode this system has.
- "I'll silently drop bad rows." → **No.** Drop them into `invalid_df`
  with a reason. The audit trail depends on it.
- "I'll add a try/except around the whole pipeline so it never crashes."
  → **No.** The watcher already isolates handler failures per file.
  Burying errors any further makes diagnosis impossible.

## 9. Working with Airtable from this codebase

The companion CRM lives in the Airtable base **"LOBO Outbound System"**
(base id `appn47vi9R3sLiEof`). Tables: `Active Leads`, `Recycled Leads`,
`Called Leads`, `Follow-Ups`, `Archived Leads`. All five tables share the
same schema (Company Name, Contact Name, Job Title, LinkedIn URL, Email,
Phone, Industry, AI Score, Status, etc.).

When asked to add a lead via Airtable MCP tools:
- Default destination is **`Active Leads`** unless the user specifies.
- Map our `lead_score` → Airtable `AI Score`, `lead_priority` → `Status`
  *only if* a matching choice exists on the singleSelect — otherwise
  leave Status blank and put the priority in Notes.
- If the user provides a website URL, put it in **Notes** (the LinkedIn
  URL field expects a `linkedin.com` URL).
- Always look up `tableId`/`fieldId` via `list_tables_for_base` —
  **never** substitute user-facing names for IDs in `create_records_for_table`
  payloads.

## 10. Pull request and commit conventions

- Develop on the branch the harness specifies; never push to `main`
  without explicit instruction.
- Commit subject line ≤ 70 chars; body explains *why*.
- Don't create a PR unless the user asks.
- Don't include model identifiers, internal session ids, or marketing
  names in commit messages or code.

## 11. When in doubt

- Read `constants.py` first. Most "where do I configure X" answers are
  there.
- Read the relevant `scripts/test_*.py` next — it shows the canonical
  input/output shape for that stage.
- If a change spans more than one stage, you're probably about to
  violate rule 5 (decoupling). Split it.
