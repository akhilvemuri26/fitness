from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.internal import router as internal_router
from app.api.routes.web import router as web_router
from app.api.routes.whoop import router as whoop_router

router = APIRouter()
router.include_router(health_router)
router.include_router(web_router)
router.include_router(whoop_router)
router.include_router(internal_router)

