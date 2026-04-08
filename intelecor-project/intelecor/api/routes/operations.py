from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.dependencies import get_current_tenant, get_session
from db.tables import AnalyticsResultTable

router = APIRouter()


@router.get("/summary")
async def get_operations_summary(
    tenant_id: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Operations screen: appointments, DNA rates, utilisation, referral sources."""
    result = await session.execute(
        select(AnalyticsResultTable)
        .where(AnalyticsResultTable.tenant_id == tenant_id)
        .where(AnalyticsResultTable.module == "operations")
        .order_by(AnalyticsResultTable.generated_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    return latest.results if latest else {}
