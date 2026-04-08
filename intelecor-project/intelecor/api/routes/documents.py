from fastapi import APIRouter, Depends
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.dependencies import get_current_tenant, get_session
from db.tables import AnalyticsResultTable

router = APIRouter()


@router.get("/summary")
async def get_documents_summary(
    tenant_id: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """
    Documents screen: aggregate metrics from pre-computed analytics.
    Returns unsigned count, age brackets, backlog trend, avg signing time.
    Source: analytics_results table (no patient data).
    """
    result = await session.execute(
        select(AnalyticsResultTable)
        .where(AnalyticsResultTable.tenant_id == tenant_id)
        .where(AnalyticsResultTable.module == "documents")
        .order_by(AnalyticsResultTable.generated_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    return latest.results if latest else {}


@router.get("/queue")
async def get_unsigned_letter_queue(
    tenant_id: str = Depends(get_current_tenant),
):
    """
    Real-time pass-through to Gentu Letters API.

    Fetches current unsigned letters directly from Gentu at request time.
    Data passes through to the frontend and is never stored in PostgreSQL.
    This ensures zero patient-identifiable records in our database.

    For MVP with mock adapter: returns mock data from JSON files.
    For production: calls Gentu Letters API with tenant credentials.
    """
    from adapters.mock_adapter import MockAdapter

    # TODO: resolve adapter from tenant config (mock vs gentu)
    adapter = MockAdapter()

    # Fetch all documents — wide date range to get everything current
    documents = await adapter.get_documents(
        tenant_id,
        start_date=date.today() - timedelta(days=90),
        end_date=date.today(),
    )

    # Filter to unsigned only and format for the queue table
    unsigned = [d for d in documents if d.status.value == "unsigned"]
    unsigned.sort(key=lambda d: d.days_unsigned, reverse=True)

    return {
        "queue": [
            {
                "id": d.id,
                "patient_id": d.patient_id,
                "letter_type": d.letter_type.value,
                "recipient_name": f"{d.recipient.title or ''} {d.recipient.given_name} {d.recipient.family_name}".strip(),
                "recipient_practice": d.recipient.practice_name,
                "created_at": d.created_at.isoformat(),
                "days_unsigned": d.days_unsigned,
                "source": d.dictation_source.value if d.dictation_source else "unknown",
            }
            for d in unsigned
        ],
        "source": "gentu_api_realtime",
        "fetched_at": date.today().isoformat(),
    }
