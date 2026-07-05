from fastapi.testclient import TestClient

from src.app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "queue_configured" in payload
    assert "dlq_configured" in payload
