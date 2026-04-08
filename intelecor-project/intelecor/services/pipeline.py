import structlog
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from adapters.base import BaseAdapter
from analytics.financial import FinancialAnalytics
from analytics.operations import OperationsAnalytics
from analytics.documents import DocumentsAnalytics
from db.tables import BillingEventTable, AnalyticsResultTable

logger = structlog.get_logger()


class Pipeline:
    """
    ETL orchestrator — transient processing architecture.

    Flow:
      1. Pull data from adapter into memory (Pydantic models)
      2. Load billing records from PostgreSQL (permanent storage)
      3. Run analytics modules against in-memory data
      4. Save computed aggregate results to PostgreSQL
      5. Discard raw data (garbage collected on function return)

    Raw appointment, document, and referral data NEVER touches the database.
    Only billing records (from CSV import) and computed analytics snapshots persist.
    """

    def __init__(self, adapter: BaseAdapter):
        self.adapter = adapter
        self.financial = FinancialAnalytics()
        self.operations = OperationsAnalytics()
        self.documents = DocumentsAnalytics()

    async def run_full(
        self,
        tenant_id: str,
        session: AsyncSession,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        logger.info("pipeline.start", tenant_id=tenant_id,
                     start_date=str(start_date), end_date=str(end_date))

        # Step 1: Pull operational data into memory (transient)
        appointments = await self.adapter.get_appointments(tenant_id, start_date, end_date)
        documents = await self.adapter.get_documents(tenant_id, start_date, end_date)
        referrals = await self.adapter.get_referrals(tenant_id, start_date, end_date)

        # Step 2: Load billing data from PostgreSQL (permanent storage)
        billing_result = await session.execute(
            select(BillingEventTable)
            .where(BillingEventTable.tenant_id == tenant_id)
            .where(BillingEventTable.service_date >= start_date)
            .where(BillingEventTable.service_date <= end_date)
        )
        billing_rows = billing_result.scalars().all()
        billing_events = self._rows_to_billing_models(billing_rows, tenant_id)

        # Step 3: Run analytics modules against in-memory data
        financial_results = self.financial.analyse(
            billing_events=billing_events,
            appointments=appointments,
        )

        operations_results = self.operations.analyse(
            appointments=appointments,
            referrals=referrals,
        )

        documents_results = self.documents.analyse(
            documents=documents,
        )

        results = {
            "financial": financial_results.model_dump(),
            "operations": operations_results,
            "documents": documents_results.model_dump(),
        }

        # Step 4: Save computed aggregates to PostgreSQL
        for module, data in results.items():
            session.add(AnalyticsResultTable(
                tenant_id=tenant_id,
                module=module,
                period_type="weekly",
                period_start=start_date,
                period_end=end_date,
                results=data,
            ))

        await session.commit()

        logger.info("pipeline.complete", tenant_id=tenant_id,
                     appointments_processed=len(appointments),
                     documents_processed=len(documents),
                     billing_records=len(billing_events))

        # Step 5: Raw data discarded — function returns, memory freed
        # appointments, documents, referrals are garbage collected
        # Only the aggregate results in analytics_results table persist

        return results

    def _rows_to_billing_models(self, rows, tenant_id):
        from models.billing import BillingEvent, BillingType, ClaimStatus, PaymentStatus

        events = []
        for row in rows:
            events.append(BillingEvent(
                invoice_id=row.invoice_id,
                tenant_id=tenant_id,
                patient_id=row.patient_id or "",
                practitioner_id=row.practitioner_id or "",
                provider_number=row.provider_number or "",
                location=row.location or "",
                appointment_id=row.appointment_id,
                invoice_date=row.invoice_date,
                service_date=row.service_date,
                mbs_item=row.mbs_item,
                item_description=row.item_description or "",
                schedule_fee=float(row.schedule_fee or 0),
                charged_amount=float(row.charged_amount or 0),
                billing_type=BillingType(row.billing_type),
                claim_status=ClaimStatus(row.claim_status),
                payment_status=PaymentStatus(row.payment_status),
                medicare_benefit=float(row.medicare_benefit or 0),
                gap_amount=float(row.gap_amount or 0),
                patient_paid=float(row.patient_paid or 0),
                insurer_paid=float(row.insurer_paid or 0),
                dva_amount=float(row.dva_amount or 0),
                total_received=float(row.total_received or 0),
                outstanding=float(row.outstanding or 0),
                claim_submitted_date=row.claim_submitted_date,
                claim_processed_date=row.claim_processed_date,
                payment_received_date=row.payment_received_date,
                referring_doctor=row.referring_doctor,
                referring_provider_no=row.referring_provider_no,
                notes=row.notes,
            ))
        return events
