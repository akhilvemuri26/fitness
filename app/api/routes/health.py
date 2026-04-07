from fastapi import APIRouter

from app.core.config import get_settings
from app.services.connectors.whoop import WhoopClient

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/healthz/config")
def health_config() -> dict[str, object]:
    settings = get_settings()
    auth_url = None
    if settings.whoop_client_id and settings.whoop_redirect_uri:
        auth_url = WhoopClient.build_authorization_url(
            client_id=settings.whoop_client_id,
            redirect_uri=settings.whoop_redirect_uri,
            state="debugstate",
            scopes=[
                "offline",
                "read:profile",
                "read:body_measurement",
                "read:cycles",
                "read:recovery",
                "read:sleep",
                "read:workout",
            ],
        )
    return {
        "app_env": settings.app_env,
        "app_base_url": settings.app_base_url,
        "whoop_redirect_uri": settings.whoop_redirect_uri,
        "whoop_client_id_present": bool(settings.whoop_client_id),
        "enable_scheduler": settings.enable_scheduler,
        "whoop_auth_url_preview": auth_url,
    }
