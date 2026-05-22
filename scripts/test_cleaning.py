"""
test_cleaning.py
===============
Stage 4 test (offline, no Drive). Feeds a messy DataFrame through
normalize -> validate -> dedupe and prints what each step kept/dropped.

Run:
    python -m scripts.test_cleaning
"""

import pandas as pd

from app.config.constants import LEAD_SCHEMA
from app.cleaning import normalize, validators, dedupe


def _row(**kw) -> dict:
    """Build a full schema row, defaulting unspecified fields to ''."""
    return {col: kw.get(col, "") for col in LEAD_SCHEMA}


SAMPLE = pd.DataFrame([
    _row(full_name="jane DOE", first_name="jane", last_name="doe",
         company="acme mfg", role="maintenance manager",
         email="  Jane@ACME.com ", linkedin_profile="https://linkedin.com/in/jane/",
         connection_date="01 Jan 2024"),
    # Exact email duplicate of Jane.
    _row(full_name="J Doe", company="Acme", email="jane@acme.com",
         linkedin_profile="https://linkedin.com/in/jane2"),
    # Fuzzy duplicate: same person, company spelled out.
    _row(full_name="Jane Doe", company="Acme Manufacturing",
         linkedin_profile="https://linkedin.com/in/jane3"),
    # Valid, distinct lead.
    _row(full_name="John Smith", company="Globex", role="operations director",
         email="john@globex.com", connection_date="15 Feb 2024"),
    # Invalid email.
    _row(full_name="Bad Email", company="Nowhere", email="not-an-email"),
    # Blank row.
    _row(),
    # Invalid LinkedIn URL.
    _row(full_name="Bad URL", company="Somewhere",
         linkedin_profile="http://facebook.com/someone"),
])


def main() -> None:
    print("LOBO AI Leads — Stage 4 cleaning test")
    print("=" * 50)

    norm = normalize.normalize(SAMPLE)
    print("After normalize (email/url/date/case):")
    print(norm[["full_name", "email", "linkedin_profile", "connection_date"]]
          .to_string(index=False))
    print("-" * 50)

    valid, invalid = validators.validate(norm)
    print(f"Valid: {len(valid)}  Invalid: {len(invalid)}")
    if not invalid.empty:
        print(invalid[["full_name", "invalid_reason"]].to_string(index=False))
    print("-" * 50)

    unique, dups = dedupe.dedupe(valid)
    print(f"Unique: {len(unique)}  Duplicates: {len(dups)}")
    if not dups.empty:
        print(dups[["full_name", "duplicate_reason"]].to_string(index=False))
    print("-" * 50)
    print("Final unique leads:")
    print(unique[["full_name", "company", "email"]].to_string(index=False))
    print("=" * 50)
    print("SUCCESS: cleaning pipeline ran end to end.")


if __name__ == "__main__":
    main()
