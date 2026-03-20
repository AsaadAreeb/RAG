"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.api.routes import query, upload, sql, memory, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-load singleton models on startup
    from backend.services.embedding_service import EmbeddingService
    from backend.services.reranker_service import RerankerService
    EmbeddingService()   # loads once
    RerankerService()    # loads once
    yield


app = FastAPI(
    title="Enterprise RAG System",
    description="Production-grade RAG with Grok + Gemini + Local Models",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router, tags=["Query"])
app.include_router(upload.router, tags=["Ingestion"])
app.include_router(sql.router, tags=["SQL"])
app.include_router(memory.router, tags=["Memory"])
app.include_router(admin.router, tags=["Admin"])


@app.get("/health")
def health():
    return {"status": "ok"}