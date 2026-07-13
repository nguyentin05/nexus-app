from fastapi import APIRouter

from app.api.routes import health, metrics, profile

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(metrics.router)
api_router.include_router(profile.router)
