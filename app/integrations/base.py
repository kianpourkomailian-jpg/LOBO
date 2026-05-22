"""
base.py
======
The shared contract every outbound integration implements.

Why a base class?
-----------------
The brief calls for future integrations (Dynamics, Google Sheets, AI calling,
email). Rather than each one inventing its own shape, they all subclass
`LeadIntegration` and implement `send_leads`. That gives the pipeline a single,
predictable way to push leads to any destination later:

    for integration in enabled_integrations:
        integration.send_leads(final_df)

Each concrete integration today is a STUB that logs and no-ops, so the seam
exists and is testable without committing to any external SDK yet.
"""

from abc import ABC, abstractmethod

import pandas as pd

from app.logs.logger import get_logger

log = get_logger(__name__)


class LeadIntegration(ABC):
    """Abstract base for anything that receives processed leads."""

    #: Human-readable name, set by subclasses (used in logs).
    name: str = "base"

    @property
    def enabled(self) -> bool:
        """
        Whether this integration should run.

        Stubs return False so they're safely skipped until real config +
        credentials are wired in. Override once an integration is implemented.
        """
        return False

    @abstractmethod
    def send_leads(self, df: pd.DataFrame) -> None:
        """Push the given leads to the destination. Implemented per backend."""
        raise NotImplementedError

    def _not_implemented(self, df: pd.DataFrame) -> None:
        """Helper for stubs: log intent without failing the pipeline."""
        log.info(
            "[%s] integration not implemented yet — would send %d lead(s).",
            self.name,
            len(df),
        )
