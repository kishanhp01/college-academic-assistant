from langchain_core.documents import Document

from app.assistant.providers import create_chat_model

INSUFFICIENT_CONTEXT = "The provided college documents do not contain enough information to answer this question."


def format_sources(documents: list[Document]) -> list[dict[str, str]]:
    sources = []
    for document in documents:
        source = str(document.metadata.get("source", "Unknown document"))
        page = document.metadata.get("page")
        label = f"{source} (page {int(page) + 1})" if page is not None else source
        if not any(item["label"] == label for item in sources):
            sources.append({"label": label, "excerpt": document.page_content[:500]})
    return sources


def generate_answer(question: str, documents: list[Document], model=None) -> str:
    if not documents:
        return INSUFFICIENT_CONTEXT
    context = "\n\n".join(
        f"Source: {doc.metadata.get('source', 'Unknown document')}\n{doc.page_content}" for doc in documents
    )
    chat = model or create_chat_model()
    response = chat.invoke(
        "Answer the student's question using only the supplied college document excerpts. "
        "Do not infer or invent college rules. If evidence is insufficient, say so clearly. "
        "Mention the source filename (and page when available).\n\n"
        f"Question: {question}\n\nDocument excerpts:\n{context}"
    )
    return str(response.content)
