from fastapi.testclient import TestClient

from apex_f1.api import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard():
    response = client.get("/")
    assert response.status_code == 200
    assert "SYNTHETIC DEMO" in response.text


def test_strategy_endpoint():
    result = client.post(
        "/api/v1/strategy/evaluate",
        json={"current_lap": 25, "trials": 40, "seed": 123},
    )
    assert result.status_code == 200
    assert result.json()["trials"] == 40


def test_invalid_lap_rejected():
    result = client.post(
        "/api/v1/strategy/evaluate",
        json={"current_lap": 60, "total_laps": 57},
    )
    assert result.status_code == 422


def test_integration_dashboard_page():
    response = client.get("/integrations")
    assert response.status_code == 200
    assert "Real upstream code." in response.text
    assert "TUM" in response.text


def test_replay_page_is_served_without_local_data():
    response = client.get("/replay")
    assert response.status_code == 200
    assert "Rewind the race." in response.text


def test_replay_summary_missing_responds_404(monkeypatch, tmp_path):
    monkeypatch.setenv("F1_DATA_DIR", str(tmp_path))
    response = client.get("/api/v1/historical/2024/1/summary")
    assert response.status_code == 404
    assert "import-race" in response.json()["detail"]


def test_replay_snapshot_timeline_is_strict(monkeypatch, tmp_path):
    from apex_f1.historical_import import race_file
    from apex_f1.replay import CompletedLap, HistoricalRace

    monkeypatch.setenv("F1_DATA_DIR", str(tmp_path))
    sample = HistoricalRace(2024, 1, [
        CompletedLap("AAA", 1, 91, 91, "MEDIUM", 1, 1, 1),
        CompletedLap("BBB", 1, 94, 94, "HARD", 1, 1, 2),
        CompletedLap("AAA", 2, 180, 89, "MEDIUM", 2, 1, 1),
        CompletedLap("BBB", 2, 190, 96, "SOFT", 2, 2, 2),
    ])
    sample.save(race_file(2024, 1))
    response = client.get("/api/v1/historical/2024/1/snapshot/2")
    assert response.status_code == 200
    result = response.json()
    bbb = next(x for x in result["drivers"] if x["driver"] == "BBB")
    assert bbb["last_completed_lap"] == 1
    assert bbb["last_known_compound"] == "HARD"
    assert result["cutoff_session_seconds"] == 180
