from datetime import date
import httpx
from adapters.base import BaseAdapter
from models.appointment import Appointment
from models.billing import BillingEvent
from models.document import Document
from models.referral import Referral, Practitioner, Patient
from api.config import get_settings


class GentuAdapter(BaseAdapter):
    """
    Gentu API adapter — connects to the four Gentu REST APIs.

    Requires developer partner access from Magentus.
    Status: STUB — to be implemented when API access is granted.

    APIs used:
    - Healthcare API: GET /tenants/{id}/appointments (patient + appointment data)
    - Bookings API: practitioners, referrals, availability
    - Letters API: outgoing correspondence pipeline
    - Billing: CSV export (no API available)
    """

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.gentu_api_base_url
        self.api_key = settings.gentu_api_key
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )

    async def get_appointments(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[Appointment]:
        # TODO: Implement when Gentu Healthcare API access is granted
        # endpoint: GET /tenants/{tenant_id}/appointments
        # params: start_date, end_date, page, per_page
        # Response contains nested patient, practitioner, location objects
        raise NotImplementedError("Gentu API access pending — use MockAdapter")

    async def get_billing_events(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[BillingEvent]:
        # Billing data comes via CSV export, not API
        # Use CsvAdapter for billing data
        raise NotImplementedError("Billing data uses CSV export — use CsvAdapter")

    async def get_documents(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[Document]:
        # TODO: Implement when Gentu Letters API access is granted
        raise NotImplementedError("Gentu API access pending — use MockAdapter")

    async def get_referrals(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[Referral]:
        # TODO: Implement when Gentu Bookings API access is granted
        raise NotImplementedError("Gentu API access pending — use MockAdapter")

    async def get_practitioners(self, tenant_id: str) -> list[Practitioner]:
        # TODO: Implement when Gentu Bookings API access is granted
        raise NotImplementedError("Gentu API access pending — use MockAdapter")

    async def get_patients(
        self, tenant_id: str, patient_ids: list[str] | None = None
    ) -> list[Patient]:
        # Patients are extracted from appointment responses in the Healthcare API
        raise NotImplementedError("Gentu API access pending — use MockAdapter")

    async def close(self):
        await self.client.aclose()
