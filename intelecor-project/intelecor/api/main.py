from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from api.config import get_settings
from api.routes import overview, financial, operations, documents

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
)

settings = get_settings()

app = FastAPI(
    title="INTELECOR API",
    description="Practice Intelligence Platform for Australian Medical Specialists",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router, prefix="/api/overview", tags=["Overview"])
app.include_router(financial.router, prefix="/api/financial", tags=["Financial"])
app.include_router(operations.router, prefix="/api/operations", tags=["Operations"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "intelecor-api"}
