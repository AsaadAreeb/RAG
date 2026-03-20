"""PDF → Chunks → VectorStore with incremental (hash-based) indexing."""
from __future__ import annotations
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from ingestion.chunker import chunk_text, Chunk
from vectorstore.chroma_store import ChromaStore
from backend.services.embedding_service import EmbeddingService
from backend.core.config import get_settings

settings = get_settings()


@dataclass
class IngestionResult:
    document_id: str
    filename: str
    total_chunks: int
    new_chunks: int
    skipped_chunks: int


class PDFProcessor:
    def __init__(self) -> None:
        self.store = ChromaStore()
        self.embedder = EmbeddingService()

    def _extract_text(self, path: Path) -> str:
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
        return "\n\n".join(pages)

    def _doc_id(self, filename: str) -> str:
        return hashlib.sha256(filename.encode()).hexdigest()[:16]

    async def ingest(self, file_path: Path) -> IngestionResult:
        filename = file_path.name
        doc_id = self._doc_id(filename)
        text = self._extract_text(file_path)
        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)

        existing_hashes = self.store.get_existing_hashes(doc_id)
        new_chunks, skipped = [], 0

        for chunk in chunks:
            if chunk.content_hash in existing_hashes:
                skipped += 1
                continue
            new_chunks.append(chunk)

        if new_chunks:
            texts = [c.text for c in new_chunks]
            embeddings = self.embedder.embed_batch(texts)
            ids = [f"{doc_id}_{c.chunk_index}" for c in new_chunks]
            metadatas = [
                {
                    "doc_id": doc_id,
                    "filename": filename,
                    "chunk_index": c.chunk_index,
                    "content_hash": c.content_hash,
                    "token_count": c.token_count,
                }
                for c in new_chunks
            ]
            self.store.add(ids=ids, embeddings=embeddings,
                           documents=texts, metadatas=metadatas)

        return IngestionResult(
            document_id=doc_id,
            filename=filename,
            total_chunks=len(chunks),
            new_chunks=len(new_chunks),
            skipped_chunks=skipped,
        )
