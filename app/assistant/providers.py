from langchain_core.language_models.chat_models import BaseChatModel

from app.configuration.settings import get_settings


def create_chat_model() -> BaseChatModel:
    """Build the configured provider; provider dependencies stay isolated here."""
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider in {"openai", "openai_compatible"}:
        if not settings.llm_api_key:
            raise ValueError("Set LLM_API_KEY in .env before asking the assistant a question.")
        if provider == "openai_compatible" and not settings.llm_base_url:
            raise ValueError("Set LLM_BASE_URL for the openai_compatible provider.")
        from langchain_openai import ChatOpenAI

        options = {"model": settings.llm_model, "api_key": settings.llm_api_key}
        if settings.llm_base_url:
            options["base_url"] = settings.llm_base_url
        return ChatOpenAI(**options)
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        options = {"model": settings.llm_model}
        if settings.llm_base_url:
            options["base_url"] = settings.llm_base_url
        return ChatOllama(**options)
    raise ValueError(f"Unsupported LLM_PROVIDER '{settings.llm_provider}'. Choose openai, openai_compatible, or ollama.")
