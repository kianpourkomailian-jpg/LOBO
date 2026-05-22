"""
lead_scoring.py
==============
Assigns a numeric `lead_score` (0-100) to each lead.

Design goals (from the brief)
-----------------------------
* MODULAR    — scoring rules live in constants.py, logic lives here.
* EDITABLE   — retune by changing weights/keyword lists, not code.
* WEIGHTED   — each signal contributes a configurable number of points.

How a score is built
---------------------
For each lead we look at its role + company text and award points for:
  1. matching a HIGH_VALUE_ROLE        (one-off bonus),
  2. each HIGH_VALUE_INDUSTRY keyword  (per match),
  3. each DECISION_MAKER_KEYWORD       (per match).
The total is capped at 100 so scores stay comparable.
"""

import pandas as pd

from app.config.constants import (
    DECISION_MAKER_KEYWORDS,
    HIGH_VALUE_INDUSTRIES,
    HIGH_VALUE_ROLES,
    SCORING_WEIGHTS,
)
from app.logs.logger import get_logger

log = get_logger(__name__)

_MAX_SCORE = 100


def score_row(row: pd.Series) -> int:
    """
    Compute the 0-100 score for a single lead row.

    Kept as a standalone function so it's easy to unit-test and reuse.
    """
    role = (row.get("role") or "").lower()
    company = (row.get("company") or "").lower()
    # Industries can show up in either the role or the company name.
    haystack = f"{role} {company}"

    score = 0

    # 1) High-value role: a single bonus if ANY target title appears.
    if any(title in role for title in HIGH_VALUE_ROLES):
        score += SCORING_WEIGHTS["high_value_role"]

    # 2) Industry keywords: points per distinct industry matched.
    for industry in HIGH_VALUE_INDUSTRIES:
        if industry in haystack:
            score += SCORING_WEIGHTS["industry"]

    # 3) Decision-maker keywords: points per distinct keyword matched.
    for keyword in DECISION_MAKER_KEYWORDS:
        if keyword in role:
            score += SCORING_WEIGHTS["decision_maker_keyword"]

    return min(score, _MAX_SCORE)


def score_leads(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `df` with the `lead_score` column populated."""
    df = df.copy()
    df["lead_score"] = df.apply(score_row, axis=1)
    log.info("Scored %d leads (avg %.1f)", len(df),
             df["lead_score"].mean() if len(df) else 0)
    return df
