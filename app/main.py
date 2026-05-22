"""
main.py
=======
Application entry point.

Stage 1: this only proves the app boots and Drive is reachable. The full
pipeline (watch -> ingest -> clean -> dedupe -> score -> export -> archive)
is wired up in later stages.

Run:
    python -m app.main
"""

from app.drive.drive_client import DriveClient


def main() -> None:
    client = DriveClient()
    info = client.whoami()
    print("LOBO AI Leads is running.")
    print(f"Connected to Drive as: {info.get('user', {}).get('emailAddress')}")
    # Later stages will start the APScheduler folder watcher here.


if __name__ == "__main__":
    main()
