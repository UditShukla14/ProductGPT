import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.goodman_ratings import SOURCE_TYPE as GOODMAN_SOURCE_TYPE
from app.ingestion.registry import ingest_file
from app.ingestion.shopify_products import SOURCE_TYPE as SHOPIFY_SOURCE_TYPE
from app.schemas.common import IngestUploadResponse

router = APIRouter(prefix="/ingest", tags=["ingest"])

SUPPORTED_TYPES = {GOODMAN_SOURCE_TYPE, SHOPIFY_SOURCE_TYPE}


@router.post("/upload", response_model=IngestUploadResponse)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    source_type: str = Form(default=GOODMAN_SOURCE_TYPE),
    replace: bool = Form(default=True),
    db: Session = Depends(get_db),
) -> IngestUploadResponse:
    if source_type not in SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported source type: {source_type}")

    suffix = Path(file.filename or "upload.xlsx").suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        source = ingest_file(db, tmp_path, source_type=source_type, replace=replace)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return IngestUploadResponse(
        source_id=source.id,
        source_type=source.source_type,
        filename=source.filename,
        row_count=source.row_count,
        status=source.status,
    )
