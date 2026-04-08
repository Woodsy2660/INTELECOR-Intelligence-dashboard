import os
import structlog
from celery import Celery
from celery.schedules import crontab

logger = structlog.get_logger()

_db_sync = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://intelecor:intelecor_dev@localhost:5432/intelecor",
)

BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    _db_sync.replace("postgresql://", "sqla+postgresql://"),
)
BACKEND_URL = os.environ.get(
    "CELERY_RESULT_BACKEND",
    _db_sync.replace("postgresql://", "db+postgresql://"),
)

celery_app = Celery("intelecor", broker=BROKER_URL, backend=BACKEND_URL)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Australia/Sydney",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # solo pool: no fork() — required on Windows, fine for single-practice scale
    worker_pool="solo",
)

celery_app.conf.beat_schedule = {
    "pull-and-analyse-every-15-min": {
        "task": "services.celery_app.run_pipeline",
        "schedule": crontab(minute="*/15"),
        "args": [],
    },
    "generate-daily-summary": {
        "task": "services.celery_app.generate_llm_summary",
        "schedule": crontab(hour=6, minute=30),  # 06:30 AEST
        "args": [],
    },
    "send-morning-digest": {
        "task": "services.celery_app.send_email_digest",
        "schedule": crontab(hour=7, minute=0),  # 07:00 AEST
        "args": [],
    },
}


@celery_app.task(name="services.celery_app.run_pipeline")
def run_pipeline(tenant_id: str | None = None):
    """Pull data from adapter, run analytics, save results to analytics_results."""
    import asyncio
    from db.base import async_session
    from adapters.mock_adapter import MockAdapter
    from services.pipeline import Pipeline

    tid = tenant_id or "tnt_roycardiology_001"

    async def _run():
        adapter = MockAdapter()
        pipeline = Pipeline(adapter)
        async with async_session() as session:
            return await pipeline.run_full(tid, session)

    logger.info("pipeline.task_start", tenant_id=tid)
    results = asyncio.run(_run())
    logger.info("pipeline.task_complete", tenant_id=tid)
    return {
        "status": "ok",
        "tenant_id": tid,
        "total_billed": results["financial"]["total_billed"],
        "appointments": results["operations"]["summary"]["total_scheduled"],
        "unsigned": results["documents"]["total_unsigned"],
    }


@celery_app.task(name="services.celery_app.generate_llm_summary")
def generate_llm_summary(tenant_id: str | None = None):
    """LLM summary — not configured (no API key in this environment)."""
    tid = tenant_id or "tnt_roycardiology_001"
    logger.info("llm_summary.not_configured", tenant_id=tid)
    return {"status": "not_configured", "message": "Set ANTHROPIC_API_KEY to enable"}


@celery_app.task(name="services.celery_app.send_email_digest")
def send_email_digest(tenant_id: str | None = None):
    """Email digest — not configured (no Resend API key in this environment)."""
    tid = tenant_id or "tnt_roycardiology_001"
    logger.info("email_digest.not_configured", tenant_id=tid)
    return {"status": "not_configured", "message": "Set RESEND_API_KEY to enable"}
