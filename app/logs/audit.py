"""
audit.py
=======
Writes a human-readable AUDIT TRAIL for every processed file, straight to
Google Drive (no local logs — same statelessness rule as the rest).

For each run we upload, into a dynamically-created '06_LOGS' folder:
  * <ts>_<source>_summary.json  — counts + status for the whole run
  * <ts>_<source>_duplicates.csv — the duplicate rows skipped (if any)
  * <ts>_<source>_invalid.csv    — the invalid rows dropped (if any)

The JSON summary is the at-a-glance record; the CSVs let a human inspect
exactly what was skipped and why. Timestamps (UTC) keep runs ordered and
prevent overwrites.
"""

import json
from datetime import datetime, timezone

import pandas as pd

from app.config import settings
from app.config.constants import SUPPORTED_UPLOAD_MIME_TYPES
from app.drive.file_manager import FileManager
from app.logs.logger import get_logger

log = get_logger(__name__)

LOGS_FOLDER_NAME = "06_LOGS"


class AuditLogger:
    """Uploads per-run audit artifacts to the Drive logs folder."""

    def __init__(self, file_manager: FileManager):
        self.fm = file_manager
        self._logs_folder_id: str | None = None  # resolved lazily + cached

    def _logs_folder(self) -> str:
        """Return the 06_LOGS folder id, creating it under root if needed."""
        if self._logs_folder_id is None:
            root = self.fm.client.get_root_folder()
            folder = self.fm.client.get_or_create_folder(
                LOGS_FOLDER_NAME, parent_id=root["id"]
            )
            self._logs_folder_id = folder["id"]
        return self._logs_folder_id

    @staticmethod
    def _stem(source_filename: str) -> str:
        return source_filename.rsplit(".", 1)[0]

    def log_run(
        self,
        source_filename: str,
        counts: dict,
        duplicates: pd.DataFrame | None = None,
        invalid: pd.DataFrame | None = None,
        parse_error: str | None = None,
    ) -> None:
        """
        Upload the audit artifacts for one processed file.

        `counts` is a dict like:
            {"parsed": 100, "valid": 95, "invalid": 5,
             "duplicates": 10, "exported": 85}
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        prefix = f"{ts}_{self._stem(source_filename)}"
        folder_id = self._logs_folder()

        # 1) JSON summary — always written.
        summary = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "source_file": source_filename,
            "status": "error" if parse_error else "ok",
            "parse_error": parse_error,
            "counts": counts,
        }
        self.fm.upload_bytes(
            folder_id=folder_id,
            filename=f"{prefix}_summary.json",
            data=json.dumps(summary, indent=2).encode("utf-8"),
            mime_type="application/json",
        )

        # 2) Duplicate rows CSV — only if there were any.
        if duplicates is not None and not duplicates.empty:
            self.fm.upload_bytes(
                folder_id=folder_id,
                filename=f"{prefix}_duplicates.csv",
                data=duplicates.to_csv(index=False).encode("utf-8"),
                mime_type=SUPPORTED_UPLOAD_MIME_TYPES["csv"],
            )

        # 3) Invalid rows CSV — only if there were any.
        if invalid is not None and not invalid.empty:
            self.fm.upload_bytes(
                folder_id=folder_id,
                filename=f"{prefix}_invalid.csv",
                data=invalid.to_csv(index=False).encode("utf-8"),
                mime_type=SUPPORTED_UPLOAD_MIME_TYPES["csv"],
            )

        log.info("Audit logged for '%s': %s", source_filename, counts)
