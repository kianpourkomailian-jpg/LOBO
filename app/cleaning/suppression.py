"""
suppression.py
=============
Filters out leads that work for companies we ALREADY do business with
(existing customers, or accounts owned by another salesperson). These must
never reach the cleaned output or the call lists, so we drop them during
cleaning — the same way validators/dedupe drop rows: the removed rows are
returned separately (with a reason) so Stage 6 can log exactly what was
suppressed and why.

The suppression list lives in a plain-text file (one company per line, '#'
comments allowed) so it can be edited without touching code — add a line
each time you win an account and the next import is filtered automatically.
See app/config/do_not_contact.txt.

Matching is token-based and tolerant of legal suffixes and longer variants:

    an entry of "Kerry" matches "Kerry", "Kerry Foods", "Kerry Group Plc"
    an entry of "Coors" matches "Molson Coors Beverage Company"

Concretely, a company matches an entry when EVERY significant word of the
entry is present in the company name, after lower-casing, stripping accents
and punctuation, and ignoring generic corporate words (Ltd, Plc, Inc,
Group, Company, ...). Using whole-word tokens keeps it precise: "Ford" does
not match "Bradford", and "Coors" does not match anything but Coors.
"""

import re
import unicodedata
from functools import lru_cache
from typing import Iterable

import pandas as pd

from app.config import settings
from app.logs.logger import get_logger

log = get_logger(__name__)

# Generic corporate words ignored on BOTH sides when matching, so that
# "Vauxhall Motors Ltd" and "Vauxhall" reduce to the same significant tokens.
_GENERIC_TOKENS = {
    "ltd", "limited", "plc", "inc", "incorporated", "llc", "llp", "lp",
    "co", "company", "corp", "corporation", "group", "holdings",
    "gmbh", "nv", "sa", "ag", "srl", "spa", "bv", "ab", "oyj", "the",
}


@lru_cache(maxsize=8192)
def _tokens(name: str) -> frozenset:
    """Reduce a company name to its set of significant lower-case tokens."""
    # Strip accents: "Nestlé" -> "Nestle", "Müller" -> "Muller".
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    # Drop apostrophes/periods so "Kellogg's" -> "kelloggs", "N.V." -> "nv".
    ascii_name = ascii_name.lower().replace("'", "").replace(".", "")
    # Every remaining non-alphanumeric run is a separator.
    words = re.split(r"[^a-z0-9]+", ascii_name)
    return frozenset(w for w in words if w and w not in _GENERIC_TOKENS)


def compile_entries(names: Iterable[str]) -> list[frozenset]:
    """Turn raw company names into matchable token-sets (dropping empties)."""
    entries: list[frozenset] = []
    for name in names:
        toks = _tokens(name)
        if toks:  # ignore entries that reduce to nothing (e.g. "The Co Ltd")
            entries.append(toks)
    return entries


def load_suppression_list(path: str | None = None) -> list[frozenset]:
    """
    Load the do-not-contact file into a list of token-sets (one per entry).

    Blank lines and '#' comments (whole-line or inline) are ignored. A missing
    file is NOT an error — it just means "suppress nothing" (logged as a
    warning) so the pipeline keeps running if the list hasn't been created yet.
    """
    path = path or settings.DO_NOT_CONTACT_FILE
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw_lines = fh.readlines()
    except FileNotFoundError:
        log.warning("Suppression list not found at '%s' — suppressing nothing.", path)
        return []

    names = [line.split("#", 1)[0].strip() for line in raw_lines]
    entries = compile_entries(n for n in names if n)
    log.info("Loaded %d suppression entries from %s", len(entries), path)
    return entries


def _matched_entry(company: str, entries: list[frozenset]) -> frozenset | None:
    """Return the first entry whose tokens are all present in `company`."""
    company_tokens = _tokens(company)
    if not company_tokens:
        return None
    for entry in entries:
        if entry <= company_tokens:  # every word of the entry is in the company
            return entry
    return None


def suppress(
    df: pd.DataFrame,
    entries: list[frozenset] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split `df` into (kept_df, suppressed_df).

    `suppressed_df` carries an extra `suppressed_reason` column naming the
    matched company, e.g. "do_not_contact:pepsico" or
    "do_not_contact:general motors".

    Passing `entries` is mainly for testing; in production it is loaded from
    the configured do-not-contact file on first use.
    """
    if entries is None:
        entries = load_suppression_list()

    empty = df.iloc[0:0].copy()
    if df.empty or not entries or "company" not in df.columns:
        return df.copy(), empty

    reasons = [
        ("do_not_contact:" + " ".join(sorted(match)))
        if (match := _matched_entry(str(company or ""), entries))
        else None
        for company in df["company"]
    ]
    reason_series = pd.Series(reasons, index=df.index)
    is_suppressed = reason_series.notna()

    kept_df = df[~is_suppressed].copy()
    suppressed_df = df[is_suppressed].copy()
    if not suppressed_df.empty:
        suppressed_df["suppressed_reason"] = reason_series[is_suppressed].values

    log.info("Suppression: %d kept, %d suppressed", len(kept_df), len(suppressed_df))
    return kept_df, suppressed_df
