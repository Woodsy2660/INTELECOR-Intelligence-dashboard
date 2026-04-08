from pydantic import BaseModel
from datetime import date, datetime
from enum import Enum
from typing import Optional


# --- Referrals ---

class ReferralStatus(str, Enum):
    ACTIVE = "active"
    PENDING_APPOINTMENT = "pending_appointment"
    EXPIRED = "expired"
    COMPLETED = "completed"


class ReferralUrgency(str, Enum):
    ROUTINE = "routine"
    SEMI_URGENT = "semi_urgent"
    URGENT = "urgent"


class ReferringDoctor(BaseModel):
    title: Optional[str] = None
    given_name: str
    family_name: str
    provider_number: str
    practice_name: str


class Referral(BaseModel):
    id: str
    tenant_id: str
    patient_id: str
    referring_doctor: ReferringDoctor
    referral_date: date
    received_date: Optional[date] = None
    valid_to: date
    referral_reason: Optional[str] = None
    urgency: ReferralUrgency = ReferralUrgency.ROUTINE
    status: ReferralStatus
    linked_appointment_id: Optional[str] = None
    created_at: datetime


# --- Practitioners ---

class ProviderNumber(BaseModel):
    number: str
    location_id: str
    location_name: str


class Practitioner(BaseModel):
    id: str
    tenant_id: str
    title: Optional[str] = None
    given_name: str
    family_name: str
    provider_numbers: list[ProviderNumber]
    specialty: str
    ahpra_number: Optional[str] = None
    active: bool = True


# --- Patients (de-identified for analytics) ---

class Patient(BaseModel):
    """Minimal patient record for analytics. No PII beyond what's needed for linking."""
    id: str
    tenant_id: str
    date_of_birth: date
    gender: Optional[str] = None
    concession_type: Optional[str] = None
    postcode: Optional[str] = None  # suburb-level only, for demographic analysis
    is_dva: bool = False
    created_at: datetime
