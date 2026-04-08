from fastapi import APIRouter, Depends
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from api.dependencies import get_current_tenant, get_session
from db.tables import AnalyticsResultTable, BillingEventTable

router = APIRouter()


@router.get("/summary")
async def get_financial_summary(
    tenant_id: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """
    Financial screen: aggregate metrics from pre-computed analytics.
    Returns totals, collection rate, billing type breakdown, MBS breakdown.
    Source: analytics_results table (no patient data).
    """
    result = await session.execute(
        select(AnalyticsResultTable)
        .where(AnalyticsResultTable.tenant_id == tenant_id)
        .where(AnalyticsResultTable.module == "financial")
        .order_by(AnalyticsResultTable.generated_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    return latest.results if latest else {}


@router.get("/leakage")
async def get_leakage_flags(
    tenant_id: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """
    Revenue leakage flags — hybrid approach.

    Rejected claims + overdue gaps: queried from billing_events table
    (permanently stored from CSV import).

    Unbilled appointments: real-time pass-through to Gentu API,
    cross-referenced against billing_events to find completed
    appointments with no matching invoice.
    """
    flags = []

    # --- From PostgreSQL: rejected claims ---
    rejected = await session.execute(
        select(BillingEventTable)
        .where(BillingEventTable.tenant_id == tenant_id)
        .where(BillingEventTable.claim_status == "rejected")
    )
    for row in rejected.scalars().all():
        flags.append({
            "flag_type": "rejected_claim",
            "severity": "red",
            "reference_id": row.invoice_id,
            "patient_id": row.patient_id,
            "service_date": row.service_date.isoformat(),
            "mbs_item": row.mbs_item,
            "amount": float(row.charged_amount),
            "detail": f"Claim rejected — {row.notes or 'review required'}",
        })

    # --- From PostgreSQL: overdue gap payments ---
    overdue_cutoff = date.today() - timedelta(days=14)
    overdue = await session.execute(
        select(BillingEventTable)
        .where(BillingEventTable.tenant_id == tenant_id)
        .where(BillingEventTable.outstanding > 0)
        .where(BillingEventTable.invoice_date < overdue_cutoff)
    )
    for row in overdue.scalars().all():
        days_overdue = (date.today() - row.invoice_date).days
        flags.append({
            "flag_type": "overdue_gap",
            "severity": "yellow",
            "reference_id": row.invoice_id,
            "patient_id": row.patient_id,
            "service_date": row.service_date.isoformat(),
            "mbs_item": row.mbs_item,
            "amount": float(row.outstanding),
            "detail": f"Patient gap unpaid — {days_overdue} days overdue",
        })

    # --- From Gentu API: unbilled appointments ---
    from adapters.mock_adapter import MockAdapter

    adapter = MockAdapter()  # TODO: resolve from tenant config
    appointments = await adapter.get_appointments(
        tenant_id,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today(),
    )

    # Get all billed appointment IDs from PostgreSQL
    billed_result = await session.execute(
        select(BillingEventTable.appointment_id)
        .where(BillingEventTable.tenant_id == tenant_id)
        .where(BillingEventTable.appointment_id.isnot(None))
    )
    billed_appt_ids = {row[0] for row in billed_result.all()}

    # Flag completed appointments with no matching billing record
    for appt in appointments:
        if appt.status.value == "completed" and appt.id not in billed_appt_ids:
            flags.append({
                "flag_type": "unbilled_appointment",
                "severity": "amber",
                "reference_id": appt.id,
                "patient_id": appt.patient_id,
                "service_date": appt.scheduled_start.date().isoformat(),
                "mbs_item": None,
                "amount": None,
                "detail": f"Completed {appt.appointment_type.name} with no matching invoice",
            })

    # Sort by severity: red first, then amber, then yellow
    severity_order = {"red": 0, "amber": 1, "yellow": 2}
    flags.sort(key=lambda f: severity_order.get(f["severity"], 3))

    return {
        "flags": flags,
        "source": "hybrid_db_and_api",
        "fetched_at": date.today().isoformat(),
    }
