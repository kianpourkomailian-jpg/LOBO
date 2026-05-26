"""
main.py
=======
Application entry point.

Boots the Drive connection, builds the full processing Pipeline, and starts
the FolderWatcher pointed at it. From here the system is fully autonomous:
new files dropped into 01_RAW_LINKEDIN_EXPORTS are downloaded, parsed,
cleaned, de-duplicated, scored, exported to 02_CLEANED_LEADS, archived to
03_PROCESSED_LEADS, and audit-logged to 06_LOGS.

Run:
    python -m app.main
"""

import time

from app.config import settings
from app.drive.drive_client import DriveClient
from app.drive.file_manager import FileManager
from app.drive.folder_watcher import FolderWatcher
from app.pipeline import Pipeline
from app.logs.logger import get_logger

log = get_logger(__name__)


def _ensure_auxiliary_folders(client: DriveClient) -> None:
    """
    Create folders that aren't part of the pre-existing structure if they're
    missing — currently 07_RAW_DUMP (ad-hoc free-text inbox). Idempotent.
    """
    root = client.get_root_folder()
    client.get_or_create_folder(settings.DRIVE_DUMP_FOLDER, parent_id=root["id"])
    log.info("Auxiliary folder ensured: %s", settings.DRIVE_DUMP_FOLDER)


def main() -> None:
    client = DriveClient()
    info = client.whoami()
    log.info("LOBO AI Leads running; connected as %s",
             info.get("user", {}).get("emailAddress"))

    _ensure_auxiliary_folders(client)

    # Build the pipeline (shares one FileManager/auth session) and watcher.
    file_manager = FileManager(client=client)
    pipeline = Pipeline(file_manager=file_manager)
    watcher = FolderWatcher(handler=pipeline.process_file, client=client)
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
