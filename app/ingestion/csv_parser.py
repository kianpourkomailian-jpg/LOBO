"""
csv_parser.py
============
Low-level readers that turn in-memory CSV/XLSX bytes into pandas DataFrames.

This module is format-aware but NOT LinkedIn-aware: it just gets bytes into a
DataFrame as safely as possible. The LinkedIn-specific column mapping lives in
linkedin_parser.py, which builds on these helpers.
"""

import io

import pandas as pd

from app.logs.logger import get_logger

log = get_logger(__name__)


def detect_header_row(buffer: io.BytesIO, markers: set[str]) -> int:
    """
    Find the 0-based index of the header line in a CSV that may have preamble.

    LinkedIn's Connections.csv often starts with a few "Notes:" lines before
    the real header. We scan the first ~15 lines and return the index of the
    first line that contains several of the expected column markers.

    Returns 0 if no obvious header is found (i.e. assume row 0 is the header).
    """
    buffer.seek(0)
    text = buffer.read().decode("utf-8-sig", errors="replace")
    buffer.seek(0)

    for i, line in enumerate(text.splitlines()[:15]):
        cells = {c.strip().strip('"').lower() for c in line.split(",")}
        # Require at least 2 markers so a stray word doesn't false-match.
        if len(cells & markers) >= 2:
            return i
    return 0


def read_csv(buffer: io.BytesIO, skiprows: int = 0) -> pd.DataFrame:
    """
    Read CSV bytes into a DataFrame.

    `skiprows` drops preamble lines above the header. All columns are read as
    strings (dtype=str) so we never lose leading zeros or mangle phone-like
    values; cleaning/typing happens in later stages.
    """
    buffer.seek(0)
    df = pd.read_csv(
        buffer,
        skiprows=skiprows,
        dtype=str,
        encoding="utf-8-sig",       # tolerate a UTF-8 BOM
        keep_default_na=False,      # keep empty strings as "" not NaN
        on_bad_lines="skip",        # skip malformed rows rather than crash
    )
    log.info("CSV parsed: %d rows, %d cols", len(df), len(df.columns))
    return df


def read_xlsx(buffer: io.BytesIO) -> pd.DataFrame:
    """Read XLSX bytes (first sheet) into a DataFrame, all values as strings."""
    buffer.seek(0)
    df = pd.read_excel(buffer, dtype=str, engine="openpyxl")
    df = df.fillna("")  # normalise blanks to empty strings
    log.info("XLSX parsed: %d rows, %d cols", len(df), len(df.columns))
    return df
