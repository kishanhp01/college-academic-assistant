from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.assistant import providers


def test_huggingface_provider_is_constructed_without_network_call(monkeypatch):
    settings = SimpleNamespace(
        llm_provider="huggingface",
        huggingface_api_key="test-token",
        huggingface_model="Qwen/Qwen2.5-1.5B-Instruct",
    )
    endpoint = object()
    chat_model = object()
    endpoint_factory = Mock(return_value=endpoint)
    chat_factory = Mock(return_value=chat_model)

    monkeypatch.setattr(providers, "get_settings", lambda: settings)
    monkeypatch.setattr(
        "langchain_huggingface.HuggingFaceEndpoint", endpoint_factory
    )
    monkeypatch.setattr("langchain_huggingface.ChatHuggingFace", chat_factory)

    result = providers.create_chat_model()

    assert result is chat_model
    endpoint_factory.assert_called_once_with(
        repo_id="Qwen/Qwen2.5-1.5B-Instruct",
        task="text-generation",
        huggingfacehub_api_token="test-token",
        max_new_tokens=512,
        do_sample=False,
    )
    chat_factory.assert_called_once_with(llm=endpoint)


def test_huggingface_provider_requires_api_key_without_exposing_it(monkeypatch):
    settings = SimpleNamespace(
        llm_provider="huggingface",
        huggingface_api_key="",
        huggingface_model="Qwen/Qwen2.5-1.5B-Instruct",
    )
    monkeypatch.setattr(providers, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="HUGGINGFACE_API_KEY") as error:
        providers.create_chat_model()

    assert "test-token" not in str(error.value)
