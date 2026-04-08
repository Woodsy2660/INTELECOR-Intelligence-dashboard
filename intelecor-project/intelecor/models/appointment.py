from pydantic import BaseModel
from datetime import datetime, date
from enum import Enum
from typing import Optional


class AppointmentStatus(str, Enum):
    BOOKED = "booked"
    CONFIRMED = "confirmed"
    ARRIVED = "arrived"
    IN_CONSULT = "in_consult"
    COMPLETED = "completed"
    DID_NOT_ARRIVE = "did_not_arrive"
    CANCELLED = "cancelled"


class AppointmentCategory(str, Enum):
    CONSULTATION = "consultation"
    PROCEDURE = "procedure"


class AppointmentType(BaseModel):
    id: str
    name: str
    duration_minutes: int
    category: AppointmentCategory
    colour: Optional[str] = None


class Appointment(BaseModel):
    id: str
    tenant_id: str
    patient_id: str
    practitioner_id: str
    location_id: str
    appointment_type: AppointmentType
    scheduled_start: datetime
    scheduled_end: datetime
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    status: AppointmentStatus
    did_not_arrive: bool = False
    is_new_patient: bool = False
    cancellation_reason: Optional[str] = None
    referral_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AppointmentSummary(BaseModel):
    """Output model for operations analytics — no patient-identifiable data."""
    total_scheduled: int
    total_completed: int
    total_dna: int
    total_cancelled: int
    completion_rate: float
    dna_rate: float
    new_patient_count: int
    followup_count: int
    procedure_count: int
    new_patient_ratio: float
    by_type: dict[str, int]
    by_status: dict[str, int]
    by_day: dict[str, dict[str, int]]
