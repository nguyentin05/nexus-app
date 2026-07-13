from fastapi import APIRouter, Response

from app.core.config import settings
from app.metrics import render_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(
        render_metrics(settings.PROJECT_NAME, settings.VERSION),
        media_type="text/plain; version=0.0.4",
    )
