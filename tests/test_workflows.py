from langchain_core.documents import Document
from app.workflows.academic import build_academic_graph


class FakeRetriever:
    def retrieve(self, query):
        return [Document(page_content="Deadline is May 1.", metadata={"source": "calendar.pdf", "page": 0})]


def test_academic_graph_analyzes_retrieves_and_answers():
    seen = {}
    def answer(query, docs):
        seen["query"] = query
        return f"According to {docs[0].metadata['source']}, deadline is May 1."
    result = build_academic_graph(FakeRetriever(), answer).invoke({"question": "  When is deadline?  "})
    assert result["analyzed_query"] == "When is deadline?"
    assert result["answer"].endswith("May 1.")
    assert result["sources"][0]["label"] == "calendar.pdf (page 1)"
