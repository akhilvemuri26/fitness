from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def require_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if x_internal_token != settings.internal_sync_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal sync token",
        )


def require_mfp_bridge_token(x_mfp_bridge_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if x_mfp_bridge_token not in {
        settings.mfp_bridge_shared_token,
        settings.internal_sync_token,
    }:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MyFitnessPal bridge token",
        )
