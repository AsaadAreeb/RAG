from __future__ import annotations
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from ingestion.pdf_processor import PDFProcessor
from backend.core.config import get_settings

router = APIRouter()
settings = get_settings()
_processor = PDFProcessor()


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    total_chunks: int
    new_chunks: int
    skipped_chunks: int
    message: str


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / (file.filename or "document.pdf")

    with save_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    result = await _processor.ingest(save_path)
    return UploadResponse(
        document_id=result.document_id,
        filename=result.filename,
        total_chunks=result.total_chunks,
        new_chunks=result.new_chunks,
        skipped_chunks=result.skipped_chunks,
        message=f"Ingested {result.new_chunks} new chunks "
                f"({result.skipped_chunks} unchanged, skipped).",
    )


@router.post("/reindex")
async def reindex(filename: str):
    path = Path(settings.upload_dir) / filename
    if not path.exists():
        raise HTTPException(404, f"{filename} not found in upload directory")
    result = await _processor.ingest(path)
    return result