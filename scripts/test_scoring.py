"""
test_scoring.py
==============
Stage 5 test (offline). Scores a small set of leads with varied roles and
companies, then assigns priority buckets, and prints the result.

Run:
    python -m scripts.test_scoring
"""

import pandas as pd

from app.config.constants import LEAD_SCHEMA
from app.scoring import lead_scoring, priority_engine


def _row(**kw) -> dict:
    return {col: kw.get(col, "") for col in LEAD_SCHEMA}


SAMPLE = pd.DataFrame([
    # High-value role + manufacturing industry + multiple keywords.
    _row(full_name="Jane Doe", role="Maintenance Manager", company="Acme Manufacturing"),
    # Director of operations in logistics.
    _row(full_name="John Smith", role="Director Of Operations", company="Globex Logistics"),
    # Generic engineer, industrial company — some signal.
    _row(full_name="Amy Lee", role="Engineer", company="Industrial Systems Ltd"),
    # Unrelated role and company — should score low.
    _row(full_name="Sam Poe", role="Graphic Designer", company="Pixel Studio"),
])


def main() -> None:
    print("LOBO AI Leads — Stage 5 scoring test")
    print("=" * 55)

    scored = lead_scoring.score_leads(SAMPLE)
    prioritised = priority_engine.assign_priority(scored)

    print(prioritised[["full_name", "role", "company",
                        "lead_score", "lead_priority"]].to_string(index=False))
    print("=" * 55)
    print("SUCCESS: leads scored and prioritised.")


if __name__ == "__main__":
    main()
