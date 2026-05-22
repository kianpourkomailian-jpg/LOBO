"""
auth.py
=======
Builds an authenticated Google Drive API client using a SERVICE ACCOUNT.

What is a service account?
--------------------------
A service account is a special "robot" Google account that belongs to your
Google Cloud project rather than to a human. It authenticates with a private
key (a JSON file) instead of a username/password. This is ideal for servers
because there is no interactive login screen — perfect for cloud deployment.

What this file does
-------------------
1. Loads the service account credentials, from EITHER:
     - an inline JSON string (env var), useful on hosts that only allow
       environment variables, OR
     - a JSON key file on disk.
2. Creates a `googleapiclient` Drive v3 service object that the rest of the
   app uses to talk to Google Drive.
"""

import json

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import settings
from app.config.constants import GOOGLE_DRIVE_SCOPES


def _load_credentials() -> service_account.Credentials:
    """
    Build credentials from inline JSON if provided, otherwise from a file.

    Inline JSON takes priority because cloud hosts (Railway/Render) often make
    it easier to paste a secret string than to mount a file.
    """
    if settings.GOOGLE_SERVICE_ACCOUNT_JSON:
        info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
        return service_account.Credentials.from_service_account_info(
            info, scopes=GOOGLE_DRIVE_SCOPES
        )

    return service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=GOOGLE_DRIVE_SCOPES
    )


def get_drive_service():
    """
    Return an authenticated Google Drive v3 service object.

    Usage:
        service = get_drive_service()
        service.files().list(...).execute()

    `cache_discovery=False` silences a harmless warning and avoids writing a
    discovery cache to disk (we want NO local persistence).
    """
    settings.validate()  # fail early with a clear error if misconfigured
    credentials = _load_credentials()
    return build("drive", "v3", credentials=credentials, cache_discovery=False)
