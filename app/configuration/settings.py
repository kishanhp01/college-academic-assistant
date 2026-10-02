from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_base_url: str = ""
    huggingface_api_key: str = ""
    huggingface_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    documents_dir: Path = Path("data/documents")
    index_dir: Path = Path("data/index")
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_k: int = 4

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
