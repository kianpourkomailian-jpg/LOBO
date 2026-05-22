"""
linkedin_parser.py
==================
Turns a raw LinkedIn export (CSV / XLSX / ZIP-of-those) into a DataFrame that
follows our standardized LEAD_SCHEMA.

Responsibilities
----------------
1. Dispatch by file type (zip -> extract members; csv/xlsx -> read directly).
2. For CSVs, skip LinkedIn's preamble and locate the real header row.
3. Map LinkedIn's column names onto our schema (case/whitespace tolerant).
4. Guarantee every output frame has ALL schema columns, in order.

What it does NOT do
-------------------
No cleaning, validation, dedupe, or scoring — those are separate stages. This
keeps parsing a pure "shape the data" step. `lead_score`/`lead_priority` are
created empty here and filled in Stage 5.
"""

import io

import pandas as pd

from app.config.constants import (
    LEAD_SCHEMA,
    LINKEDIN_COLUMN_MAP,
    LINKEDIN_HEADER_MARKERS,
)
from app.ingestion import csv_parser
from app.ingestion.zip_handler import extract_data_files
from app.logs.logger import get_logger

log = get_logger(__name__)


def _read_member(name: str, buffer: io.BytesIO) -> pd.DataFrame:
    """Read a single CSV/XLSX member into a raw DataFrame."""
    lower = name.lower()
    if lower.endswith(".xlsx"):
        return csv_parser.read_xlsx(buffer)
    # CSV: find and skip any preamble above the real header.
    skip = csv_parser.detect_header_row(buffer, LINKEDIN_HEADER_MARKERS)
    return csv_parser.read_csv(buffer, skiprows=skip)


def _map_to_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename recognised LinkedIn columns to schema names and fill the rest.

    Unrecognised columns are dropped. Missing schema columns are added empty.
    The resulting frame has exactly LEAD_SCHEMA columns, in order.
    """
    # Normalise incoming headers: strip + lowercase for matching.
    rename = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in LINKEDIN_COLUMN_MAP:
            rename[col] = LINKEDIN_COLUMN_MAP[key]
    mapped = df.rename(columns=rename)

    # Keep only columns that are part of our schema.
    keep = [c for c in mapped.columns if c in LEAD_SCHEMA]
    mapped = mapped[keep].copy()

    # Build full_name from first/last when not already present.
    if "full_name" not in mapped.columns:
        first = mapped.get("first_name", pd.Series([""] * len(mapped)))
        last = mapped.get("last_name", pd.Series([""] * len(mapped)))
        mapped["full_name"] = (
            first.fillna("").astype(str).str.strip()
            + " "
            + last.fillna("").astype(str).str.strip()
        ).str.strip()

    # Add any missing schema columns as empty strings, then order them.
    for col in LEAD_SCHEMA:
        if col not in mapped.columns:
            mapped[col] = ""
    return mapped[LEAD_SCHEMA]


def parse(filename: str, buffer: io.BytesIO) -> pd.DataFrame:
    """
    Parse a downloaded raw export into a schema-shaped DataFrame.

    Handles ZIP (concatenating all data members), CSV, and XLSX. Raises
    ValueError for unsupported types so the caller can log/skip cleanly.
    """
    lower = filename.lower()

    if lower.endswith(".zip"):
        frames = []
        for member_name, member_buf in extract_data_files(buffer):
            try:
                raw = _read_member(member_name, member_buf)
                frames.append(_map_to_schema(raw))
            except Exception:  # noqa: BLE001 — skip a bad member, keep the rest
                log.exception("Failed to parse ZIP member '%s'", member_name)
        if not frames:
            return pd.DataFrame(columns=LEAD_SCHEMA)
        return pd.concat(frames, ignore_index=True)

    if lower.endswith((".csv", ".xlsx")):
        raw = _read_member(filename, buffer)
        return _map_to_schema(raw)

    raise ValueError(f"Unsupported file type: {filename}")
