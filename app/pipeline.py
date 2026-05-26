"""
pipeline.py
==========
The end-to-end processing pipeline for a single raw export file.

This is the conductor that calls every stage in order:

  download -> parse -> normalize -> validate -> dedupe -> score
           -> upload cleaned -> archive raw -> audit log

It exposes one method, `process_file(file)`, which is exactly the handler the
FolderWatcher (Stage 2) dispatches new files to. Wiring it up here keeps
main.py tiny and keeps each stage independently testable.

Failure policy
--------------
If parsing fails, we log an audit record and LEAVE the raw file where it is
(so it can be inspected/retried) rather than archiving a file we couldn't
process. Any other unexpected error is logged and re-raised to the watcher,
which already isolates handler failures so the loop keeps running.
"""

from app.config import settings
from app.drive.file_manager import FileManager
from app.ingestion import linkedin_parser, dump_parser
from app.cleaning import normalize, validators, dedupe
from app.scoring import lead_scoring, priority_engine
from app.exports.upload_cleaned import upload_cleaned
from app.logs.audit import AuditLogger
from app.logs.logger import get_logger

log = get_logger(__name__)


def _parse_by_extension(name: str, buffer):
    """Pick the right parser based on file extension.

    .txt/.md  -> the free-text dump extractor (Claude-backed).
    others    -> the LinkedIn parser (handles ZIP/CSV/XLSX itself).
    """
    if name.lower().endswith((".txt", ".md")):
        return dump_parser.parse_dump(name, buffer)
    return linkedin_parser.parse(name, buffer)


class Pipeline:
    """Runs the full clean-and-score pipeline for one Drive file."""

    def __init__(self, file_manager: FileManager | None = None):
        self.fm = file_manager or FileManager()
        self.audit = AuditLogger(self.fm)

    def process_file(self, file: dict) -> None:
        """Process one raw export file dict ({id, name, ...})."""
        name = file["name"]
        file_id = file["id"]
        log.info("Pipeline START: %s", name)

        # 1) Download the raw bytes into memory.
        buffer = self.fm.download_to_memory(file_id)

        # 2) Parse into the standardized schema. On failure: audit + bail.
        try:
            parsed = _parse_by_extension(name, buffer)
        except Exception as exc:  # noqa: BLE001
            log.exception("Parsing failed for %s", name)
            self.audit.log_run(name, counts={"parsed": 0},
                               parse_error=str(exc))
            return  # leave the raw file in place for inspection

        # 3-6) Clean -> validate -> dedupe -> score -> prioritise.
        normalized = normalize.normalize(parsed)
        valid, invalid = validators.validate(normalized)
        unique, duplicates = dedupe.dedupe(valid)
        scored = lead_scoring.score_leads(unique)
        final = priority_engine.assign_priority(scored)

        # 7) Upload the cleaned, scored leads to 02_CLEANED_LEADS.
        upload_cleaned(final, source_filename=name, file_manager=self.fm)

        # 8) Archive the raw file into 03_PROCESSED_LEADS.
        processed_folder = self.fm.client.get_subfolder(
            settings.DRIVE_PROCESSED_FOLDER
        )
        self.fm.move_file(file_id, processed_folder["id"])

        # 9) Write the audit trail (summary + duplicate/invalid CSVs).
        counts = {
            "parsed": len(parsed),
            "valid": len(valid),
            "invalid": len(invalid),
            "duplicates": len(duplicates),
            "exported": len(final),
        }
        self.audit.log_run(name, counts=counts,
                          duplicates=duplicates, invalid=invalid)

        log.info("Pipeline DONE: %s -> %s", name, counts)
