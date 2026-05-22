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
