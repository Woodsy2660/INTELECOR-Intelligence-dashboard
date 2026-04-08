import csv
from datetime import date
from pathlib import Path
from models.billing import BillingEvent, BillingType, ClaimStatus, PaymentStatus


class CsvBillingAdapter:
    """
    Parses Gentu CSV billing exports into internal BillingEvent models.

    This adapter handles financial data because Gentu does not expose
    billing endpoints through its developer partner API. Practices
    export billing data as CSV from within Gentu.
    """

    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)

    async def get_billing_events(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> list[BillingEvent]:
        rows = self._read_csv()
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

    def _read_csv(self) -> list[dict]:
        with open(self.csv_path, "r") as f:
            return list(csv.DictReader(f))

    def _parse_date(self, value: str | None) -> date | None:
        if not value or not value.strip():
            return None
        return date.fromisoformat(value.strip())
