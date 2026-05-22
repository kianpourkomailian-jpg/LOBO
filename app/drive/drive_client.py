"""
drive_client.py
===============
A thin, friendly wrapper around the raw Google Drive API.

Why a wrapper?
--------------
The raw Drive API is verbose and easy to get wrong (query escaping, Shared
Drive flags, pagination). This class centralises that complexity so the rest
of the app can call simple methods like `find_folder("02_CLEANED_LEADS")`.

Design rules honoured here
--------------------------
* We NEVER hardcode folder IDs. Folders are looked up by NAME at runtime.
* Everything works in the cloud (no local storage assumptions).
* Shared Drives are supported transparently via the include* flags.

Stage 1 scope
-------------
This client provides folder discovery + listing + a connectivity check.
Upload / download / move operations live in `file_manager.py` (Stage 2),
which will build on top of this client.
"""

from app.drive.auth import get_drive_service
from app.config import settings
from app.config.constants import MIME_FOLDER


class DriveClient:
    """Authenticated helper for talking to Google Drive."""

    def __init__(self, service=None):
        # Allow injecting a service (handy for tests); otherwise build one.
        self.service = service or get_drive_service()

    # ------------------------------------------------------------------
    # Internal helper: common kwargs so Shared Drives "just work".
    # ------------------------------------------------------------------
    def _list_kwargs(self) -> dict:
        kwargs = {
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
            "fields": "files(id, name, mimeType, parents)",
            "pageSize": 100,
        }
        # If a specific Shared Drive is configured, scope the search to it.
        if settings.DRIVE_SHARED_DRIVE_ID:
            kwargs["corpora"] = "drive"
            kwargs["driveId"] = settings.DRIVE_SHARED_DRIVE_ID
        return kwargs

    @staticmethod
    def _escape(value: str) -> str:
        """Escape single quotes so names are safe inside a Drive query."""
        return value.replace("'", "\\'")

    # ------------------------------------------------------------------
    # Connectivity check — used by the Stage 1 test script.
    # ------------------------------------------------------------------
    def whoami(self) -> dict:
        """
        Return basic info about the authenticated account + storage quota.

        This is the cheapest possible call to confirm that credentials work
        and that we can reach the Drive API at all.
        """
        return (
            self.service.about()
            .get(fields="user(displayName, emailAddress), storageQuota")
            .execute()
        )

    # ------------------------------------------------------------------
    # Folder discovery (by name).
    # ------------------------------------------------------------------
    def find_folder(self, name: str, parent_id: str | None = None) -> dict | None:
        """
        Find a single folder by name, optionally within a given parent.

        Returns the first matching folder dict {id, name, ...} or None.
        """
        query = (
            f"name = '{self._escape(name)}' "
            f"and mimeType = '{MIME_FOLDER}' "
            f"and trashed = false"
        )
        if parent_id:
            query += f" and '{parent_id}' in parents"

        result = self.service.files().list(q=query, **self._list_kwargs()).execute()
        files = result.get("files", [])
        return files[0] if files else None

    def get_root_folder(self) -> dict:
        """
        Locate the top-level project folder (e.g. 'LOBO_AI_LEADS').

        Raises a clear error if it cannot be found — usually this means the
        folder was not SHARED with the service account's email address.
        """
        folder = self.find_folder(settings.DRIVE_ROOT_FOLDER_NAME)
        if not folder:
            raise RuntimeError(
                f"Root folder '{settings.DRIVE_ROOT_FOLDER_NAME}' not found. "
                "Make sure it exists in Drive and is shared with the service "
                "account email (see README, 'Share Google Drive folders')."
            )
        return folder

    def get_subfolder(self, subfolder_name: str) -> dict:
        """
        Find one of the standard subfolders inside the project root folder.

        Example: get_subfolder('01_RAW_LINKEDIN_EXPORTS')
        """
        root = self.get_root_folder()
        folder = self.find_folder(subfolder_name, parent_id=root["id"])
        if not folder:
            raise RuntimeError(
                f"Subfolder '{subfolder_name}' not found inside "
                f"'{settings.DRIVE_ROOT_FOLDER_NAME}'."
            )
        return folder

    def get_or_create_folder(self, name: str, parent_id: str) -> dict:
        """
        Find a subfolder by name inside `parent_id`, creating it if absent.

        Used for the audit-log folder, which isn't part of the pre-existing
        structure. Returns the folder dict {id, name}.
        """
        existing = self.find_folder(name, parent_id=parent_id)
        if existing:
            return existing

        metadata = {
            "name": name,
            "mimeType": MIME_FOLDER,
            "parents": [parent_id],
        }
        folder = (
            self.service.files()
            .create(body=metadata, fields="id, name", supportsAllDrives=True)
            .execute()
        )
        return folder

    def list_files(self, folder_id: str) -> list[dict]:
        """
        List non-folder files directly inside a folder.

        Used later by the folder watcher to detect new uploads.
        """
        query = (
            f"'{folder_id}' in parents "
            f"and mimeType != '{MIME_FOLDER}' "
            f"and trashed = false"
        )
        result = self.service.files().list(q=query, **self._list_kwargs()).execute()
        return result.get("files", [])
