"""
ai_calling_client.py
==================
STUB for a future AI calling-system integration.

When implemented this will hand HIGH-priority leads to an automated calling
platform (e.g. queue calls, sync outcomes back to 04_CALL_HISTORY). For now
it logs intent and no-ops.
"""

import pandas as pd

from app.integrations.base import LeadIntegration


class AICallingIntegration(LeadIntegration):
    name = "ai_calling"

    def send_leads(self, df: pd.DataFrame) -> None:
        # TODO: filter to HIGH priority and enqueue calls via the calling API.
        self._not_implemented(df)
