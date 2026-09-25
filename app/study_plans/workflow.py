from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from app.study_plans.models import StudyPlan, StudyPlanRequest
from app.study_plans.planner import generate_study_plan


class PlanState(TypedDict, total=False):
    request: StudyPlanRequest
    plan: StudyPlan


def build_study_plan_graph(generator=generate_study_plan):
    graph = StateGraph(PlanState)
    graph.add_node("generate_plan", lambda state: {"plan": generator(state["request"])})
    graph.add_edge(START, "generate_plan")
    graph.add_edge("generate_plan", END)
    return graph.compile()
