"""
priority_engine.py
==================
Turns a numeric `lead_score` into a human-friendly `lead_priority` bucket:
HIGH / MEDIUM / LOW.

Keeping this separate from scoring means you can change the *bucketing* (the
thresholds) without touching how scores are calculated, and vice versa.
Thresholds live in constants.PRIORITY_THRESHOLDS so they're easy to retune.
"""

import pandas as pd

from app.config.constants import PRIORITY_THRESHOLDS
from app.logs.logger import get_logger

log = get_logger(__name__)


def score_to_priority(score: int) -> str:
    """Map a numeric score to HIGH / MEDIUM / LOW using the thresholds."""
    if score >= PRIORITY_THRESHOLDS["HIGH"]:
        return "HIGH"
    if score >= PRIORITY_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "LOW"


def assign_priority(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of `df` with `lead_priority` filled from `lead_score`.

    Assumes `lead_score` is already populated (Stage 5 scoring runs first).
    """
    df = df.copy()
    df["lead_priority"] = df["lead_score"].fillna(0).astype(int).apply(score_to_priority)

    if len(df):
        counts = df["lead_priority"].value_counts().to_dict()
        log.info("Priority breakdown: %s", counts)
    return df
