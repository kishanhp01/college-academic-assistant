from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def test_frontend_pages_and_local_assets_exist():
    expected_pages = {
        "login.html",
        "register.html",
        "dashboard.html",
        "chatbot.html",
        "study_planner.html",
    }
    assert expected_pages.issubset({path.name for path in FRONTEND.glob("*.html")})

    for page in FRONTEND.glob("*.html"):
        content = page.read_text(encoding="utf-8")
        refs = re.findall(r'(?:src|href)="(\./[^"#?]+)', content)
        for reference in refs:
            assert (FRONTEND / reference.removeprefix("./")).is_file(), (
                f"{page.name} references missing local asset {reference}"
            )


def test_api_client_matches_existing_backend_routes_and_uses_session_cookies():
    client = (FRONTEND / "js" / "api.js").read_text(encoding="utf-8")
    routes = (ROOT / "app" / "api" / "routes.py").read_text(encoding="utf-8")

    for path in (
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/me",
        "/api/chat",
        "/api/chat/history",
        "/api/study-plan",
        "/api/study-plan/modify",
    ):
        assert path in client
        assert path.removeprefix("/api") in routes

    assert 'credentials: "include"' in client


def test_frontend_contains_no_provider_secrets_or_fake_chat_answer():
    for path in FRONTEND.rglob("*"):
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            assert "hf_" not in content
            assert "sk-" not in content
            assert "HUGGINGFACE_API_KEY=" not in content
    chat = (FRONTEND / "js" / "chatbot.js").read_text(encoding="utf-8")
    assert "api.chat(question)" in chat
    assert '"The answer is' not in chat
