"""Further offline evidence and safety checks for optional LLM adapter."""
from __future__ import annotations

import pytest

from apex_f1.llm import (
    LLMNotConfigured,
    LLMSettings,
    _validate_answer,
    snapshot_context,
)
from apex_f1.replay import CompletedLap, HistoricalRace


def test_snapshot_context_rejects_future_observations():
    historical = HistoricalRace(2024, 1, [CompletedLap("AAA", 1, 91, 91)])
    snapshot = historical.snapshot(1)
    snapshot["drivers"][0]["last_seen_session_seconds"] = 9999
    with pytest.raises(ValueError, match="Future"):
        snapshot_context(snapshot, "overview")


def test_no_full_race_summary_fields_in_model_context():
    historical = HistoricalRace(
        2024, 1, [
            CompletedLap("AAA", 1, 91, 91),
            CompletedLap("AAA", 2, 190, 99),
        ],
    )
    snapshot = historical.snapshot(1)
    snapshot["future_winner"] = "AAA"
    snapshot["summary"] = historical.summary()
    context = snapshot_context(snapshot, "rivals")
    assert "future_winner" not in context
    assert "summary" not in context
    assert "available_leader_laps" not in context
    assert context["last_observed_drivers"][0]["last_completed_lap"] == 1


def test_validation_rejects_nonexistent_evidence():
    with pytest.raises(Exception, match="evidence"):
        _validate_answer(
            {"brief": "An interpretation",
             "observations": [{"finding": "A claim", "evidence": ["D_FUTURE"]}],
             "unknowns": ["Not enough data"]},
            {"D_AAA"},
        )


def test_configuration_blocks_nonlocal_plain_http():
    config = LLMSettings(
        enabled=True, api_key="placeholder", model="model",
        base_url="http://example.com/v1", timeout_seconds=5,
    )
    with pytest.raises(LLMNotConfigured):
        config.endpoint()


def test_configuration_allows_local_http_only():
    config = LLMSettings(
        enabled=True, api_key="placeholder", model="model",
        base_url="http://localhost:9000/v1", timeout_seconds=5,
    )
    assert config.endpoint() == "http://localhost:9000/v1/chat/completions"
