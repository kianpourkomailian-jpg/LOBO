"""
dynamics_client.py
=================
STUB for a future Microsoft Dynamics 365 integration.

When implemented this will push scored leads into Dynamics (e.g. via the
Dataverse Web API / OAuth). For now it's a no-op that logs intent, so the
pipeline can reference it without any Dynamics credentials existing yet.
"""

import pandas as pd

from app.integrations.base import LeadIntegration


class DynamicsIntegration(LeadIntegration):
    name = "dynamics"

    def send_leads(self, df: pd.DataFrame) -> None:
        # TODO: authenticate to Dataverse and upsert leads as Contacts/Leads.
        self._not_implemented(df)
