from fastapi import APIRouter

from app.api.v1 import health, hvac, ingest, recommendations

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(hvac.router)
api_router.include_router(recommendations.router)
api_router.include_router(ingest.router)
