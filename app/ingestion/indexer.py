from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from app.configuration.settings import get_settings
from app.ingestion.chunking import split_documents
from app.ingestion.loader import load_directory


def create_embeddings(model_name: str | None = None) -> HuggingFaceEmbeddings:
    settings = get_settings()
    return HuggingFaceEmbeddings(model_name=model_name or settings.embedding_model)


def build_index(documents_dir: str | Path | None = None, index_dir: str | Path | None = None) -> int:
    settings = get_settings()
    documents = load_directory(documents_dir or settings.documents_dir)
    if not documents:
        raise ValueError("No PDF or TXT documents found. Add documents before building the index.")
    chunks = split_documents(documents, settings.chunk_size, settings.chunk_overlap)
    index_path = Path(index_dir or settings.index_dir)
    index_path.mkdir(parents=True, exist_ok=True)
    vector_store = FAISS.from_documents(chunks, create_embeddings())
    vector_store.save_local(str(index_path))
    return len(chunks)


def load_index(index_dir: str | Path | None = None) -> FAISS:
    settings = get_settings()
    index_path = Path(index_dir or settings.index_dir)
    if not (index_path / "index.faiss").exists():
        raise FileNotFoundError(f"No FAISS index found at {index_path}. Build it using python -m app.ingestion.cli.")
    return FAISS.load_local(str(index_path), create_embeddings(), allow_dangerous_deserialization=True)
