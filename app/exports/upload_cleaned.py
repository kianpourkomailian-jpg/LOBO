"""
upload_cleaned.py
================
Uploads a cleaned lead DataFrame as a CSV into the 02_CLEANED_LEADS folder.

It ties together:
  * export_clean_csv.to_csv_bytes  (DataFrame -> CSV bytes)
  * FileManager.upload_bytes       (bytes -> Google Drive)

Output filenames are derived from the source export name plus a UTC timestamp,
so repeated runs never overwrite each other and stay easy to trace.
"""

from datetime import datetime, timezone

import pandas as pd

from app.config import settings
from app.config.constants import SUPPORTED_UPLOAD_MIME_TYPES
from app.drive.file_manager import FileManager
from app.logs.logger import get_logger

log = get_logger(__name__)


def _output_name(source_filename: str) -> str:
    """Build 'cleaned_<source-stem>_<UTC timestamp>.csv'."""
    stem = source_filename.rsplit(".", 1)[0]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"cleaned_{stem}_{ts}.csv"


def upload_cleaned(
    df: pd.DataFrame,
    source_filename: str,
    file_manager: FileManager,
) -> dict:
    """
    Export `df` to CSV and upload it to 02_CLEANED_LEADS.

    Returns the created Drive file's metadata {id, name}.
    """
    from app.exports.export_clean_csv import to_csv_bytes

    cleaned_folder = file_manager.client.get_subfolder(settings.DRIVE_CLEANED_FOLDER)
    data = to_csv_bytes(df)
    name = _output_name(source_filename)

    result = file_manager.upload_bytes(
        folder_id=cleaned_folder["id"],
        filename=name,
        data=data,
        mime_type=SUPPORTED_UPLOAD_MIME_TYPES["csv"],
    )
    log.info("Uploaded cleaned leads: %s (%d rows)", result.get("name"), len(df))
    return result
