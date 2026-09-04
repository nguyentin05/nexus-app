from fastapi import APIRouter

from app.api.routes import auth, benchmark, health, metrics
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(metrics.router)
api_router.include_router(auth.router)
if settings.AIOPS_BENCHMARK_ENABLED:
    api_router.include_router(benchmark.router)
