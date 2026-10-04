from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import streamlit as st
from pydantic import ValidationError

from app.configuration.settings import get_settings
from app.study_plans.models import StudyPlan, StudyPlanRequest, Subject
from app.study_plans.planner import modify_study_plan
from app.study_plans.workflow import build_study_plan_graph


st.set_page_config(page_title="College Academic Assistant", page_icon="🎓", layout="wide")


@st.cache_resource
def get_academic_graph():
    from app.workflows.academic import build_academic_graph

    return build_academic_graph()


@st.cache_resource
def get_study_plan_graph():
    return build_study_plan_graph()


def current_settings():
    try:
        return get_settings()
    except Exception:
        return None


def document_status(settings: Any) -> tuple[int, bool]:
    documents_dir = Path(getattr(settings, "documents_dir", "data/documents"))
    index_dir = Path(getattr(settings, "index_dir", "data/index"))
    try:
        document_count = sum(
            1
            for path in documents_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in {".pdf", ".txt"}
        )
    except OSError:
        document_count = 0
    return document_count, (index_dir / "index.faiss").is_file()


def initialize_session_state() -> None:
    defaults = {
        "demo_user": "",
        "chat_transcript": [],
        "chat_history": [],
        "study_plan": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar(settings: Any, documents_found: int, index_available: bool) -> str:
    with st.sidebar:
        st.title("Academic assistant")
        st.caption("Local student demo")
        st.divider()
        st.subheader("Knowledge base status")
        st.write(f"Documents found: **{documents_found}**")
        st.write(
            "FAISS index: **Available**" if index_available else "FAISS index: **Not available**"
        )
        st.write(f"LLM provider: **{getattr(settings, 'llm_provider', 'Not configured')}**")
        if st.button("Build / refresh document index", use_container_width=True):
            if not documents_found:
                st.error(
                    "No PDF or TXT documents were found. Add approved college documents "
                    "to data/documents/ first."
                )
            else:
                try:
                    from app.ingestion.indexer import build_index

                    with st.spinner("Reading documents and building the index…"):
                        chunk_count = build_index()
                    st.success(f"Index ready: {chunk_count} text chunks.")
                    st.cache_resource.clear()
                    st.rerun()
                except Exception:
                    st.error(
                        "The document index could not be built. Check that the documents are "
                        "readable and the embedding model is available."
                    )

        st.divider()
        if st.session_state.demo_user:
            st.caption(f"Demo access: {st.session_state.demo_user}")
            page = st.radio(
                "Go to",
                ["Dashboard", "AI Chatbot", "Chat History", "Study Planner"],
                label_visibility="collapsed",
            )
            if st.button("Exit demo", use_container_width=True):
                st.session_state.demo_user = ""
                st.session_state.chat_transcript = []
                st.session_state.chat_history = []
                st.session_state.study_plan = None
                st.rerun()
            return page
        st.caption("Enter a name to open this local demo.")
        return "Login / user access"


def render_access_page() -> None:
    st.title("College Academic Assistant")
    st.subheader("Demo access")
    st.info(
        "This is a simple demo identity, not secure authentication. Do not enter a password "
        "or sensitive personal information. Your chat history is kept only in this Streamlit session."
    )
    with st.form("demo_access_form"):
        username = st.text_input("Name", max_chars=80).strip()
        enter_demo = st.form_submit_button("Continue", type="primary")
    if enter_demo:
        if not username:
            st.error("Enter a name to continue.")
        else:
            st.session_state.demo_user = username
            st.rerun()


def render_dashboard(documents_found: int, index_available: bool, settings: Any) -> None:
    st.title(f"Welcome, {st.session_state.demo_user}")
    st.write("Choose a section from the sidebar to ask a question or plan your study time.")
    first, second, third = st.columns(3)
    first.metric("College documents", documents_found)
    second.metric("FAISS index", "Ready" if index_available else "Not built")
    third.metric("LLM provider", getattr(settings, "llm_provider", "Not configured"))
    if not index_available:
        st.info(
            "The college knowledge base is not available yet. Add approved documents to "
            "data/documents/ and build the index from the sidebar. General questions can "
            "still use the configured LLM."
        )


def render_chatbot() -> None:
    st.title("AI Chatbot")
    st.caption("Ask an academic question or a general study question.")

    for item in st.session_state.chat_transcript:
        with st.chat_message(item["role"]):
            if item["role"] == "assistant" and item.get("error"):
                st.error(item["content"])
            else:
                st.markdown(item["content"])
                if item.get("route") or item.get("source"):
                    labels = [
                        str(value).replace("_", " ").title()
                        for value in (item.get("route"), item.get("source"))
                        if value
                    ]
                    st.caption(" · ".join(labels))
                if item.get("sources"):
                    with st.expander("Retrieved college sources"):
                        for source in item["sources"]:
                            st.markdown(f"**{source.get('label', 'College document')}**")
                            if source.get("excerpt"):
                                st.write(source["excerpt"])

    if question := st.chat_input("Type your question"):
        st.session_state.chat_transcript.append({"role": "user", "content": question})
        try:
            with st.spinner("Preparing an answer…"):
                result = get_academic_graph().invoke({"question": question})
            answer = result.get("answer")
            if not isinstance(answer, str):
                raise RuntimeError("The assistant returned an invalid response.")
            route = result.get("route")
            source = result.get("source")
            sources = result.get("sources", [])
            if not isinstance(sources, list):
                sources = []
            st.session_state.chat_transcript.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "route": route,
                    "source": source,
                    "sources": sources,
                }
            )
            st.session_state.chat_history.append(
                {
                    "question": question,
                    "answer": answer,
                    "route": route,
                    "source": source,
                    "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "sources": sources,
                }
            )
        except FileNotFoundError:
            message = (
                "College knowledge base is not available yet. Please add the college "
                "documents and build the index."
            )
            st.session_state.chat_transcript.append(
                {"role": "assistant", "content": message, "error": True}
            )
        except ValueError:
            message = (
                "The language model is not configured. Set the selected provider and its "
                "required settings in .env, then restart the app."
            )
            st.session_state.chat_transcript.append(
                {"role": "assistant", "content": message, "error": True}
            )
        except Exception:
            message = "The assistant could not complete that request. Please try again later."
            st.session_state.chat_transcript.append(
                {"role": "assistant", "content": message, "error": True}
            )
        st.rerun()


def render_chat_history() -> None:
    st.title("Chat History")
    st.caption("Successful conversations from this Streamlit session only.")
    history = list(reversed(st.session_state.chat_history))
    if not history:
        st.info("There are no saved answers in this session yet.")
        return
    for item in history:
        with st.container(border=True):
            st.caption(item["created_at"])
            st.markdown(f"**You asked:** {item['question']}")
            st.markdown(item["answer"])
            details = [
                str(value).replace("_", " ").title()
                for value in (item.get("route"), item.get("source"))
                if value
            ]
            if details:
                st.caption(" · ".join(details))
            if item.get("sources"):
                with st.expander("Retrieved sources"):
                    for source in item["sources"]:
                        st.markdown(f"**{source.get('label', 'College document')}**")
                        if source.get("excerpt"):
                            st.write(source["excerpt"])


def render_plan(plan: StudyPlan) -> None:
    st.subheader("Your study plan")
    st.write(f"Exam date: **{plan.exam_date.isoformat()}**")
    if plan.assumptions:
        with st.expander("Plan notes"):
            for note in plan.assumptions:
                st.write(f"- {note}")
    if plan.sessions:
        st.dataframe(
            [session.model_dump(mode="json") for session in plan.sessions],
            hide_index=True,
        )
    else:
        st.info("This plan has no remaining study sessions.")


def _parse_changed_priorities(text: str) -> dict[str, int]:
    priorities: dict[str, int] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        if "=" not in line:
            raise ValueError("Use one Subject=1-to-5 priority per line.")
        name, value = line.rsplit("=", 1)
        name = name.strip()
        try:
            priority = int(value.strip())
        except ValueError:
            raise ValueError("Priority values must be whole numbers from 1 to 5.") from None
        if not name or not 1 <= priority <= 5:
            raise ValueError("Each changed priority must have a subject name and a value from 1 to 5.")
        priorities[name] = priority
    return priorities


def render_study_planner() -> None:
    st.title("Study Planner")
    st.caption("Create and revise a plan using the existing study-planning workflow.")
    count = st.number_input(
        "Number of subjects", min_value=1, max_value=12, value=1, step=1, key="plan_subject_count"
    )
    with st.form("study_plan_form"):
        subjects: list[Subject] = []
        for index in range(int(count)):
            with st.expander(f"Subject {index + 1}", expanded=index == 0):
                name = st.text_input("Subject name", key=f"plan_subject_name_{index}").strip()
                difficulty = st.slider(
                    "Difficulty (1 = easier, 5 = harder)", 1, 5, 3,
                    key=f"plan_difficulty_{index}",
                )
                priority = st.slider("Priority (1–5)", 1, 5, 3, key=f"plan_priority_{index}")
                subjects.append(Subject(name=name, difficulty=difficulty, priority=priority))
        exam_date = st.date_input(
            "Exam date", value=date.today() + timedelta(days=14),
            min_value=date.today() + timedelta(days=1), key="plan_exam_date",
        )
        available_hours = st.number_input(
            "Available study hours per day", min_value=0.25, max_value=24.0,
            value=2.0, step=0.25, key="plan_hours",
        )
        preferences = st.text_area("Preferences (optional)", key="plan_preferences")
        submitted = st.form_submit_button("Generate study plan", type="primary")

    if submitted:
        if any(not subject.name for subject in subjects):
            st.error("Enter a name for each subject.")
        else:
            try:
                request = StudyPlanRequest(
                    subjects=subjects,
                    exam_date=exam_date,
                    available_hours_per_day=available_hours,
                    preferences=preferences.strip(),
                )
                result = get_study_plan_graph().invoke({"request": request})
                st.session_state.study_plan = result["plan"]
            except (ValidationError, ValueError):
                st.error("Check the subject details, study hours, and exam date, then try again.")
            except Exception:
                st.error("The study plan could not be generated. Please try again.")

    plan = st.session_state.study_plan
    if not isinstance(plan, StudyPlan):
        return

    render_plan(plan)
    st.subheader("Modify this plan")
    with st.form("modify_plan_form"):
        missed_text = st.text_input("Missed subjects (comma separated)")
        new_hours = st.number_input(
            "New available hours per day (0 keeps the current amount)",
            min_value=0.0, max_value=24.0, value=0.0, step=0.25,
        )
        change_exam_date = st.checkbox("Change the exam date")
        new_exam_date = None
        if change_exam_date:
            new_exam_date = st.date_input(
                "New exam date", value=max(plan.exam_date, date.today() + timedelta(days=1)),
                min_value=date.today() + timedelta(days=1), key="modified_exam_date",
            )
        changed_priorities_text = st.text_area(
            "Changed priorities (one Subject=1-5 per line)",
        )
        modify_submitted = st.form_submit_button("Update study plan")

    if modify_submitted:
        try:
            priorities = _parse_changed_priorities(changed_priorities_text)
            missed = [item.strip() for item in missed_text.split(",") if item.strip()]
            st.session_state.study_plan = modify_study_plan(
                plan,
                missed_sessions=missed or None,
                available_hours_per_day=new_hours or None,
                exam_date=new_exam_date,
                changed_priorities=priorities or None,
            )
            st.rerun()
        except ValueError as error:
            st.error(str(error))
        except Exception:
            st.error("The study plan could not be updated. Check your changes and try again.")


def main() -> None:
    initialize_session_state()
    settings = current_settings()
    documents_found, index_available = document_status(settings)
    page = render_sidebar(settings, documents_found, index_available)

    if not st.session_state.demo_user:
        render_access_page()
        return
    if page == "Dashboard":
        render_dashboard(documents_found, index_available, settings)
    elif page == "AI Chatbot":
        render_chatbot()
    elif page == "Chat History":
        render_chat_history()
    elif page == "Study Planner":
        render_study_planner()


main()
