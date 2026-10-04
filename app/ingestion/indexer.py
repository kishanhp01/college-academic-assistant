from pathlib import Path
import json

import joblib

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from app.configuration.settings import get_settings
from app.ingestion.chunking import split_documents
from app.ingestion.loader import load_directory
from app.retrieval.tfidf_embeddings import TfidfEmbeddings


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
    try:
        embeddings = create_embeddings()
        vector_store = FAISS.from_documents(chunks, embeddings)
    except PermissionError:
        # Hugging Face Hub may fail its Windows cache/symlink probe even when
        # the selected cache directory itself is writable. Fall back offline.
        embeddings = TfidfEmbeddings.fit([chunk.page_content for chunk in chunks])
        vector_store = FAISS.from_documents(chunks, embeddings)
        joblib.dump(embeddings.vectorizer, index_path / "tfidf_vectorizer.joblib")
        (index_path / "embedding_backend.json").write_text(
            json.dumps({"backend": "tfidf"}), encoding="utf-8"
        )
        vector_store.save_local(str(index_path))
    else:
        vector_store.save_local(str(index_path))
        (index_path / "embedding_backend.json").unlink(missing_ok=True)
        (index_path / "tfidf_vectorizer.joblib").unlink(missing_ok=True)
    return len(chunks)


def load_index(index_dir: str | Path | None = None) -> FAISS:
    settings = get_settings()
    index_path = Path(index_dir or settings.index_dir)
    if not (index_path / "index.faiss").exists():
        raise FileNotFoundError(f"No FAISS index found at {index_path}. Build it using python -m app.ingestion.cli.")
    backend_file = index_path / "embedding_backend.json"
    if backend_file.is_file():
        backend = json.loads(backend_file.read_text(encoding="utf-8")).get("backend")
        if backend != "tfidf":
            raise ValueError("The FAISS index declares an unsupported embedding backend.")
        vectorizer_path = index_path / "tfidf_vectorizer.joblib"
        if not vectorizer_path.is_file():
            raise FileNotFoundError("The persisted TF-IDF vectorizer is missing from the index.")
        embeddings = TfidfEmbeddings(joblib.load(vectorizer_path))
    else:
        embeddings = create_embeddings()
    return FAISS.load_local(
        str(index_path), embeddings, allow_dangerous_deserialization=True
    )
