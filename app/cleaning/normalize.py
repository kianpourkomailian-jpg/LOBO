"""
normalize.py
===========
Standardises the *values* inside a schema-shaped lead DataFrame.

Parsing (Stage 3) got the columns right; normalisation makes the contents
consistent so that dedupe and scoring behave predictably:

  * trim stray whitespace everywhere
  * Title-Case names and companies ("jane DOE" -> "Jane Doe")
  * lower-case + trim emails ("  Jane@ACME.com " -> "jane@acme.com")
  * tidy LinkedIn URLs (strip trailing slashes / query strings)
  * parse free-form connection dates into ISO format (YYYY-MM-DD)

Normalisation does NOT delete rows — that's validation's job. It only cleans
what's there, leaving blanks as blanks.
"""

import pandas as pd

from app.config.constants import LEAD_SCHEMA
from app.logs.logger import get_logger

log = get_logger(__name__)

# Columns that read best in Title Case.
_TITLE_CASE_COLS = ["full_name", "first_name", "last_name", "company", "role"]


def _clean_url(url: str) -> str:
    """Lower-case host, drop query string and trailing slash."""
    url = str(url).strip()
    if not url:
        return ""
    url = url.split("?", 1)[0]            # remove tracking query params
    return url.rstrip("/")


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a normalised copy of `df` (assumed to already follow LEAD_SCHEMA).
    """
    df = df.copy()

    # 1) Strip whitespace on every column (all values are strings).
    for col in LEAD_SCHEMA:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    # 2) Title-case names/companies/roles for consistent display + matching.
    for col in _TITLE_CASE_COLS:
        # Only re-case non-empty values; .title() on "" is harmless but cheap.
        df[col] = df[col].apply(lambda v: v.title() if v else v)

    # 3) Emails: lower-case + trimmed (already stripped above).
    df["email"] = df["email"].str.lower()

    # 4) LinkedIn URLs: tidy up.
    df["linkedin_profile"] = df["linkedin_profile"].apply(_clean_url)

    # 5) Connection date -> ISO (YYYY-MM-DD). Unparseable -> left blank.
    parsed = pd.to_datetime(df["connection_date"], errors="coerce")
    df["connection_date"] = parsed.dt.strftime("%Y-%m-%d").fillna("")

    log.info("Normalised %d rows", len(df))
    return df
