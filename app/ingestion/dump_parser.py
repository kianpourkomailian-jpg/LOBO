"""
dump_parser.py
=============
STUB for the 07_RAW_DUMP folder.

Purpose
-------
Users will drop ad-hoc, free-text leads into 07_RAW_DUMP (e.g. a .txt with
"Dave Otway, Crepe Cuisine, http://www.crepecuisine.com/"). When implemented
this module turns that free text into a LEAD_SCHEMA-shaped DataFrame, which
then flows through the normal cleaning / scoring / export pipeline.

For now extraction is intentionally NOT implemented — files park in the dump
folder until this is wired up. The function still returns a valid (empty)
schema-shaped DataFrame so callers can rely on its shape.

When implementing later
-----------------------
1. Decide on the extraction strategy (regex/heuristics vs. an LLM call).
2. Fill `parse_dump` so it returns a DataFrame with LEAD_SCHEMA columns.
3. In `pipeline.Pipeline.process_file`, dispatch on file extension:
       if name.lower().endswith((".txt", ".md")):
           parsed = dump_parser.parse_dump(name, buffer)
       else:
           parsed = linkedin_parser.parse(name, buffer)
4. Add the dump folder to the watcher (FolderWatcher currently watches only
   DRIVE_RAW_FOLDER; either point it at multiple folders or run two watchers).
"""

import io

import pandas as pd

from app.config.constants import LEAD_SCHEMA
from app.logs.logger import get_logger

log = get_logger(__name__)


def parse_dump(filename: str, buffer: io.BytesIO) -> pd.DataFrame:
    """
    Extract leads from a free-text dump file.

    Currently a no-op: logs a notice and returns an empty schema-shaped
    DataFrame. Callers can rely on the column shape even though no rows are
    produced yet.
    """
    log.info(
        "[dump_parser] Extraction not implemented yet — '%s' will be left "
        "for manual processing.",
        filename,
    )
    return pd.DataFrame(columns=LEAD_SCHEMA)
