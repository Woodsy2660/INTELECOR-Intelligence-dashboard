from pydantic import BaseModel
from datetime import date, datetime
from enum import Enum
from typing import Optional


class BillingType(str, Enum):
    PRIVATE = "private"
    BULK_BILL = "bulk_bill"
    DVA = "dva"
    ECLIPSE_NO_GAP = "eclipse_no_gap"
    ECLIPSE_KNOWN_GAP = "eclipse_known_gap"
    ECLIPSE_PATIENT_CLAIM = "eclipse_patient_claim"
    WORKCOVER = "workcover"


class ClaimStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING = "pending"


class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    PENDING = "pending"


class BillingEvent(BaseModel):
    invoice_id: str
    tenant_id: str
    patient_id: str
    practitioner_id: str
    provider_number: str
    location: str
    appointment_id: Optional[str] = None
    invoice_date: date
    service_date: date
    mbs_item: str
    item_description: str
    schedule_fee: float
    charged_amount: float
    billing_type: BillingType
    claim_status: ClaimStatus
    payment_status: PaymentStatus
    medicare_benefit: float = 0.0
    gap_amount: float = 0.0
    patient_paid: float = 0.0
    insurer_paid: float = 0.0
    dva_amount: float = 0.0
    total_received: float = 0.0
    outstanding: float = 0.0
    claim_submitted_date: Optional[date] = None
    claim_processed_date: Optional[date] = None
    payment_received_date: Optional[date] = None
    referring_doctor: Optional[str] = None
    referring_provider_no: Optional[str] = None
    notes: Optional[str] = None


class FinancialSummary(BaseModel):
    """Output model for financial analytics — aggregate figures only."""
    total_billed: float
    total_received: float
    total_outstanding: float
    collection_rate: float
    by_billing_type: dict[str, float]
    by_mbs_item: dict[str, dict]
    leakage_flags: list[dict]
    period_comparison: Optional[dict] = None


class LeakageFlag(BaseModel):
    flag_type: str  # rejected_claim, unbilled_appointment, overdue_gap
    reference_id: str
    patient_id: str
    service_date: date
    mbs_item: Optional[str] = None
    amount: Optional[float] = None
    detail: str
    severity: str  # red, amber, yellow
