"""
file_manager.py
===============
Concrete file operations on Google Drive: download, upload, and move.

This sits on top of `DriveClient` (which handles auth + folder discovery)
and provides the verbs the ingestion pipeline needs:

  * download_to_memory  — pull a raw export into RAM (no local disk needed)
  * upload_bytes        — push a cleaned file (e.g. CSV bytes) into a folder
  * move_file           — re-parent a file (raw -> processed) after handling

Why "in memory"?
----------------
A hard project rule is: NO reliance on local/persistent storage. So instead
of saving downloads to disk, we stream them into a `BytesIO` buffer that the
parsers read directly. This keeps the app stateless and cloud-friendly.
"""

import io

from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from app.drive.drive_client import DriveClient


class FileManager:
    """Download / upload / move helpers, all RAM-based (no local files)."""

    def __init__(self, client: DriveClient | None = None):
        self.client = client or DriveClient()
        self.service = self.client.service

    # ------------------------------------------------------------------
    # Download a file's bytes into memory.
    # ------------------------------------------------------------------
    def download_to_memory(self, file_id: str) -> io.BytesIO:
        """
        Download the file with the given id into a BytesIO buffer.

        Returns a buffer rewound to position 0, ready for a parser to read.
        """
        request = self.service.files().get_media(
            fileId=file_id, supportsAllDrives=True
        )
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            # Each call fetches the next chunk; status carries progress.
            _, done = downloader.next_chunk()

        buffer.seek(0)  # rewind so callers can read from the start
        return buffer

    # ------------------------------------------------------------------
    # Upload bytes as a new file into a folder.
    # ------------------------------------------------------------------
    def upload_bytes(
        self,
        folder_id: str,
        filename: str,
        data: bytes,
        mime_type: str = "text/csv",
    ) -> dict:
        """
        Create a new file in `folder_id` from raw bytes.

        Used to write cleaned CSV output into 02_CLEANED_LEADS.
        Returns the created file's metadata {id, name}.
        """
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=True)
        metadata = {"name": filename, "parents": [folder_id]}
        return (
            self.service.files()
            .create(
                body=metadata,
                media_body=media,
                fields="id, name",
                supportsAllDrives=True,
            )
            .execute()
        )

    # ------------------------------------------------------------------
    # Move a file from one folder to another (change its parent).
    # ------------------------------------------------------------------
    def move_file(self, file_id: str, new_parent_id: str) -> dict:
        """
        Move a file by replacing its parent folder.

        Drive treats folder membership as "parents", so moving = remove the
        old parent(s) and add the new one in a single update call. Used to
        archive a processed raw export into 03_PROCESSED_LEADS.
        """
        # Look up current parents so we can detach them.
        current = (
            self.service.files()
            .get(fileId=file_id, fields="parents", supportsAllDrives=True)
            .execute()
        )
        previous_parents = ",".join(current.get("parents", []))

        return (
            self.service.files()
            .update(
                fileId=file_id,
                addParents=new_parent_id,
                removeParents=previous_parents,
                fields="id, name, parents",
                supportsAllDrives=True,
            )
            .execute()
        )
