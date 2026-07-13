from fastapi import APIRouter

from app.api.routes import auth, health, metrics

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(metrics.router)
api_router.include_router(auth.router)
