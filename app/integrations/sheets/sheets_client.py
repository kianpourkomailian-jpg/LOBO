"""
sheets_client.py
===============
STUB for a future Google Sheets integration.

When implemented this will append/sync cleaned leads to a Google Sheet (the
same service account already has Drive access, so it can be extended to the
Sheets API). For now it logs intent and no-ops.
"""

import pandas as pd

from app.integrations.base import LeadIntegration


class SheetsIntegration(LeadIntegration):
    name = "sheets"

    def send_leads(self, df: pd.DataFrame) -> None:
        # TODO: use the Sheets API to append rows to a configured spreadsheet.
        self._not_implemented(df)
