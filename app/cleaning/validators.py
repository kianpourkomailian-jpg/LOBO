"""
validators.py
============
Splits a normalised lead DataFrame into VALID and INVALID rows.

We don't silently drop bad data — we separate it and tag *why* it was
rejected, so Stage 6 can log invalid records for review. A row is invalid if:

  * it is effectively blank (no name AND no company AND no email), or
  * it has an email that isn't a syntactically valid address, or
  * it has a linkedin_profile that isn't a plausible LinkedIn URL.

Note on emails: a BLANK email is allowed (many valid LinkedIn connections
have no email). Only a *malformed, non-empty* email is rejected. Same logic
for LinkedIn URLs.
"""

import re

import pandas as pd

from app.logs.logger import get_logger

log = get_logger(__name__)

# Pragmatic email check: something@something.tld (not full RFC 5322).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Accept linkedin.com profile URLs (with or without scheme/subdomain).
_LINKEDIN_RE = re.compile(r"^(https?://)?([a-z0-9-]+\.)?linkedin\.com/.+", re.I)


def _row_reason(row: pd.Series) -> str | None:
    """Return a rejection reason for a row, or None if it's valid."""
    name = (row.get("full_name") or "").strip()
    company = (row.get("company") or "").strip()
    email = (row.get("email") or "").strip()
    url = (row.get("linkedin_profile") or "").strip()

    # Blank row: no useful identifying info at all.
    if not name and not company and not email:
        return "blank_row"

    # Non-empty but malformed email.
    if email and not _EMAIL_RE.match(email):
        return "invalid_email"

    # Non-empty but implausible LinkedIn URL.
    if url and not _LINKEDIN_RE.match(url):
        return "invalid_linkedin_url"

    return None


def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Return (valid_df, invalid_df).

    `invalid_df` is a copy of the rejected rows with an extra
    `invalid_reason` column explaining why each was dropped.
    """
    if df.empty:
        return df.copy(), df.copy()

    reasons = df.apply(_row_reason, axis=1)
    is_valid = reasons.isna()

    valid_df = df[is_valid].copy()
    invalid_df = df[~is_valid].copy()
    invalid_df["invalid_reason"] = reasons[~is_valid].values

    log.info("Validation: %d valid, %d invalid", len(valid_df), len(invalid_df))
    return valid_df, invalid_df
