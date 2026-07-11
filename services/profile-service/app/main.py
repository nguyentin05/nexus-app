import logging

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.db import init_schema
from app.events import start_consumer, stop_consumer

LOGGER = logging.getLogger("profile-service")

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)
app.include_router(api_router)


@app.on_event("startup")
def startup() -> None:
    try:
        init_schema()
    except Exception:
        LOGGER.exception("database schema initialization failed; continuing startup")
    start_consumer()


@app.on_event("shutdown")
def shutdown() -> None:
    stop_consumer()
