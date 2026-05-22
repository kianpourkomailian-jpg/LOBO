"""
folder_watcher.py
================
Watches the raw-exports folder for newly uploaded files.

How it works
------------
We POLL the folder on a fixed interval with APScheduler (rather than relying
on push notifications, which need a public webhook URL — overkill here). On
each tick we list the files in 01_RAW_LINKEDIN_EXPORTS and hand any *new,
supported* files to a handler callback.

What counts as "new"?
---------------------
Two layers, which together avoid double-processing without local storage:
  1. In-memory set of file ids already dispatched this run (cheap guard
     against picking the same file twice between polls).
  2. The pipeline itself MOVES a handled file out of the raw folder into
     03_PROCESSED_LEADS, so it won't appear in future listings at all.

The watcher only DETECTS and DISPATCHES — it does not parse. That keeps it
decoupled from the ingestion logic (added in Stage 3).
"""

from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.config.constants import SUPPORTED_UPLOAD_MIME_TYPES
from app.drive.drive_client import DriveClient
from app.logs.logger import get_logger

log = get_logger(__name__)

# A "handler" receives one file dict {id, name, mimeType, ...} per new file.
FileHandler = Callable[[dict], None]


class FolderWatcher:
    """Polls the raw-exports folder and dispatches new files to a handler."""

    def __init__(self, handler: FileHandler, client: DriveClient | None = None):
        self.handler = handler
        self.client = client or DriveClient()
        # Files we've already dispatched in this process lifetime.
        self._seen_ids: set[str] = set()
        self._scheduler = BackgroundScheduler()

    # ------------------------------------------------------------------
    # Decide whether a listed file is one we should process.
    # ------------------------------------------------------------------
    @staticmethod
    def _is_supported(file: dict) -> bool:
        """Accept by extension OR by Drive MIME type (ZIP / CSV / XLSX)."""
        name = file.get("name", "").lower()
        if name.endswith((".zip", ".csv", ".xlsx")):
            return True
        return file.get("mimeType") in SUPPORTED_UPLOAD_MIME_TYPES.values()

    # ------------------------------------------------------------------
    # One polling pass — also usable directly in tests.
    # ------------------------------------------------------------------
    def check_once(self) -> int:
        """
        Run a single scan. Returns the number of new files dispatched.

        Any exception from the handler is caught and logged so one bad file
        never kills the whole watcher loop.
        """
        raw_folder = self.client.get_subfolder(settings.DRIVE_RAW_FOLDER)
        files = self.client.list_files(raw_folder["id"])

        dispatched = 0
        for file in files:
            if file["id"] in self._seen_ids:
                continue
            if not self._is_supported(file):
                log.info("Skipping unsupported file: %s", file.get("name"))
                self._seen_ids.add(file["id"])  # don't re-evaluate every tick
                continue

            log.info("New file detected: %s", file.get("name"))
            self._seen_ids.add(file["id"])
            try:
                self.handler(file)
                dispatched += 1
            except Exception:  # noqa: BLE001 — keep the watcher alive
                log.exception("Handler failed for file: %s", file.get("name"))

        return dispatched

    # ------------------------------------------------------------------
    # Start/stop the background polling loop.
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Begin polling every WATCH_INTERVAL_SECONDS until the process ends."""
        interval = settings.WATCH_INTERVAL_SECONDS
        log.info(
            "Watching '%s' every %ss for new exports...",
            settings.DRIVE_RAW_FOLDER,
            interval,
        )
        self.check_once()  # run immediately on startup, then on schedule
        self._scheduler.add_job(self.check_once, "interval", seconds=interval)
        self._scheduler.start()

    def stop(self) -> None:
        """Stop the scheduler (used on shutdown)."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
