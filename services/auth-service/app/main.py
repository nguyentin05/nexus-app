import logging

from fastapi import FastAPI, Request, Response

from app.api.router import api_router
from app.core.config import settings
from app.core.db import init_schema
from app.metrics import metrics_middleware
from app.telemetry import configure_telemetry

LOGGER = logging.getLogger("auth-service")

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)


@app.middleware("http")
async def collect_metrics(request: Request, call_next) -> Response:
    response = await metrics_middleware(request, call_next)
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return response


app.include_router(api_router)
configure_telemetry(app, settings.PROJECT_NAME, settings.VERSION)


@app.on_event("startup")
def startup() -> None:
    try:
        init_schema()
    except Exception:
        LOGGER.exception("database schema initialization failed; continuing startup")
