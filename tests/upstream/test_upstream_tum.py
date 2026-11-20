"""These tests run ONLY in upstream-integration CI, with real submodules checked out."""
from pathlib import Path

from fastapi.testclient import TestClient

from apex_f1.api import app
from apex_f1.integrations.paths import upstream_path
from apex_f1.integrations.stratlab import probe_stratlab
from apex_f1.integrations.tum_basic import compare_tum_example, probe_tum

client = TestClient(app)


def test_upstream_checkout_present_and_stratlab_contract():
    tum = probe_tum()
    stratlab = probe_stratlab()
    assert tum["source_present"], "TUM submodule missing; initialize it in upstream CI"
    assert stratlab["source_present"], "F1-StratLab submodule missing"
    assert stratlab["source_contract_verified"], "Pinned run_lap contract changed"
    assert stratlab["runtime_executed"] is False  # This is not an agent smoke test.
    assert Path(upstream_path("race-simulation") / "LICENSE").is_file()


def test_real_tum_basic_source_executes_with_original_example():
    result = compare_tum_example([18, 25, 32])
    assert result["runtime_executed"] is True
    assert result["mode"] == "UPSTREAM_TUM_2017_REFERENCE_EXAMPLE"
    assert result["race_laps"] == 55
    assert len(result["strategies"]) == 3
    assert all(row["modelled_full_race_seconds"] > 0 for row in result["strategies"])
    assert result["strategies"][0]["delta_to_best_seconds"] == 0
    assert {row["pit_inlap_index"] for row in result["strategies"]} == {18, 25, 32}


def test_tum_api_matches_reproducible_direct_run():
    direct = compare_tum_example([15, 24])
    response = client.post("/api/v1/integrations/tum/compare", json={"pit_laps": [24, 15]})
    assert response.status_code == 200, response.text
    assert response.json() == direct
