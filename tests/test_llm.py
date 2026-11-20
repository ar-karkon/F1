"""All tests are offline; no real API keys or external requests are used."""
from __future__ import annotations

import io
import json
from urllib.error import URLError

import pytest
from fastapi.testclient import TestClient

from apex_f1.api import app
from apex_f1.llm import LLMNotConfigured, LLMSettings, LLMUpstreamError, explain_snapshot
from apex_f1.replay import CompletedLap, HistoricalRace

client = TestClient(app)


def race():
    return HistoricalRace(
        2024, 1,
        [
            CompletedLap("AAA", 1, 90, 90, "MEDIUM", 1, 1, 1),
            CompletedLap("BBB", 1, 94, 94, "HARD", 1, 1, 2),
            CompletedLap("AAA", 2, 180, 90, "MEDIUM", 2, 1, 1),
            CompletedLap("BBB", 2, 191, 97, "WET", 1, 2, 2),
        ],
    )


def fake_settings():
    return LLMSettings(True, "test-token-not-real", "test-model", "https://llm.example/v1", 5)


def ok_message():
    return {
        "choices": [{"message": {"content": json.dumps({
            "brief": "AAA completed its second lap first.",
            "observations": [{"finding": "BBB has only one observed completion.",
                              "evidence": ["D_BBB"]}],
            "unknowns": ["Other cars may not have completed lap two yet."],
        })}}],
    }


def test_llm_disabled_by_default(monkeypatch):
    monkeypatch.delenv("APEX_LLM_ENABLED", raising=False)
    monkeypatch.setenv("APEX_LLM_API_KEY", "dont-show")
    state = client.get("/api/v1/llm/status")
    assert state.status_code == 200
    assert state.json()["configured"] is False
    assert "dont-show" not in state.text
    with pytest.raises(LLMNotConfigured):
        explain_snapshot(race().snapshot(2))


def test_invalid_url_blocks_credential_leak():
    cfg = LLMSettings(True, "not-real", "test", "http://llm.example/v1", 5)
    assert cfg.configured() is False
    with pytest.raises(LLMNotConfigured):
        cfg.endpoint()


def test_llm_receives_only_current_as_of_snapshot(monkeypatch):
    captured = {}

    class MockResponse:
        def __enter__(self):
            return io.BytesIO(json.dumps(ok_message()).encode())

        def __exit__(self, *_args):
            return False

    def fake_open(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return MockResponse()

    monkeypatch.setattr("apex_f1.llm.urlopen", fake_open)
    result = explain_snapshot(race().snapshot(2), settings=fake_settings())
    context = json.loads(json.loads(captured["request"].data)["messages"][1]["content"])
    bbb = next(x for x in context["last_observed_drivers"] if x["driver"] == "BBB")
    assert bbb["last_completed_lap"] == 1
    assert bbb["last_known_compound"] == "HARD"
    assert "WET" not in json.dumps(context)
    assert context["cutoff_session_seconds"] == 180
    assert "full_race" not in json.dumps(context)
    assert result["mode"] == "LLM_HISTORICAL_COMMENTARY_UNVALIDATED"
    assert captured["timeout"] == 5
    assert result["observations"][0]["evidence"] == ["D_BBB"]


def test_invalid_evidence_is_rejected(monkeypatch):
    wrong = ok_message()
    wrong["choices"][0]["message"]["content"] = json.dumps({
        "brief": "Test",
        "observations": [{"finding": "Not visible", "evidence": ["D_CCC"]}],
        "unknowns": ["Unknown"],
    })

    class MockResponse:
        def __enter__(self):
            return io.BytesIO(json.dumps(wrong).encode())

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("apex_f1.llm.urlopen", lambda *_a, **_k: MockResponse())
    with pytest.raises(LLMUpstreamError, match="evidence"):
        explain_snapshot(race().snapshot(2), settings=fake_settings())


def test_provider_error_does_not_expose_secrets(monkeypatch):
    def failed(*_args, **_kwargs):
        raise URLError("secret-header-should-not-leak")

    monkeypatch.setattr("apex_f1.llm.urlopen", failed)
    with pytest.raises(LLMUpstreamError) as exc:
        explain_snapshot(race().snapshot(2), settings=fake_settings())
    assert "secret-header" not in str(exc.value)


def test_http_api_requires_explicit_opt_in(monkeypatch, tmp_path):
    monkeypatch.setenv("F1_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("APEX_LLM_ENABLED", raising=False)
    history = race()
    history.save(tmp_path / "race-2024-round-1-R.json")
    response = client.post("/api/v1/historical/2024/1/brief/2", json={"focus": "rivals"})
    assert response.status_code == 503


def test_http_api_rejects_unknown_focus(monkeypatch):
    monkeypatch.delenv("APEX_LLM_ENABLED", raising=False)
    response = client.post("/api/v1/historical/2024/1/brief/2", json={"focus": "bets"})
    assert response.status_code == 422


def test_http_api_returns_mocked_grounded_brief(monkeypatch, tmp_path):
    monkeypatch.setenv("F1_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APEX_LLM_ENABLED", "true")
    monkeypatch.setenv("APEX_LLM_API_KEY", "fake-secret")
    monkeypatch.setenv("APEX_LLM_MODEL", "test-model")
    monkeypatch.setenv("APEX_LLM_BASE_URL", "https://llm.example/v1")
    race().save(tmp_path / "race-2024-round-1-R.json")

    class MockResponse:
        def __enter__(self):
            return io.BytesIO(json.dumps(ok_message()).encode())

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("apex_f1.llm.urlopen", lambda *_a, **_k: MockResponse())
    response = client.post("/api/v1/historical/2024/1/brief/2", json={"focus": "rivals"})
    assert response.status_code == 200
    assert response.json()["leader_lap"] == 2
    assert response.json()["brief"] == "AAA completed its second lap first."
    assert "fake-secret" not in response.text
