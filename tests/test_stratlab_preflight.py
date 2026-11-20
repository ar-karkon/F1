"""No-LLM upstream preflight must never claim inference without weights."""
from __future__ import annotations

from apex_f1.integrations.stratlab import STRATLAB_COMMIT
from apex_f1.integrations.stratlab_preflight import audit_stratlab


def test_missing_upstream_is_explicit(tmp_path):
    result = audit_stratlab(tmp_path)
    assert result["status"] == "NOT_CHECKED_OUT"
    assert result["runtime_executed"] is False
    assert result["actual_model_predictions"] is False
    assert result["runtime_attempt_ready"] is False
    assert result["checkout_commit"] is None


def test_model_requirements_are_checked(tmp_path):
    path = tmp_path / "src/strategy/inference/engine.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        "def run_lap(race_state, laps_df, *, profile='rich'):\n"
        "    return None\n"
    )
    result = audit_stratlab(tmp_path)
    assert result["source_contract_verified"]
    assert "data/models/tire_degradation/routing_config.json" in (
        result["missing_prerequisites"]
    )
    assert result["pinned_commit"] == STRATLAB_COMMIT
    assert not result["runtime_executed"]
