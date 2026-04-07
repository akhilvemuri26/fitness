from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.dashboard import DashboardService
from app.services.sync import HevySyncService, WhoopSyncService

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def dashboard(
    request: Request,
    selected_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
):
    dashboard_service = DashboardService(db)
    context = dashboard_service.build_dashboard_context(selected_date=selected_date)
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=context,
    )


@router.get("/connections")
def connections(request: Request, db: Session = Depends(get_db)):
    dashboard_service = DashboardService(db)
    context = dashboard_service.build_connections_context()
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="connections.html",
        context=context,
    )


@router.post("/actions/sync/hevy")
def trigger_hevy_sync(db: Session = Depends(get_db)) -> RedirectResponse:
    HevySyncService(db).sync()
    return RedirectResponse(url="/connections", status_code=303)


@router.post("/actions/sync/whoop")
def trigger_whoop_sync(db: Session = Depends(get_db)) -> RedirectResponse:
    WhoopSyncService(db).reconcile()
    return RedirectResponse(url="/connections", status_code=303)


@router.get("/privacy")
def privacy(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        context={"request": request, "title": "Privacy Policy — Fitness Hub"},
    )
