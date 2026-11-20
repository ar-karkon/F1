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
