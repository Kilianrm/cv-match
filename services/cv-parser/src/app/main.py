import logging

from fastapi import FastAPI

from src.shared.config import settings

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CV Parser Service",
    description="Queue-driven CV parser service",
    version="0.1.0",
)


@app.get("/health", summary="Service health check")
async def health() -> dict:
    return {
        "service": settings.service_name,
        "status": "ok",
        "queue_configured": bool(settings.parser_queue_url),
        "dlq_configured": bool(settings.parser_dlq_url),
    }
