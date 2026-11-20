"""SovInfra compatibility preset and secret-safe API smoke checks."""
from __future__ import annotations

import io
import json

import pytest

from apex_f1.llm import LLMSettings, LLMUpstreamError, smoke_connection


def test_sovinfra_is_safe_default_and_stays_disabled(monkeypatch):
    for key in (
        "APEX_LLM_ENABLED",
        "APEX_LLM_MODEL",
        "APEX_LLM_BASE_URL",
        "APEX_LLM_API_KEY",
        "SOVINFRA_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    settings = LLMSettings.from_env()
    assert settings.enabled is False
    assert settings.configured() is False
    assert settings.base_url == "https://api.sovinfra.ai/v1"
    assert settings.model == "sovapi"
    assert settings.endpoint() == "https://api.sovinfra.ai/v1/chat/completions"


def test_private_sovinfra_key_fallback_does_not_escape_in_status(monkeypatch):
    monkeypatch.setenv("SOVINFRA_API_KEY", "only-in-private-env")
    monkeypatch.delenv("APEX_LLM_API_KEY", raising=False)
    monkeypatch.setenv("APEX_LLM_ENABLED", "true")
    monkeypatch.delenv("APEX_LLM_MODEL", raising=False)
    monkeypatch.delenv("APEX_LLM_BASE_URL", raising=False)
    settings = LLMSettings.from_env()
    assert settings.configured() is True
    assert settings.model == "sovapi"
    assert "only-in-private-env" not in json.dumps(settings.public_status())


def test_smoke_sends_minimal_text_only_and_never_logs_secret(monkeypatch):
    calls = []

    class MockResponse:
        def __enter__(self):
            return io.BytesIO(
                json.dumps({"choices": [{"message": {"content": "OK"}}]}).encode()
            )

        def __exit__(self, *_args):
            return False

    def fake_open(req, timeout):
        calls.append((req, timeout))
        return MockResponse()

    monkeypatch.setattr("apex_f1.llm.urlopen", fake_open)
    settings = LLMSettings(
        True, "private-placeholder-token", "sovapi", "https://api.sovinfra.ai/v1", 5
    )
    result = smoke_connection(settings)
    assert result["status"] == "OK"
    assert result["historical_data_sent"] is False
    assert result["endpoint_host"] == "api.sovinfra.ai"
    assert "private-placeholder-token" not in json.dumps(result)
    request, timeout = calls[0]
    request_body = json.loads(request.data)
    assert request.full_url == "https://api.sovinfra.ai/v1/chat/completions"
    assert request_body["model"] == "sovapi"
    assert request_body["messages"] == [
        {"role": "user", "content": "Reply with the single word OK."}
    ]
    assert "OpenF1" not in json.dumps(request_body)
    assert timeout == 5


def test_smoke_rejects_noncompliant_empty_response(monkeypatch):
    class MockResponse:
        def __enter__(self):
            return io.BytesIO(
                json.dumps({"choices": [{"message": {"content": ""}}]}).encode()
            )

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("apex_f1.llm.urlopen", lambda *_a, **_k: MockResponse())
    settings = LLMSettings(
        True, "private-placeholder-token", "sovapi", "https://api.sovinfra.ai/v1", 5
    )
    with pytest.raises(LLMUpstreamError, match="empty"):
        smoke_connection(settings)
