from fastapi import APIRouter, Depends
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from api.dependencies import get_current_tenant, get_session
from db.tables import AnalyticsResultTable, BillingEventTable

router = APIRouter()


@router.get("/summary")
async def get_overview_summary(
    tenant_id: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(AnalyticsResultTable)
        .where(AnalyticsResultTable.tenant_id == tenant_id)
        .order_by(AnalyticsResultTable.generated_at.desc())
        .limit(3)
    )
    latest = {r.module: r.results for r in result.scalars().all()}

    action_items = await _build_action_items(session, tenant_id)

    return {
        "headline": {
            "revenue_this_week": latest.get("financial", {}).get("total_received", 0),
            "patients_seen": latest.get("operations", {}).get("summary", {}).get("total_completed", 0),
            "outstanding_revenue": latest.get("financial", {}).get("total_outstanding", 0),
            "unsigned_letters": latest.get("documents", {}).get("total_unsigned", 0),
        },
        "financial": latest.get("financial"),
        "operations": latest.get("operations"),
        "documents": latest.get("documents"),
        "action_items": action_items,
    }


async def _build_action_items(session: AsyncSession, tenant_id: str) -> list[dict]:
    items = []

    # Rejected claims — from billing_events table
    result = await session.execute(
        select(func.count())
        .select_from(BillingEventTable)
        .where(BillingEventTable.tenant_id == tenant_id)
        .where(BillingEventTable.claim_status == "rejected")
    )
    rejected_count = result.scalar() or 0
    if rejected_count > 0:
        items.append({
            "type": "rejected_claim",
            "title": f"{rejected_count} Rejected Claim{'s' if rejected_count > 1 else ''}",
            "subtitle": "Requires rebilling",
            "severity": "red",
            "link": "/financial",
        })

    # Overdue gap payments — from billing_events table
    overdue_cutoff = date.today() - timedelta(days=14)
    result = await session.execute(
        select(func.count(), func.sum(BillingEventTable.outstanding))
        .select_from(BillingEventTable)
        .where(BillingEventTable.tenant_id == tenant_id)
        .where(BillingEventTable.outstanding > 0)
        .where(BillingEventTable.invoice_date < overdue_cutoff)
    )
    row = result.one()
    overdue_count = row[0] or 0
    overdue_amount = float(row[1] or 0)
    if overdue_count > 0:
        items.append({
            "type": "unpaid_gap",
            "title": f"{overdue_count} Unpaid Gap Invoice{'s' if overdue_count > 1 else ''}",
            "subtitle": f"Past due > 14 days (${overdue_amount:,.2f})",
            "severity": "yellow",
            "link": "/financial",
        })

    # Unsigned letters + expiring referrals — from latest analytics_results
    # (no direct table queries needed, the counts are in the pre-computed results)
    result = await session.execute(
        select(AnalyticsResultTable.results)
        .where(AnalyticsResultTable.tenant_id == tenant_id)
        .where(AnalyticsResultTable.module == "documents")
        .order_by(AnalyticsResultTable.generated_at.desc())
        .limit(1)
    )
    doc_results = result.scalar_one_or_none()
    if doc_results:
        unsigned = doc_results.get("total_unsigned", 0)
        if unsigned > 0:
            items.append({
                "type": "unsigned_letters",
                "title": f"{unsigned} Letters Unsigned",
                "subtitle": "Batch signing available",
                "severity": "amber" if unsigned <= 15 else "red",
                "link": "/documents",
            })

    return items