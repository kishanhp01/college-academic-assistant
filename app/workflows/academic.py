from typing import TypedDict

from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph

from app.assistant.answering import generate_answer
from app.assistant.general_answering import answer_general_question
from app.assistant.router import route_question
from app.retrieval.retriever import AcademicRetriever


class AcademicState(TypedDict, total=False):
    question: str
    analyzed_query: str
    route: str
    documents: list[Document]
    answer: str
    sources: list[dict[str, str]]
    source: str


def build_academic_graph(
    retriever=None,
    answer_fn=generate_answer,
    general_answer_fn=None,
    router_fn=None,
):
    general_answer_fn = general_answer_fn or answer_general_question
    router_fn = router_fn or route_question
    active_retriever = retriever

    def route(state: AcademicState) -> dict:
        question = state["question"].strip()
        return {
            "question": question,
            "analyzed_query": question,
            "route": router_fn(question),
        }

    def college_rag(state: AcademicState) -> dict:
        nonlocal active_retriever
        if active_retriever is None:
            active_retriever = AcademicRetriever()

        from app.assistant.answering import format_sources

        documents = active_retriever.retrieve(state["analyzed_query"])
        answer = answer_fn(state["analyzed_query"], documents)
        return {
            "documents": documents,
            "answer": answer,
            "sources": format_sources(documents),
            "source": "college_documents",
        }

    def general(state: AcademicState) -> dict:
        result = general_answer_fn(state["question"])
        return {
            "answer": result["answer"],
            "source": result.get("source", "general_llm"),
            "sources": [],
        }

    def choose_branch(state: AcademicState) -> str:
        return state["route"]

    graph = StateGraph(AcademicState)
    graph.add_node("question_router", route)
    graph.add_node("college_rag", college_rag)
    graph.add_node("general", general)
    graph.add_edge(START, "question_router")
    graph.add_conditional_edges(
        "question_router",
        choose_branch,
        {"college": "college_rag", "general": "general"},
    )
    graph.add_edge("college_rag", END)
    graph.add_edge("general", END)
    return graph.compile()
