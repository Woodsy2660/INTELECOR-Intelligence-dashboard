import pytest
from datetime import date
from adapters.mock_adapter import MockAdapter
from analytics.financial import FinancialAnalytics
from analytics.operations import OperationsAnalytics
from analytics.documents import DocumentsAnalytics


TENANT_ID = "tnt_roycardiology_001"
START = date(2026, 3, 15)
END = date(2026, 4, 7)


@pytest.fixture
def adapter():
    return MockAdapter()


@pytest.mark.asyncio
async def test_mock_adapter_loads_appointments(adapter):
    appointments = await adapter.get_appointments(TENANT_ID, START, END)
    assert len(appointments) > 0
    for appt in appointments:
        assert appt.tenant_id == TENANT_ID
        assert appt.patient_id is not None
        assert appt.status is not None


@pytest.mark.asyncio
async def test_mock_adapter_loads_billing(adapter):
    events = await adapter.get_billing_events(TENANT_ID, START, END)
    assert len(events) > 0
    for event in events:
        assert event.mbs_item is not None
        assert event.charged_amount >= 0


@pytest.mark.asyncio
async def test_mock_adapter_loads_documents(adapter):
    documents = await adapter.get_documents(TENANT_ID, START, END)
    assert len(documents) > 0
    for doc in documents:
        assert doc.status is not None


@pytest.mark.asyncio
async def test_mock_adapter_loads_referrals(adapter):
    referrals = await adapter.get_referrals(TENANT_ID, START, END)
    assert len(referrals) >= 0  # may be empty depending on date range


@pytest.mark.asyncio
async def test_financial_analytics(adapter):
    appointments = await adapter.get_appointments(TENANT_ID, START, END)
    billing = await adapter.get_billing_events(TENANT_ID, START, END)

    analytics = FinancialAnalytics()
    result = analytics.analyse(billing, appointments)

    assert result.total_billed >= 0
    assert result.total_received >= 0
    assert 0 <= result.collection_rate <= 100
    assert isinstance(result.by_billing_type, dict)
    assert isinstance(result.by_mbs_item, dict)


@pytest.mark.asyncio
async def test_operations_analytics(adapter):
    appointments = await adapter.get_appointments(TENANT_ID, START, END)

    analytics = OperationsAnalytics()
    result = analytics.analyse(appointments)

    summary = result["summary"]
    assert summary["total_scheduled"] >= 0
    assert 0 <= summary["completion_rate"] <= 100
    assert 0 <= summary["dna_rate"] <= 100


@pytest.mark.asyncio
async def test_documents_analytics(adapter):
    documents = await adapter.get_documents(TENANT_ID, START, END)

    analytics = DocumentsAnalytics()
    result = analytics.analyse(documents)

    assert result.total_unsigned >= 0
    assert result.avg_days_to_sign >= 0
    assert isinstance(result.by_age_bracket, dict)
    assert isinstance(result.unsigned_queue, list)


@pytest.mark.asyncio
async def test_leakage_detection(adapter):
    appointments = await adapter.get_appointments(TENANT_ID, START, END)
    billing = await adapter.get_billing_events(TENANT_ID, START, END)

    analytics = FinancialAnalytics()
    result = analytics.analyse(billing, appointments)

    for flag in result.leakage_flags:
        assert flag["flag_type"] in ("rejected_claim", "unbilled_appointment", "overdue_gap")
        assert flag["severity"] in ("red", "amber", "yellow")
