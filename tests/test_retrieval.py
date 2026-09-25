from langchain_core.documents import Document

from app.retrieval.retriever import AcademicRetriever


class FakeStore:
    def similarity_search(self, query, k=4):
        return [Document(page_content=f"match for {query}", metadata={"source": "faq.txt"})][:k]


def test_retriever_requests_query_and_k():
    docs = AcademicRetriever(vector_store=FakeStore()).retrieve("internship", k=1)
    assert docs[0].metadata["source"] == "faq.txt"
