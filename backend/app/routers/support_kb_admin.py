from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from .. import schemas
from ..ai.support_kb import (
    SUPPORT_KB_COLLECTION,
    build_support_kb_context,
    load_support_kb,
    rebuild_support_kb_index,
    save_support_kb,
)
from .auth import require_admin_token

router = APIRouter(
    prefix="/api/admin/support-kb",
    tags=["Admin Support KB"],
    dependencies=[Depends(require_admin_token)],
)


def _with_updated_at(data: dict) -> dict:
    payload = dict(data)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    return payload


@router.get("", response_model=schemas.SupportKBResponse)
def get_support_kb():
    data = load_support_kb()
    return schemas.SupportKBResponse(data=schemas.SupportKBPayload(**data))


@router.put("", response_model=schemas.SupportKBResponse)
def update_support_kb(payload: schemas.SupportKBPayload):
    normalized = _with_updated_at(payload.model_dump())
    saved = save_support_kb(normalized)
    rebuild_support_kb_index()
    return schemas.SupportKBResponse(message="updated", data=schemas.SupportKBPayload(**saved))


@router.post("/reindex", response_model=schemas.SupportKBReindexResponse)
def reindex_support_kb():
    article_count = rebuild_support_kb_index()
    return schemas.SupportKBReindexResponse(
        message="Support KB vector index rebuilt",
        article_count=article_count,
        collection_name=SUPPORT_KB_COLLECTION,
    )


@router.get("/preview-context", response_model=schemas.SupportKBContextPreviewResponse)
def preview_support_kb_context(query: str = Query(..., min_length=2, max_length=500)):
    context = build_support_kb_context(query, top_k=3)
    return schemas.SupportKBContextPreviewResponse(query=query, context=context)
