from pathlib import Path
from langchain_core.documents import Document
from app.ingestion.loader import load_file
from app.ingestion.chunking import split_documents


def test_load_txt_adds_source(tmp_path: Path):
    path = tmp_path / "faq.txt"
    path.write_text("Exam registration closes Friday.", encoding="utf-8")
    docs = load_file(path)
    assert docs[0].page_content == "Exam registration closes Friday."
    assert docs[0].metadata["source"] == "faq.txt"


def test_chunking_preserves_source():
    docs = [Document(page_content="word " * 40, metadata={"source": "rules.txt"})]
    chunks = split_documents(docs, chunk_size=30, chunk_overlap=5)
    assert len(chunks) > 1
    assert all(chunk.metadata["source"] == "rules.txt" for chunk in chunks)
