"""Lightweight contract/error tests; do not require checked-out submodules."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apex_f1.api import app
from apex_f1.integrations.stratlab import probe_stratlab
from apex_f1.integrations.tum_basic import UpstreamUnavailable, compare_tum_example, probe_tum

client = TestClient(app)


def test_missing_upstream_returns_actionable_message(tmp_path):
    with pytest.raises(UpstreamUnavailable, match="git submodule update --init"):
        compare_tum_example(root=tmp_path)


def test_tum_validation_rejects_duplicates_without_executing(tmp_path):
    path = tmp_path / "race-simulation"
    (path / "racesim_basic/src").mkdir(parents=True)
    (path / "racesim_basic/input/parameters").mkdir(parents=True)
    (path / "racesim_basic/src/calc_racetimes_basic.py").touch()
    (path / "racesim_basic/input/parameters/pars_YasMarina_2017.ini").touch()
    with pytest.raises(ValueError, match="distinct"):
        compare_tum_example(pit_laps=[18, 18], root=path)


def test_stratlab_contract_detects_missing_source(tmp_path):
    result = probe_stratlab(root=tmp_path)
    assert result["status"] == "NOT_CHECKED_OUT"
    assert result["runtime_executed"] is False


def test_stratlab_contract_detects_expected_arguments(tmp_path):
    file = Path(tmp_path / "src/strategy/inference/engine.py")
    file.parent.mkdir(parents=True)
    file.write_text("def run_lap(race_state, laps_df, *, profile='no-llm'):\n    pass\n")
    assert probe_stratlab(tmp_path)["source_contract_verified"] is True


def test_status_endpoint_never_claims_execution():
    result = client.get("/api/v1/integrations/status")
    assert result.status_code == 200
    assert result.json()["stratlab"]["runtime_executed"] is False


def test_tum_endpoint_missing_submodule_returns_503(monkeypatch, tmp_path):
    monkeypatch.setenv("APEX_F1_UPSTREAM_DIR", str(tmp_path))
    response = client.post("/api/v1/integrations/tum/compare", json={"pit_laps": [18, 25]})
    assert response.status_code == 503
    assert "submodule" in response.json()["detail"].lower()


def test_tum_endpoint_pydantic_rejects_invalid_compound():
    response = client.post(
        "/api/v1/integrations/tum/compare", json={"start_compound": "PINK"}
    )
    assert response.status_code == 422


def test_tum_status_does_not_require_optional_numpy(tmp_path):
    assert probe_tum(tmp_path)["source_present"] is False
