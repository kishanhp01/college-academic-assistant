from pathlib import Path

import pytest

from app.ingestion import indexer
from app.retrieval.retriever import AcademicRetriever


class ControlledTestEmbeddings:
    """Tiny deterministic vectors for pipeline tests; no model download is needed."""

    vocabulary = {"apple": 0, "orchard": 1, "fruit": 2, "river": 3, "water": 4}

    @classmethod
    def _embed(cls, text: str) -> list[float]:
        vector = [0.0] * len(cls.vocabulary)
        for word in text.lower().replace(".", " ").split():
            if word in cls.vocabulary:
                vector[cls.vocabulary[word]] += 1.0
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def test_build_load_and_retrieve_controlled_text_with_faiss(tmp_path: Path, monkeypatch):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    (documents_dir / "controlled_test_fixture.txt").write_text(
        "A red apple grows in an orchard. Apples are fruit.", encoding="utf-8"
    )
    (documents_dir / "unrelated_test_fixture.txt").write_text(
        "A river carries water through a valley.", encoding="utf-8"
    )
    index_dir = tmp_path / "index"
    embeddings = ControlledTestEmbeddings()
    monkeypatch.setattr(indexer, "create_embeddings", lambda: embeddings)

    chunk_count = indexer.build_index(documents_dir, index_dir)

    assert chunk_count == 2
    assert (index_dir / "index.faiss").is_file()
    assert (index_dir / "index.pkl").is_file()

    persisted_store = indexer.load_index(index_dir)
    results = AcademicRetriever(vector_store=persisted_store).retrieve("apple orchard fruit", k=1)

    assert len(results) == 1
    assert "apple" in results[0].page_content.lower()
    assert results[0].metadata["source"] == "controlled_test_fixture.txt"


def test_build_index_rejects_empty_documents_directory(tmp_path: Path):
    documents_dir = tmp_path / "empty-documents"
    documents_dir.mkdir()

    with pytest.raises(ValueError, match="No PDF or TXT documents found"):
        indexer.build_index(documents_dir, tmp_path / "index")


def test_permission_blocked_hugging_face_uses_persisted_tfidf_fallback(tmp_path: Path, monkeypatch):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    (documents_dir / "test_fixture.txt").write_text(
        "TEST FIXTURE ONLY: a quartz prism reflects a violet beam.", encoding="utf-8"
    )
    monkeypatch.setattr(
        indexer,
        "create_embeddings",
        lambda: (_ for _ in ()).throw(PermissionError("blocked model cache")),
    )
    index_dir = tmp_path / "index"

    assert indexer.build_index(documents_dir, index_dir) == 1
    assert (index_dir / "index.faiss").is_file()
    assert (index_dir / "tfidf_vectorizer.joblib").is_file()

    store = indexer.load_index(index_dir)
    results = store.similarity_search("violet beam through quartz prism", k=1)
    assert results[0].metadata["source"] == "test_fixture.txt"
    assert "quartz prism" in results[0].page_content
