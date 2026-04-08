import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Date, DateTime,
    Text, Index, Numeric,
)
from sqlalchemy.dialects.postgresql import JSONB
from db.base import Base


def gen_uuid():
    return str(uuid.uuid4())


class TenantTable(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    practice_name = Column(String, nullable=False)
    abn = Column(String)
    contact_email = Column(String)
    config = Column(JSONB, default=dict)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BillingEventTable(Base):
    __tablename__ = "billing_events"

    invoice_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    patient_id = Column(String)
    practitioner_id = Column(String)
    provider_number = Column(String)
    location = Column(String)
    appointment_id = Column(String)
    invoice_date = Column(Date, nullable=False)
    service_date = Column(Date, nullable=False)
    mbs_item = Column(String, nullable=False)
    item_description = Column(String)
    schedule_fee = Column(Numeric(10, 2), default=0)
    charged_amount = Column(Numeric(10, 2), default=0)
    billing_type = Column(String, nullable=False)
    claim_status = Column(String, nullable=False)
    payment_status = Column(String, nullable=False)
    medicare_benefit = Column(Numeric(10, 2), default=0)
    gap_amount = Column(Numeric(10, 2), default=0)
    patient_paid = Column(Numeric(10, 2), default=0)
    insurer_paid = Column(Numeric(10, 2), default=0)
    dva_amount = Column(Numeric(10, 2), default=0)
    total_received = Column(Numeric(10, 2), default=0)
    outstanding = Column(Numeric(10, 2), default=0)
    claim_submitted_date = Column(Date)
    claim_processed_date = Column(Date)
    payment_received_date = Column(Date)
    referring_doctor = Column(String)
    referring_provider_no = Column(String)
    notes = Column(Text)

    __table_args__ = (
        Index("ix_billing_tenant_date", "tenant_id", "service_date"),
        Index("ix_billing_status", "tenant_id", "payment_status"),
        Index("ix_billing_mbs", "tenant_id", "mbs_item"),
        Index("ix_billing_claim", "tenant_id", "claim_status"),
    )


class AnalyticsResultTable(Base):
    __tablename__ = "analytics_results"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, nullable=False)
    module = Column(String, nullable=False)
    period_type = Column(String, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    results = Column(JSONB, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_analytics_lookup", "tenant_id", "module", "period_type", "period_start"),
    )
