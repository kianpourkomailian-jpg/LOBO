"""
test_connection.py
==================
Stage 1 smoke test. Run this FIRST, before anything else.

It verifies, in order:
  1. Your credentials load correctly (auth works).
  2. We can reach the Drive API (prints the service account identity).
  3. The project root folder is visible to the service account.
  4. Each expected subfolder exists and is reachable.

Run from the project root:
    python -m scripts.test_connection
"""

from app.config import settings
from app.drive.drive_client import DriveClient


def main() -> None:
    print("LOBO AI Leads — Stage 1 connection test")
    print("=" * 50)

    # 1) Validate configuration up front (clear error if misconfigured).
    settings.validate()
    print("[OK] Configuration looks valid.")

    # 2) Authenticate + confirm API reachability.
    client = DriveClient()
    info = client.whoami()
    user = info.get("user", {})
    print(f"[OK] Authenticated as: {user.get('emailAddress', 'unknown')}")

    # 3) Find the top-level project folder.
    root = client.get_root_folder()
    print(f"[OK] Found root folder '{root['name']}' (id={root['id']})")

    # 4) Confirm each standard subfolder is present.
    subfolders = [
        settings.DRIVE_RAW_FOLDER,
        settings.DRIVE_CLEANED_FOLDER,
        settings.DRIVE_PROCESSED_FOLDER,
        settings.DRIVE_CALL_HISTORY_FOLDER,
        settings.DRIVE_DONOT_CONTACT_FOLDER,
    ]
    for name in subfolders:
        folder = client.get_subfolder(name)
        print(f"[OK] Subfolder '{name}' (id={folder['id']})")

    print("=" * 50)
    print("SUCCESS: Google Drive is connected and all folders are reachable.")


if __name__ == "__main__":
    main()
