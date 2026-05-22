"""
dedupe.py
========
Removes duplicate leads, in two passes:

  1. EXACT pass — collapse rows that share a strong identity key:
       * the same (non-empty) email, or
       * the same (non-empty) linkedin_profile.
     These are unambiguous duplicates; we keep the first occurrence.

  2. FUZZY pass — catch near-duplicates that exact keys miss, e.g.
       "Jane Doe / Acme Mfg" vs "Jane Doe / Acme Manufacturing".
     We compare a "name + company" signature using rapidfuzz; rows scoring
     above a threshold against an already-kept row are treated as duplicates.

Like validation, we don't just discard duplicates — we return them separately
(with a reason) so Stage 6 can log what was skipped.
"""

import pandas as pd
from rapidfuzz import fuzz

from app.logs.logger import get_logger

log = get_logger(__name__)

# Two-factor fuzzy match: a row is a duplicate only if BOTH the name is very
# similar AND the company is similar. This catches abbreviations like
# "Acme Mfg" vs "Acme Manufacturing" without merging two different people who
# happen to work at the same company.
NAME_THRESHOLD = 90      # token_sort_ratio on full_name
COMPANY_THRESHOLD = 80   # partial_ratio on company (tolerant of abbreviations)


def _name_company(row: pd.Series) -> tuple[str, str]:
    """Return (name, company) lower-cased for fuzzy comparison."""
    return (
        (row.get("full_name") or "").strip().lower(),
        (row.get("company") or "").strip().lower(),
    )


def dedupe(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Return (unique_df, duplicates_df).

    `duplicates_df` carries an extra `duplicate_reason` column
    ("duplicate_email", "duplicate_linkedin", or "fuzzy_duplicate").
    """
    if df.empty:
        return df.copy(), df.copy()

    df = df.reset_index(drop=True)
    dropped_idx: dict[int, str] = {}  # row index -> reason

    # --- Pass 1: exact email / linkedin duplicates -------------------
    for key, reason in (("email", "duplicate_email"),
                         ("linkedin_profile", "duplicate_linkedin")):
        seen: set[str] = set()
        for idx, value in df[key].items():
            value = (value or "").strip().lower()
            if not value:
                continue  # blanks are never "duplicates" of each other
            if value in seen:
                dropped_idx.setdefault(idx, reason)
            else:
                seen.add(value)

    # --- Pass 2: fuzzy name+company among the survivors --------------
    kept: list[tuple[str, str]] = []  # (name, company) of rows we keep
    for idx, row in df.iterrows():
        if idx in dropped_idx:
            continue
        name, company = _name_company(row)
        if not name and not company:
            continue
        # A duplicate needs BOTH a strong name match and a company match.
        is_dup = any(
            fuzz.token_sort_ratio(name, k_name) >= NAME_THRESHOLD
            and company and k_company
            and fuzz.partial_ratio(company, k_company) >= COMPANY_THRESHOLD
            for k_name, k_company in kept
        )
        if is_dup:
            dropped_idx[idx] = "fuzzy_duplicate"
        else:
            kept.append((name, company))

    # --- Assemble outputs --------------------------------------------
    dup_indices = list(dropped_idx.keys())
    unique_df = df.drop(index=dup_indices).reset_index(drop=True)
    duplicates_df = df.loc[dup_indices].copy()
    if not duplicates_df.empty:
        duplicates_df["duplicate_reason"] = [dropped_idx[i] for i in dup_indices]

    log.info("Dedupe: %d unique, %d duplicates", len(unique_df), len(duplicates_df))
    return unique_df, duplicates_df
