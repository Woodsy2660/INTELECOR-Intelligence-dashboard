from abc import ABC, abstractmethod
from datetime import date
from models.appointment import Appointment
from models.billing import BillingEvent
from models.document import Document
from models.referral import Referral, Practitioner, Patient


class BaseAdapter(ABC):
    """
    Abstract adapter interface.

    Every data source adapter (Mock, Gentu API, CSV) must implement
    these methods and return data as internal Pydantic models.

    The adapter is responsible for:
    - Connecting to the data source
    - Pulling raw data
    - Translating vendor-specific schemas into internal models
    - Stripping PII where required (patient names, Medicare numbers, etc.)

    The adapter is NOT responsible for:
    - Storing data (that's the pipeline's job)
    - Running analytics (that's the analytics modules' job)
    - Authentication/authorisation (that's the API layer's job)
    """

    @abstractmethod
    async def get_appointments(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[Appointment]:
        """Fetch appointments for the given date range."""
        pass

    @abstractmethod
    async def get_billing_events(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[BillingEvent]:
        """Fetch billing/invoice records for the given date range."""
        pass

    @abstractmethod
    async def get_documents(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[Document]:
        """Fetch correspondence/letters for the given date range."""
        pass

    @abstractmethod
    async def get_referrals(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[Referral]:
        """Fetch referrals for the given date range."""
        pass

    @abstractmethod
    async def get_practitioners(self, tenant_id: str) -> list[Practitioner]:
        """Fetch practitioner profiles for the tenant."""
        pass

    @abstractmethod
    async def get_patients(
        self, tenant_id: str, patient_ids: list[str] | None = None
    ) -> list[Patient]:
        """Fetch de-identified patient records."""
        pass
