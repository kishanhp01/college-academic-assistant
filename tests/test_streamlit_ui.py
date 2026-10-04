from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app" / "ui" / "streamlit_app.py"


def test_streamlit_entrypoint_renders_demo_access_without_flask():
    app = AppTest.from_file(APP_PATH).run(timeout=30)

    assert not app.exception
    assert app.title[0].value == "College Academic Assistant"
    assert any("Demo access" in item.value for item in app.subheader)


def test_streamlit_study_planner_page_loads_for_demo_user():
    app = AppTest.from_file(APP_PATH)
    app.session_state["demo_user"] = "Demo Student"
    app.run(timeout=30)
    app.radio[0].set_value("Study Planner").run(timeout=30)

    assert not app.exception
    assert any(item.value == "Study Planner" for item in app.title)
