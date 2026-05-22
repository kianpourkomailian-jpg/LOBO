"""
main.py
=======
Application entry point.

Stage 2: boots the Drive connection and starts the folder watcher. New files
in 01_RAW_LINKEDIN_EXPORTS are detected and logged. The real ingestion handler
(parse -> clean -> score -> export -> archive) is plugged in from Stage 3.

Run:
    python -m app.main
"""

import time

from app.drive.drive_client import DriveClient
from app.drive.folder_watcher import FolderWatcher
from app.logs.logger import get_logger

log = get_logger(__name__)


def _placeholder_handler(file: dict) -> None:
    """
    Temporary handler used until Stage 3.

    For now we just acknowledge the file. We deliberately do NOT move it yet,
    so nothing is lost before the parsing pipeline exists.
    """
    log.info("Detected (no pipeline yet): %s [%s]", file.get("name"), file.get("id"))


def main() -> None:
    client = DriveClient()
    info = client.whoami()
    log.info("LOBO AI Leads running; connected as %s",
             info.get("user", {}).get("emailAddress"))

    watcher = FolderWatcher(handler=_placeholder_handler, client=client)
    watcher.start()

    # Keep the process alive so the background scheduler keeps polling.
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down watcher...")
        watcher.stop()


if __name__ == "__main__":
    main()
