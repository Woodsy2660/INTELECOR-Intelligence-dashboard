import json
import csv
from datetime import date, datetime
from pathlib import Path
from adapters.base import BaseAdapter
from models.appointment import (
    Appointment, AppointmentType, AppointmentStatus, AppointmentCategory,
)
from models.billing import BillingEvent, BillingType, ClaimStatus, PaymentStatus
from models.document import (
    Document, LetterStatus, LetterType, DictationSource, LetterRecipient,
)
from models.referral import (
    Referral, ReferralStatus, ReferralUrgency, ReferringDoctor,
    Practitioner, ProviderNumber, Patient,
)


DATA_DIR = Path(__file__).parent.parent / "data" / "mock"


class MockAdapter(BaseAdapter):
    """
    Loads mock data from JSON and CSV files.
    Translates the simulated Gentu response format into internal Pydantic models.

    This is the reference implementation — it demonstrates exactly how the
    Gentu adapter will translate real API responses into internal models.
    """

    async def get_appointments(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[Appointment]:
        raw = self._load_json("healthcare_api_appointments.json")
        appointments = []

        for appt in raw.get("appointments", []):
            scheduled = datetime.fromisoformat(appt["scheduled_start"])
            if not (start_date <= scheduled.date() <= end_date):
                continue

            apt_type = appt["appointment_type"]
            appointments.append(Appointment(
                id=appt["id"],
                tenant_id=tenant_id,
                patient_id=appt["patient"]["id"],
                practitioner_id=appt["practitioner"]["id"],
                location_id=appt["location"]["id"],
                appointment_type=AppointmentType(
                    id=apt_type["id"],
                    name=apt_type["name"],
                    duration_minutes=apt_type["duration_minutes"],
                    category=AppointmentCategory(apt_type["category"]),
                    colour=apt_type.get("colour"),
                ),
                scheduled_start=datetime.fromisoformat(appt["scheduled_start"]),
                scheduled_end=datetime.fromisoformat(appt["scheduled_end"]),
                actual_start=self._parse_dt(appt.get("actual_start")),
                actual_end=self._parse_dt(appt.get("actual_end")),
                status=AppointmentStatus(appt["status"]),
                did_not_arrive=appt.get("did_not_arrive", False),
                is_new_patient=appt.get("is_new_patient", False),
                cancellation_reason=appt.get("cancellation_reason"),
                referral_id=appt.get("referral", {}).get("id") if appt.get("referral") else None,
                notes=appt.get("notes"),
                created_at=datetime.fromisoformat(appt["created_at"]),
                updated_at=datetime.fromisoformat(appt["updated_at"]),
            ))

        return appointments

    async def get_billing_events(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[BillingEvent]:
        rows = self._load_csv("gentu_billing_export.csv")
        events = []

        for row in rows:
            service_date = date.fromisoformat(row["Service Date"])
            if not (start_date <= service_date <= end_date):
                continue

            events.append(BillingEvent(
                invoice_id=row["Invoice ID"],
                tenant_id=tenant_id,
                patient_id=row["Patient ID"],
                practitioner_id="prac_001",
                provider_number=row["Provider Number"],
                location=row["Location"],
                appointment_id=row["Appointment ID"],
                invoice_date=date.fromisoformat(row["Invoice Date"]),
                service_date=service_date,
                mbs_item=row["MBS Item"],
                item_description=row["Item Description"],
                schedule_fee=float(row["Schedule Fee"]),
                charged_amount=float(row["Charged Amount"]),
                billing_type=BillingType(row["Billing Type"]),
                claim_status=ClaimStatus(row["Claim Status"]),
                payment_status=PaymentStatus(row["Payment Status"]),
                medicare_benefit=float(row["Medicare Benefit"]),
                gap_amount=float(row["Gap Amount"]),
                patient_paid=float(row["Patient Paid"]),
                insurer_paid=float(row["Insurer Paid"]),
                dva_amount=float(row["DVA Amount"]),
                total_received=float(row["Total Received"]),
                outstanding=float(row["Outstanding"]),
                claim_submitted_date=self._parse_date(row.get("Claim Submitted Date")),
                claim_processed_date=self._parse_date(row.get("Claim Processed Date")),
                payment_received_date=self._parse_date(row.get("Payment Received Date")),
                referring_doctor=row.get("Referring Doctor"),
                referring_provider_no=row.get("Referring Provider No"),
                notes=row.get("Notes"),
            ))

        return events

    async def get_documents(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[Document]:
        raw = self._load_json("letters_api_correspondence.json")
        documents = []

        for ltr in raw.get("letters", []):
            created = datetime.fromisoformat(ltr["created_at"])
            if not (start_date <= created.date() <= end_date):
                continue

            recipient = ltr["recipient"]
            documents.append(Document(
                id=ltr["id"],
                tenant_id=tenant_id,
                patient_id=ltr["patient_id"],
                practitioner_id=ltr["practitioner_id"],
                appointment_id=ltr.get("appointment_id"),
                letter_type=LetterType(ltr["letter_type"]),
                template=ltr.get("template"),
                recipient=LetterRecipient(
                    title=recipient.get("title"),
                    given_name=recipient["given_name"],
                    family_name=recipient["family_name"],
                    provider_number=recipient.get("provider_number"),
                    practice_name=recipient.get("practice_name"),
                ),
                subject=ltr.get("subject"),
                status=LetterStatus(ltr["status"]),
                dictation_source=DictationSource(ltr["dictation_source"]) if ltr.get("dictation_source") else None,
                created_at=datetime.fromisoformat(ltr["created_at"]),
                updated_at=datetime.fromisoformat(ltr["updated_at"]),
                signed_at=self._parse_dt(ltr.get("signed_at")),
                sent_at=self._parse_dt(ltr.get("sent_at")),
                sent_method=ltr.get("sent_method"),
                days_unsigned=ltr.get("days_unsigned", 0),
            ))

        return documents

    async def get_referrals(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[Referral]:
        raw = self._load_json("bookings_api_practitioners.json")
        referrals = []

        for ref in raw.get("referrals", []):
            ref_date = date.fromisoformat(ref["referral_date"])
            if not (start_date <= ref_date <= end_date):
                continue

            doc = ref["referring_doctor"]
            referrals.append(Referral(
                id=ref["id"],
                tenant_id=tenant_id,
                patient_id=ref["patient_id"],
                referring_doctor=ReferringDoctor(
                    title=doc.get("title"),
                    given_name=doc["given_name"],
                    family_name=doc["family_name"],
                    provider_number=doc["provider_number"],
                    practice_name=doc["practice_name"],
                ),
                referral_date=ref_date,
                received_date=self._parse_date(ref.get("received_date")),
                valid_to=date.fromisoformat(ref["valid_to"]),
                referral_reason=ref.get("referral_reason"),
                urgency=ReferralUrgency(ref.get("urgency", "routine")),
                status=ReferralStatus(ref["status"]),
                linked_appointment_id=ref.get("linked_appointment_id"),
                created_at=datetime.fromisoformat(ref["created_at"]),
            ))

        return referrals

    async def get_practitioners(self, tenant_id: str) -> list[Practitioner]:
        raw = self._load_json("bookings_api_practitioners.json")
        practitioners = []

        for prac in raw.get("practitioners", []):
            practitioners.append(Practitioner(
                id=prac["id"],
                tenant_id=tenant_id,
                title=prac.get("title"),
                given_name=prac["given_name"],
                family_name=prac["family_name"],
                provider_numbers=[
                    ProviderNumber(**pn) for pn in prac.get("provider_numbers", [])
                ],
                specialty=prac["specialty"],
                ahpra_number=prac.get("ahpra_number"),
                active=prac.get("active", True),
            ))

        return practitioners

    async def get_patients(
        self, tenant_id: str, patient_ids: list[str] | None = None
    ) -> list[Patient]:
        raw = self._load_json("healthcare_api_appointments.json")
        seen = set()
        patients = []

        for appt in raw.get("appointments", []):
            pat = appt["patient"]
            if pat["id"] in seen:
                continue
            if patient_ids and pat["id"] not in patient_ids:
                continue
            seen.add(pat["id"])

            patients.append(Patient(
                id=pat["id"],
                tenant_id=tenant_id,
                date_of_birth=date.fromisoformat(pat["date_of_birth"]),
                gender=pat.get("gender"),
                concession_type=pat.get("concession_type"),
                postcode=pat.get("address", {}).get("postcode"),
                is_dva=pat.get("dva_file_number") is not None,
                created_at=datetime.fromisoformat(appt["created_at"]),
            ))

        return patients

    # --- Helpers ---

    def _load_json(self, filename: str) -> dict:
        filepath = DATA_DIR / filename
        with open(filepath, "r") as f:
            return json.load(f)

    def _load_csv(self, filename: str) -> list[dict]:
        filepath = DATA_DIR / filename
        with open(filepath, "r") as f:
            return list(csv.DictReader(f))

    def _parse_dt(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    def _parse_date(self, value: str | None) -> date | None:
        if not value or not value.strip():
            return None
        return date.fromisoformat(value.strip())
