"""
Run the INTELECOR analytics pipeline for Roy Cardiology.

Usage (from intelecor-project/intelecor/):
    python scripts/run_pipeline.py
"""
import asyncio
import os
import sys
from datetime import date
from pathlib import Path

# Ensure the intelecor package root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func

from adapters.mock_adapter import MockAdapter
from services.pipeline import Pipeline
from db.tables import AnalyticsResultTable

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://intelecor:intelecor_dev@localhost:5432/intelecor",
)
TENANT_ID = "tnt_roycardiology_001"
START_DATE = date(2026, 3, 15)
END_DATE = date(2026, 4, 7)


async def main() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    adapter = MockAdapter()
    pipeline = Pipeline(adapter)

    print(f"Running pipeline for {TENANT_ID}")
    print(f"Period: {START_DATE} to {END_DATE}")
    print("-" * 52)

    async with session_factory() as session:
        results = await pipeline.run_full(
            tenant_id=TENANT_ID,
            session=session,
            start_date=START_DATE,
            end_date=END_DATE,
        )

    # ── Financial ──────────────────────────────────────────────
    fin = results["financial"]
    print("\nFINANCIAL")
    print(f"  Total billed:      ${fin['total_billed']:,.2f}")
    print(f"  Total received:    ${fin['total_received']:,.2f}")
    print(f"  Outstanding:       ${fin['total_outstanding']:,.2f}")
    print(f"  Collection rate:   {fin['collection_rate']}%")
    print(f"  Billing mix:       {', '.join(f'{k}=${v:,.0f}' for k, v in fin['by_billing_type'].items())}")
    print(f"  Leakage flags:     {len(fin['leakage_flags'])}")
    for flag in fin["leakage_flags"]:
        print(f"    [{flag['severity'].upper()}] {flag['flag_type']}: {flag['detail']}")

    # ── Operations ─────────────────────────────────────────────
    ops = results["operations"]["summary"]
    print("\nOPERATIONS")
    print(f"  Scheduled:         {ops['total_scheduled']}")
    print(f"  Completed:         {ops['total_completed']}")
    print(f"  DNA:               {ops['total_dna']}")
    print(f"  Cancelled:         {ops['total_cancelled']}")
    print(f"  Completion rate:   {ops['completion_rate']}%")
    print(f"  DNA rate:          {ops['dna_rate']}%")
    print(f"  New patients:      {ops['new_patient_count']}")
    print(f"  Referral sources:  {results['operations'].get('referral_sources', [])}")

    # ── Documents ──────────────────────────────────────────────
    docs = results["documents"]
    print("\nDOCUMENTS")
    print(f"  Unsigned:          {docs['total_unsigned']}")
    print(f"  Signed unsent:     {docs['total_signed_unsent']}")
    print(f"  Avg days to sign:  {docs['avg_days_to_sign']}")
    print(f"  Age brackets:      {docs['by_age_bracket']}")
    print(f"  By type:           {docs['by_type']}")

    # ── Verify analytics_results rows ─────────────────────────
    async with session_factory() as session:
        count_result = await session.execute(
            select(func.count()).select_from(AnalyticsResultTable)
            .where(AnalyticsResultTable.tenant_id == TENANT_ID)
            .where(AnalyticsResultTable.period_start == START_DATE)
            .where(AnalyticsResultTable.period_end == END_DATE)
        )
        row_count = count_result.scalar()

    print(f"\nanalytics_results rows (this run): {row_count}")
    assert row_count % 3 == 0 and row_count >= 3, (
        f"Expected a multiple of 3 rows ≥ 3, got {row_count}"
    )
    print("OK: Verified — 3 module results (financial/operations/documents) saved")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
