from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings
from app.db.session import SessionLocal, create_schema_if_needed
from app.services.jobs import scheduler_service
from app.services.source_accounts import SourceAccountService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    create_schema_if_needed()
    db = SessionLocal()
    try:
        SourceAccountService(db).bootstrap_defaults()
    finally:
        db.close()
    if settings.enable_scheduler:
        scheduler_service.start()
    try:
        yield
    finally:
        scheduler_service.shutdown()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)
