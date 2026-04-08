"""
Seed script for INTELECOR development database.
Run with: python -m db.seed
"""
import csv
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from db.base import Base
from db.tables import TenantTable, BillingEventTable

DATABASE_URL_SYNC = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://intelecor:intelecor_dev@localhost:5432/intelecor",
)
CSV_PATH = Path(__file__).parent.parent / "data" / "mock" / "gentu_billing_export.csv"
TENANT_ID = "tnt_roycardiology_001"


def parse_date(value: str) -> date | None:
    if not value or not value.strip():
        return None
    return date.fromisoformat(value.strip())


def parse_decimal(value: str) -> Decimal | None:
    if not value or not value.strip():
        return None
    return Decimal(value.strip())


def seed(session: Session) -> None:
    # 1. Upsert tenant
    tenant = TenantTable(
        id=TENANT_ID,
        name="Roy Cardiology",
        practice_name="Roy Cardiology",
        contact_email="andrew@roycardiology.com.au",
        config={
            "adapter_type": "mock",
            "mbs_items_tracked": ["110", "116", "55126", "55141", "11700", "91824"],
            "dna_alert_threshold": 10.0,
            "unsigned_warning_days": 7,
        },
        active=True,
    )
    session.merge(tenant)

    # 2. Read CSV and upsert billing events
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            event = BillingEventTable(
                invoice_id=row["Invoice ID"].strip(),
                tenant_id=TENANT_ID,
                patient_id=row["Patient ID"].strip() or None,
                practitioner_id=None,  # CSV has name only; no ID in export
                provider_number=row["Provider Number"].strip() or None,
                location=row["Location"].strip() or None,
                appointment_id=row["Appointment ID"].strip() or None,
                invoice_date=parse_date(row["Invoice Date"]),
                service_date=parse_date(row["Service Date"]),
                mbs_item=row["MBS Item"].strip(),
                item_description=row["Item Description"].strip() or None,
                schedule_fee=parse_decimal(row["Schedule Fee"]),
                charged_amount=parse_decimal(row["Charged Amount"]),
                billing_type=row["Billing Type"].strip(),
                claim_status=row["Claim Status"].strip(),
                payment_status=row["Payment Status"].strip(),
                medicare_benefit=parse_decimal(row["Medicare Benefit"]),
                gap_amount=parse_decimal(row["Gap Amount"]),
                patient_paid=parse_decimal(row["Patient Paid"]),
                insurer_paid=parse_decimal(row["Insurer Paid"]),
                dva_amount=parse_decimal(row["DVA Amount"]),
                total_received=parse_decimal(row["Total Received"]),
                outstanding=parse_decimal(row["Outstanding"]),
                claim_submitted_date=parse_date(row["Claim Submitted Date"]),
                claim_processed_date=parse_date(row["Claim Processed Date"]),
                payment_received_date=parse_date(row["Payment Received Date"]),
                referring_doctor=row["Referring Doctor"].strip() or None,
                referring_provider_no=row["Referring Provider No"].strip() or None,
                notes=row["Notes"].strip() or None,
            )
            session.merge(event)

    session.commit()


def main() -> None:
    engine = create_engine(DATABASE_URL_SYNC, echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        seed(session)

        tenant_count = session.execute(
            select(func.count()).select_from(TenantTable)
        ).scalar()
        billing_count = session.execute(
            select(func.count()).select_from(BillingEventTable)
        ).scalar()

    print(f"Tenants:        {tenant_count}")
    print(f"Billing events: {billing_count}")


if __name__ == "__main__":
    main()
