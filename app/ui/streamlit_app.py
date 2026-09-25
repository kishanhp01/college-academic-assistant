from datetime import date, timedelta
import streamlit as st

from app.ingestion.indexer import build_index
from app.study_plans.models import StudyPlanRequest, Subject
from app.study_plans.planner import generate_study_plan, modify_study_plan
from app.workflows.academic import build_academic_graph

st.set_page_config(page_title="College Academic Assistant", page_icon="🎓")
st.title("College Academic Assistant")
chat_tab, plan_tab = st.tabs(["Ask a question", "Study plan"])

with st.sidebar:
    st.subheader("College documents")
    st.caption("Place PDF and TXT files in data/documents, then build or refresh the local FAISS index.")
    if st.button("Build / refresh index"):
        with st.spinner("Reading documents and building index…"):
            try:
                st.success(f"Indexed {build_index()} text chunks.")
            except Exception as exc:
                st.error(str(exc))

with chat_tab:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("Retrieved sources"):
                    for source in message["sources"]:
                        st.markdown(f"**{source['label']}**\n\n{source['excerpt']}")
    if question := st.chat_input("Ask about academic rules, exams, internships, or FAQs"):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            try:
                result = build_academic_graph().invoke({"question": question})
                st.markdown(result["answer"])
                if result.get("sources"):
                    with st.expander("Retrieved sources"):
                        for source in result["sources"]:
                            st.markdown(f"**{source['label']}**\n\n{source['excerpt']}")
                st.session_state.messages.append({"role": "assistant", "content": result["answer"], "sources": result.get("sources")})
            except Exception as exc:
                st.error(str(exc))

with plan_tab:
    st.subheader("Create a study plan")
    count = st.number_input("Number of subjects", min_value=1, max_value=12, value=3)
    subjects = []
    for index in range(int(count)):
        with st.expander(f"Subject {index + 1}", expanded=index == 0):
            name = st.text_input("Name", value=f"Subject {index + 1}", key=f"name_{index}")
            difficulty = st.slider("Difficulty (1–5)", 1, 5, 3, key=f"difficulty_{index}")
            priority = st.slider("Priority (1–5)", 1, 5, 3, key=f"priority_{index}")
            subjects.append(Subject(name=name, difficulty=difficulty, priority=priority))
    exam_date = st.date_input("Exam date", value=date.today() + timedelta(days=14), min_value=date.today() + timedelta(days=1))
    hours = st.number_input("Available study hours per day", min_value=0.5, max_value=16.0, value=3.0, step=0.5)
    preferences = st.text_input("Preferences (breaks, study style, unavailable days)")
    if st.button("Generate study plan"):
        try:
            request = StudyPlanRequest(subjects=subjects, exam_date=exam_date,
                                       available_hours_per_day=hours, preferences=preferences)
            st.session_state.study_plan = generate_study_plan(request)
        except Exception as exc:
            st.error(str(exc))
    plan = st.session_state.get("study_plan")
    if plan:
        st.markdown("### Your plan")
        st.dataframe([session.model_dump() for session in plan.sessions], use_container_width=True)
        with st.expander("Modify this plan"):
            missed = st.text_input("Missed sessions / subjects (comma separated)")
            new_hours = st.number_input("Updated hours per day (0 keeps current)", min_value=0.0, max_value=16.0, value=0.0)
            new_exam = st.date_input("Updated exam date", value=plan.exam_date, key="updated_exam")
            priorities_text = st.text_area("Changed priorities, one Subject=1-5 per line")
            if st.button("Update plan"):
                priorities = {}
                for line in priorities_text.splitlines():
                    if "=" in line:
                        name, value = line.rsplit("=", 1)
                        priorities[name.strip()] = int(value.strip())
                st.session_state.study_plan = modify_study_plan(
                    plan, missed_sessions=[item.strip() for item in missed.split(",") if item.strip()],
                    available_hours_per_day=new_hours or None, exam_date=new_exam,
                    changed_priorities=priorities or None)
                st.rerun()
