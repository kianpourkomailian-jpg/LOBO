"""
constants.py
============
Fixed values that do NOT change per-environment and are shared across the app.

Keeping these here (instead of inside settings.py) separates:
  * settings.py  -> values that vary by deployment (.env driven)
  * constants.py -> values that are part of the program's design

For Stage 1 we only need the Google API scope and MIME types used when
searching for / creating folders and identifying uploadable file types.
Later stages (scoring, parsing) will add more constants here.
"""

# OAuth scope. "drive" gives full read/write access to files the service
# account can see. This is required to download raw exports, upload cleaned
# files, and move processed files between folders.
GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

# Google Drive uses this special MIME type to represent a folder.
MIME_FOLDER = "application/vnd.google-apps.folder"

# File types the ingestion pipeline will accept (used from Stage 2 on).
SUPPORTED_UPLOAD_MIME_TYPES = {
    "zip": "application/zip",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# ── Standardized lead schema ────────────────────────────────────────
# Every processed lead row has exactly these columns, in this order.
# Parsers map their raw input onto this; later stages fill score/priority.
LEAD_SCHEMA = [
    "full_name",
    "first_name",
    "last_name",
    "company",
    "role",
    "email",
    "linkedin_profile",
    "location",
    "connection_date",
    "lead_score",
    "lead_priority",
    "notes",
]

# ── LinkedIn export -> schema column mapping ────────────────────────
# LinkedIn's "Connections.csv" header names (left) -> our schema (right).
# Keys are lower-cased + stripped before matching, so casing/whitespace
# differences across export versions don't break the mapping.
LINKEDIN_COLUMN_MAP = {
    "first name": "first_name",
    "last name": "last_name",
    "company": "company",
    "position": "role",
    "title": "role",                 # some exports call it "Title"
    "email address": "email",
    "email": "email",
    "url": "linkedin_profile",
    "profile url": "linkedin_profile",
    "connected on": "connection_date",
    "location": "location",
    "notes": "notes",
}

# Columns we use to recognise the real header row inside a LinkedIn CSV
# (which often has a few preamble/notes lines above the header).
LINKEDIN_HEADER_MARKERS = {"first name", "last name", "url", "company"}
