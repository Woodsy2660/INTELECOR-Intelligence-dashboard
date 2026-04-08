from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional


class LetterStatus(str, Enum):
    DRAFT = "draft"
    UNSIGNED = "unsigned"
    SIGNED = "signed"
    SENT = "sent"


class LetterType(str, Enum):
    CONSULTATION_REPORT = "consultation_report"
    PROCEDURE_REPORT = "procedure_report"
    REFERRAL_LETTER = "referral_letter"
    DISCHARGE_SUMMARY = "discharge_summary"


class DictationSource(str, Enum):
    HEIDI_AI_SCRIBE = "heidi_ai_scribe"
    MANUAL_DICTATION = "manual_dictation"
    VOICEBOX = "voicebox"
    TYPED = "typed"


class LetterRecipient(BaseModel):
    title: Optional[str] = None
    given_name: str
    family_name: str
    provider_number: Optional[str] = None
    practice_name: Optional[str] = None


class Document(BaseModel):
    id: str
    tenant_id: str
    patient_id: str
    practitioner_id: str
    appointment_id: Optional[str] = None
    letter_type: LetterType
    template: Optional[str] = None
    recipient: LetterRecipient
    subject: Optional[str] = None
    status: LetterStatus
    dictation_source: Optional[DictationSource] = None
    created_at: datetime
    updated_at: datetime
    signed_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    sent_method: Optional[str] = None
    days_unsigned: int = 0


class DocumentSummary(BaseModel):
    """Output model for documents analytics."""
    total_unsigned: int
    total_signed_unsent: int
    avg_days_to_sign: float
    by_age_bracket: dict[str, int]
    by_type: dict[str, int]
    weekly_created: list[int]
    weekly_signed: list[int]
    unsigned_queue: list[dict]
