from fastapi import APIRouter, Depends

from app.core.security import require_internal_token, require_mfp_bridge_token
from app.db.session import get_db
from app.schemas.mfp import MfpSyncBatchRequest
from app.services.mfp_ingest import MfpIngestService
from app.services.sync import HevySyncService, WhoopSyncService

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/mfp-sync-batch", dependencies=[Depends(require_mfp_bridge_token)])
def mfp_sync_batch(payload: MfpSyncBatchRequest, db=Depends(get_db)) -> dict:
    service = MfpIngestService(db)
    return service.ingest_batch(payload)


@router.post("/sync/hevy", dependencies=[Depends(require_internal_token)])
def sync_hevy(db=Depends(get_db)) -> dict:
    service = HevySyncService(db)
    return service.sync()


@router.post("/sync/whoop/reconcile", dependencies=[Depends(require_internal_token)])
def sync_whoop(db=Depends(get_db)) -> dict:
    service = WhoopSyncService(db)
    return service.reconcile()
