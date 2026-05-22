"""
settings.py
===========
Central place where ALL configuration is read from the environment.

Why this file exists
--------------------
Instead of scattering os.getenv() calls across the codebase, we read every
setting ONCE here and expose simple constants. Every other module imports
from here. This keeps configuration:
  * easy to find,
  * easy to change,
  * safe (we validate required values up front).

It uses python-dotenv so that, during local development, a ".env" file is
loaded automatically. In the cloud (Railway/Render) the real environment
variables are used and the missing .env file is simply ignored.
"""

import os
from dotenv import load_dotenv

# Load variables from a local ".env" file if present.
# In production this does nothing harmful — real env vars still win.
load_dotenv()


# --- Google authentication ------------------------------------------
# Two supported ways to provide credentials (file OR inline JSON string).
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE", "./secrets/service_account.json"
)
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()


# --- Drive folder names (looked up dynamically, never hardcoded IDs) -
DRIVE_ROOT_FOLDER_NAME = os.getenv("DRIVE_ROOT_FOLDER_NAME", "LOBO_AI_LEADS")
DRIVE_RAW_FOLDER = os.getenv("DRIVE_RAW_FOLDER", "01_RAW_LINKEDIN_EXPORTS")
DRIVE_CLEANED_FOLDER = os.getenv("DRIVE_CLEANED_FOLDER", "02_CLEANED_LEADS")
DRIVE_PROCESSED_FOLDER = os.getenv("DRIVE_PROCESSED_FOLDER", "03_PROCESSED_LEADS")
DRIVE_CALL_HISTORY_FOLDER = os.getenv("DRIVE_CALL_HISTORY_FOLDER", "04_CALL_HISTORY")
DRIVE_DONOT_CONTACT_FOLDER = os.getenv("DRIVE_DONOT_CONTACT_FOLDER", "05_DONOT_CONTACT")

# Optional Shared Drive id (blank = normal "My Drive" sharing).
DRIVE_SHARED_DRIVE_ID = os.getenv("DRIVE_SHARED_DRIVE_ID", "").strip()


# --- Scheduling / logging -------------------------------------------
WATCH_INTERVAL_SECONDS = int(os.getenv("WATCH_INTERVAL_SECONDS", "60"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def validate() -> None:
    """
    Fail fast with a clear message if credentials are not configured.

    We accept EITHER an inline JSON string OR a path to a JSON file.
    Called at startup (and by the test script) so misconfiguration is
    caught immediately instead of deep inside an API call.
    """
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        return  # inline JSON provided — good enough to attempt auth

    if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
        raise RuntimeError(
            "No Google credentials found.\n"
            f"  - GOOGLE_SERVICE_ACCOUNT_JSON is empty, and\n"
            f"  - file '{GOOGLE_SERVICE_ACCOUNT_FILE}' does not exist.\n"
            "Set one of them in your .env file. See .env.example."
        )
