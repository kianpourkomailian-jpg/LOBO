"""
zip_handler.py
=============
Extracts the useful data files out of a LinkedIn export ZIP — in memory.

LinkedIn's "Download your data" gives a ZIP that contains several CSVs
(Connections.csv, messages.csv, etc.). We only care about the tabular data
files (CSV/XLSX), and we never write them to disk: each member is returned as
an in-memory buffer so the rest of the pipeline stays stateless.
"""

import io
import zipfile

from app.logs.logger import get_logger

log = get_logger(__name__)

# Members we care about inside the ZIP.
_WANTED_SUFFIXES = (".csv", ".xlsx")


def extract_data_files(zip_bytes: io.BytesIO) -> list[tuple[str, io.BytesIO]]:
    """
    Return [(member_name, buffer), ...] for each CSV/XLSX inside the ZIP.

    `zip_bytes` is a BytesIO of the whole ZIP (e.g. from FileManager
    .download_to_memory). Directory entries and non-data files are skipped.
    """
    results: list[tuple[str, io.BytesIO]] = []

    with zipfile.ZipFile(zip_bytes) as archive:
        for info in archive.infolist():
            name = info.filename
            # Skip folders and macOS resource-fork junk (__MACOSX/...).
            if info.is_dir() or name.startswith("__MACOSX"):
                continue
            if not name.lower().endswith(_WANTED_SUFFIXES):
                log.info("ZIP: skipping non-data member '%s'", name)
                continue

            # Read the member's bytes into its own buffer.
            buffer = io.BytesIO(archive.read(name))
            buffer.seek(0)
            results.append((name, buffer))
            log.info("ZIP: extracted '%s'", name)

    if not results:
        log.warning("ZIP contained no CSV/XLSX files.")
    return results
