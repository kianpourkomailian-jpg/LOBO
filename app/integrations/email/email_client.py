"""
email_client.py
==============
STUB for a future email outreach integration.

When implemented this will enroll leads (those with valid emails) into an
outreach sequence via an email/ESP API. For now it logs intent and no-ops.
"""

import pandas as pd

from app.integrations.base import LeadIntegration


class EmailIntegration(LeadIntegration):
    name = "email"

    def send_leads(self, df: pd.DataFrame) -> None:
        # TODO: send/enroll leads with non-empty emails via an ESP API.
        self._not_implemented(df)
