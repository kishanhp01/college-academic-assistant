from pathlib import Path

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader


def load_file(path: str | Path) -> list[Document]:
    """Load one supported document and attach its filename as source metadata."""
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        documents = PyPDFLoader(str(file_path)).load()
    elif suffix == ".txt":
        text = file_path.read_text(encoding="utf-8")
        documents = [Document(page_content=text, metadata={})]
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Use PDF or TXT.")
    for document in documents:
        document.metadata["source"] = file_path.name
    return documents


def load_directory(directory: str | Path) -> list[Document]:
    """Load PDF and TXT documents from a directory."""
    root = Path(directory)
    documents = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".pdf", ".txt"}:
            documents.extend(load_file(path))
    return documents
