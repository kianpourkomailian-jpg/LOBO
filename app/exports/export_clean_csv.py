"""
export_clean_csv.py
==================
Serialises a cleaned, scored lead DataFrame into CSV bytes (in memory).

Why bytes (not a file)?
-----------------------
Same no-local-storage rule as everywhere else: we produce the CSV content as
bytes and hand it straight to the uploader, which streams it to Google Drive.
Nothing touches the local disk.
"""

import pandas as pd

from app.config.constants import LEAD_SCHEMA


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """
    Return the DataFrame as UTF-8 CSV bytes, with columns forced to the
    canonical LEAD_SCHEMA order (and any missing column added empty).
    """
    out = df.copy()
    for col in LEAD_SCHEMA:
        if col not in out.columns:
            out[col] = ""
    out = out[LEAD_SCHEMA]
    # encoding handled by returning str.encode so we get raw bytes for upload.
    return out.to_csv(index=False).encode("utf-8")
