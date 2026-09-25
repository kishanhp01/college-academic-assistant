from pathlib import Path

from langchain_core.documents import Document

from app.configuration.settings import get_settings
from app.ingestion.indexer import load_index


class AcademicRetriever:
    def __init__(self, index_dir: str | Path | None = None, vector_store=None):
        self.vector_store = vector_store or load_index(index_dir)

    def retrieve(self, question: str, k: int | None = None) -> list[Document]:
        settings = get_settings()
        return self.vector_store.similarity_search(question, k=k or settings.retrieval_k)
