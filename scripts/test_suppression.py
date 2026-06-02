"""
test_suppression.py
==================
Offline test for the do-not-contact suppression filter (no Drive needed).
Builds a small DataFrame mixing existing-customer companies (in various
real-world spellings) with genuine prospects, and checks that only the
prospects survive.

Run:
    python -m scripts.test_suppression
"""

import pandas as pd

from app.config.constants import LEAD_SCHEMA
from app.cleaning import suppression


def _row(**kw) -> dict:
    """Build a full schema row, defaulting unspecified fields to ''."""
    return {col: kw.get(col, "") for col in LEAD_SCHEMA}


# Compiled inline so the test doesn't depend on the shipped list file.
ENTRIES = suppression.compile_entries(
    ["PepsiCo", "Nestle", "Kerry", "Coors", "Vauxhall", "General Motors", "MSD"]
)

SAMPLE = pd.DataFrame([
    # Existing customers — must be SUPPRESSED, despite spelling variants:
    _row(full_name="A", company="PepsiCo"),
    _row(full_name="B", company="Nestle (Canada)"),                 # extra word
    _row(full_name="C", company="Kerry Foods"),                     # longer form
    _row(full_name="D", company="Molson Coors Beverage Company"),   # brand inside
    _row(full_name="E", company="Vauxhall Motors Ltd"),             # legal suffix
    _row(full_name="F", company="General Motors"),                  # two-word entry
    # Genuine prospects — must SURVIVE:
    _row(full_name="G", company="Mars"),                            # not on the list
    _row(full_name="H", company="Imerys"),
    _row(full_name="I", company="Merck Group"),                     # != "MSD"
    _row(full_name="J", company="Bradford Bakeries"),               # != "Ford"
])


def main() -> None:
    print("LOBO AI Leads — suppression (do-not-contact) test")
    print("=" * 55)

    kept, suppressed = suppression.suppress(SAMPLE, entries=ENTRIES)

    print(f"Kept: {len(kept)}   Suppressed: {len(suppressed)}")
    print("-" * 55)
    print("Suppressed:")
    print(suppressed[["company", "suppressed_reason"]].to_string(index=False))
    print("-" * 55)
    print("Kept:")
    print(kept[["company"]].to_string(index=False))
    print("=" * 55)

    kept_companies = set(kept["company"])
    assert kept_companies == {"Mars", "Imerys", "Merck Group", "Bradford Bakeries"}, \
        f"unexpected survivors: {kept_companies}"
    assert len(suppressed) == 6, f"expected 6 suppressed, got {len(suppressed)}"
    print("SUCCESS: existing-customer leads suppressed; prospects kept.")


if __name__ == "__main__":
    main()
