from fastapi import APIRouter

api_router = APIRouter()

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.versions import router as versions_router
from app.api.instances import router as instances_router
from app.api.mods import router as mods_router

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(versions_router)
api_router.include_router(instances_router)
api_router.include_router(mods_router)
