from typing import TypedDict

from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph

from app.assistant.answering import generate_answer
from app.retrieval.retriever import AcademicRetriever


class AcademicState(TypedDict, total=False):
    question: str
    analyzed_query: str
    documents: list[Document]
    answer: str
    sources: list[dict[str, str]]


def build_academic_graph(retriever=None, answer_fn=generate_answer):
    retriever = retriever or AcademicRetriever()

    def analyze(state: AcademicState) -> dict:
        return {"analyzed_query": state["question"].strip()}

    def retrieve(state: AcademicState) -> dict:
        return {"documents": retriever.retrieve(state["analyzed_query"])}

    def answer(state: AcademicState) -> dict:
        from app.assistant.answering import format_sources

        docs = state.get("documents", [])
        return {"answer": answer_fn(state["analyzed_query"], docs), "sources": format_sources(docs)}

    graph = StateGraph(AcademicState)
    graph.add_node("query_analysis", analyze)
    graph.add_node("retrieval", retrieve)
    graph.add_node("answer_generation", answer)
    graph.add_edge(START, "query_analysis")
    graph.add_edge("query_analysis", "retrieval")
    graph.add_edge("retrieval", "answer_generation")
    graph.add_edge("answer_generation", END)
    return graph.compile()
