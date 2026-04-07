import json
import logging
import secrets

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import get_settings
from app.db.session import get_db
from app.services.connectors.whoop import verify_whoop_signature
from app.services.sync import WhoopSyncService

router = APIRouter(tags=["whoop"])
logger = logging.getLogger(__name__)


@router.get("/connect/whoop/start")
def connect_whoop_start(db=Depends(get_db)) -> RedirectResponse:
    state = secrets.token_urlsafe(8)[:8]
    service = WhoopSyncService(db)
    return RedirectResponse(service.build_authorization_url(state))


@router.get("/connect/whoop/callback", response_class=HTMLResponse)
def connect_whoop_callback(code: str | None = None, error: str | None = None, db=Depends(get_db)) -> str:
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code")
    service = WhoopSyncService(db)
    try:
        account = service.connect_with_code(code)
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text.strip()
        try:
            response_payload = exc.response.json()
            response_text = json.dumps(response_payload)
        except ValueError:
            pass
        logger.warning(
            "WHOOP token exchange failed",
            extra={
                "status_code": exc.response.status_code,
                "response_text": response_text,
            },
        )
        detail = (
            f"WHOOP token exchange failed with {exc.response.status_code}. "
            "Most commonly this means the authorization code was already used, "
            "the Client ID / Client Secret pair is wrong, or the redirect URI does not match exactly."
        )
        return (
            "<html><body><h1>WHOOP connection failed</h1>"
            f"<p>{detail}</p>"
            "<ul>"
            "<li>Make sure the WHOOP app redirect URI exactly matches <code>http://127.0.0.1:8000/connect/whoop/callback</code>.</li>"
            "<li>Start the OAuth flow again from <code>/connect/whoop/start</code> and do not refresh the callback page.</li>"
            "<li>Verify the Client ID and Client Secret in your local <code>.env</code> come from the same WHOOP app.</li>"
            "</ul>"
            f"<p>WHOOP response: <code>{response_text or 'no response body'}</code></p>"
            "<p>After updating anything, restart the app and try connecting again.</p>"
            "</body></html>"
        )
    return f"<html><body><h1>WHOOP connected</h1><p>User: {account.external_user_id or 'connected'}</p><p>You can close this window.</p></body></html>"


@router.post("/webhooks/whoop", status_code=status.HTTP_202_ACCEPTED)
async def whoop_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
) -> dict:
    settings = get_settings()
    if not settings.enable_whoop_webhooks:
        return {
            "accepted": False,
            "ignored": True,
            "reason": "WHOOP webhooks are disabled; scheduled polling is the active sync strategy.",
        }

    body = await request.body()
    provided_signature = (
        request.headers.get("X-WHOOP-Signature")
        or request.headers.get("X-Hub-Signature-256")
        or request.headers.get("X-Signature")
    )
    if not verify_whoop_signature(body, provided_signature, settings.whoop_webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid WHOOP webhook signature")
    payload = await request.json()
    service = WhoopSyncService(db)
    background_tasks.add_task(service.process_webhook, payload)
    return {"accepted": True}
