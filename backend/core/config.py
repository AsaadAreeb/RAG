from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API keys
    xai_api_key: str = ""
    gemini_api_key: str = ""

    # Model names
    grok_model: str = "grok-3"
    gemini_model: str = "gemini-2.5-flash"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Chroma
    chroma_path: str = "./storage/chroma"
    chroma_collection: str = "rag_documents"

    # SQL
    database_url: str = "sqlite+aiosqlite:///./storage/app.db"

    # Embedding / reranker
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Chunking
    chunk_size: int = 600
    chunk_overlap: int = 100

    # Retrieval
    top_k: int = 5
    next_k: int = 8
    bm25_weight: float = 0.3
    dense_weight: float = 0.7

    # Rate limiting
    rate_limit_rpm: int = 20
    requests_per_user_per_min: int = 10

    # Security
    secret_key: str = "change_me"

    # Storage
    upload_dir: str = "./storage/uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()
