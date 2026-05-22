"""
test_pipeline.py
===============
Stage 6 test (fully offline). Runs the COMPLETE pipeline against an in-memory
fake of Google Drive, so no credentials or network are needed.

We fake just enough of DriveClient/FileManager for Pipeline to run:
  * a raw "file" whose bytes are a realistic LinkedIn CSV,
  * upload/move that record into in-memory stores we can inspect.

Run:
    python -m scripts.test_pipeline
"""

import io

from app.pipeline import Pipeline

SAMPLE_CSV = (
    "Notes:\n"
    '"preamble line"\n'
    "\n"
    "First Name,Last Name,URL,Email Address,Company,Position,Connected On\n"
    "Jane,Doe,https://linkedin.com/in/janedoe,jane@acme.com,Acme Manufacturing,"
    "Maintenance Manager,01 Jan 2024\n"
    # Exact email duplicate of Jane.
    "J,Doe,https://linkedin.com/in/janedoe2,jane@acme.com,Acme,Engineer,02 Jan 2024\n"
    "John,Smith,https://linkedin.com/in/johnsmith,john@globex.com,Globex Logistics,"
    "Director of Operations,15 Feb 2024\n"
    # Invalid email row.
    "Bad,Email,,not-an-email,Nowhere,Clerk,03 Mar 2024\n"
)


class FakeClient:
    """Stand-in for DriveClient with the methods Pipeline/exports call."""

    FOLDERS = {
        "01_RAW_LINKEDIN_EXPORTS": "raw_id",
        "02_CLEANED_LEADS": "cleaned_id",
        "03_PROCESSED_LEADS": "processed_id",
    }

    def get_subfolder(self, name):
        return {"id": self.FOLDERS[name], "name": name}

    def get_root_folder(self):
        return {"id": "root_id", "name": "LOBO_AI_LEADS"}

    def get_or_create_folder(self, name, parent_id):
        return {"id": "logs_id", "name": name}


class FakeFileManager:
    """In-memory FileManager: records uploads and moves for inspection."""

    def __init__(self):
        self.client = FakeClient()
        self.uploads = []  # (folder_id, filename, bytes)
        self.moves = []    # (file_id, new_parent_id)

    def download_to_memory(self, file_id):
        return io.BytesIO(SAMPLE_CSV.encode("utf-8"))

    def upload_bytes(self, folder_id, filename, data, mime_type="text/csv"):
        self.uploads.append((folder_id, filename, data))
        return {"id": f"up_{len(self.uploads)}", "name": filename}

    def move_file(self, file_id, new_parent_id):
        self.moves.append((file_id, new_parent_id))
        return {"id": file_id, "parents": [new_parent_id]}


def main() -> None:
    print("LOBO AI Leads — Stage 6 full-pipeline test")
    print("=" * 55)

    fm = FakeFileManager()
    pipeline = Pipeline(file_manager=fm)
    pipeline.process_file({"id": "file123", "name": "Connections.csv"})

    # Inspect what the pipeline produced.
    cleaned = [u for u in fm.uploads if u[1].startswith("cleaned_")]
    logs = [u for u in fm.uploads if "logs_id" == u[0]]

    print(f"Cleaned files uploaded: {len(cleaned)}")
    for _, name, data in cleaned:
        print(f"  -> {name}")
        print(data.decode("utf-8"))

    print(f"Audit artifacts uploaded: {len(logs)}")
    for _, name, _ in logs:
        print(f"  -> {name}")

    print(f"Raw file moved: {fm.moves}")
    print("=" * 55)

    assert cleaned, "no cleaned file uploaded"
    assert fm.moves == [("file123", "processed_id")], "raw not archived correctly"
    assert any(n.endswith("_summary.json") for _, n, _ in logs), "no audit summary"
    print("SUCCESS: full pipeline ran end to end (offline).")


if __name__ == "__main__":
    main()
