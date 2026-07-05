from fastapi.testclient import TestClient
from psycopg.errors import UndefinedTable

from src.app.main import app, countries_store


def test_list_countries_returns_actionable_503_when_bootstrap_is_missing(monkeypatch) -> None:
    def raise_missing_table(*args, **kwargs):
        raise UndefinedTable('relation "countries" does not exist')

    monkeypatch.setattr(countries_store, "get_countries", raise_missing_table)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/internal/locations/countries")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Database schema is not ready. Run the bootstrap step before calling this API.",
        "error_code": "database_bootstrap_incomplete",
    }


def test_health_keeps_200_and_reports_bootstrap_not_ready(monkeypatch) -> None:
    def raise_missing_table(*args, **kwargs):
        raise UndefinedTable('relation "countries" does not exist')

    monkeypatch.setattr(countries_store, "get_countries", raise_missing_table)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["bootstrap"] == {
        "ready": False,
        "error_code": "database_bootstrap_incomplete",
    }