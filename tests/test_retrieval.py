from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS

from app.retrieval.retriever import AcademicRetriever
from app.workflows.academic import build_academic_graph


class FakeStore:
    def similarity_search(self, query, k=4):
        return [Document(page_content=f"match for {query}", metadata={"source": "faq.txt"})][:k]


def test_retriever_requests_query_and_k():
    docs = AcademicRetriever(vector_store=FakeStore()).retrieve("internship", k=1)
    assert docs[0].metadata["source"] == "faq.txt"


class ControlledEmbeddings(Embeddings):
    """Deterministic test-only vectors; these do not download a model."""

    vocabulary = {
        "test": 0,
        "university": 1,
        "attendance": 2,
        "students": 3,
        "maintain": 4,
        "percent": 5,
        "network": 6,
        "packets": 7,
    }

    @classmethod
    def embed(cls, text: str) -> list[float]:
        vector = [0.0] * len(cls.vocabulary)
        for token in text.lower().replace("%", " percent ").split():
            token = token.strip(".,:;!?()")
            if token in cls.vocabulary:
                vector[cls.vocabulary[token]] += 1.0
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed(text)


def test_faiss_retrieves_relevant_test_data_without_external_embeddings():
    documents = [
        Document(
            page_content=(
                "TEST DATA ONLY: Fictional TEST UNIVERSITY asks students to maintain "
                "75 percent attendance. This is not a real college policy."
            ),
            metadata={"source": "test_data_only.txt"},
        ),
        Document(
            page_content="TEST DATA ONLY: A network sends packets between computers.",
            metadata={"source": "unrelated_test_data_only.txt"},
        ),
    ]
    store = FAISS.from_documents(documents, ControlledEmbeddings())

    results = AcademicRetriever(vector_store=store).retrieve(
        "What is the TEST UNIVERSITY attendance requirement?", k=1
    )

    assert len(results) == 1
    assert results[0].metadata["source"] == "test_data_only.txt"
    assert "TEST DATA ONLY" in results[0].page_content


def test_college_graph_routes_retrieved_test_data_into_grounded_answerer():
    document = Document(
        page_content=(
            "TEST DATA ONLY: Fictional TEST UNIVERSITY asks students to maintain "
            "75 percent attendance. This is not a real college policy."
        ),
        metadata={"source": "test_data_only.txt", "page": 0},
    )
    store = FAISS.from_documents([document], ControlledEmbeddings())
    retriever = AcademicRetriever(vector_store=store)
    seen = {}

    def fake_grounded_answer(question, context_documents):
        seen["question"] = question
        seen["documents"] = context_documents
        return f"Test answer based only on: {context_documents[0].page_content}"

    result = build_academic_graph(retriever, fake_grounded_answer).invoke(
        {"question": "What is the TEST UNIVERSITY attendance requirement?"}
    )

    assert result["route"] == "college"
    assert seen["question"] == "What is the TEST UNIVERSITY attendance requirement?"
    assert seen["documents"][0].metadata["source"] == "test_data_only.txt"
    assert "TEST DATA ONLY" in result["answer"]
    assert result["source"] == "college_documents"
    assert result["sources"][0]["label"] == "test_data_only.txt (page 1)"
