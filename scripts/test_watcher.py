"""
test_watcher.py
==============
Stage 2 test. Runs a SINGLE scan of the raw-exports folder and reports which
files would be dispatched to the ingestion pipeline.

Unlike the live watcher, this does not loop — it scans once and exits, so it's
safe to run by hand.

Run from the project root:
    python -m scripts.test_watcher
"""

from app.drive.folder_watcher import FolderWatcher


def main() -> None:
    print("LOBO AI Leads — Stage 2 watcher test")
    print("=" * 50)

    detected: list[str] = []

    def handler(file: dict) -> None:
        # Just record the name; no parsing/moving in this test.
        detected.append(file.get("name", "<unnamed>"))

    watcher = FolderWatcher(handler=handler)
    count = watcher.check_once()

    print(f"Dispatched {count} new supported file(s):")
    for name in detected:
        print(f"  - {name}")
    print("=" * 50)
    print("Done. (Upload a CSV/XLSX/ZIP to the raw folder and re-run to test.)")


if __name__ == "__main__":
    main()
