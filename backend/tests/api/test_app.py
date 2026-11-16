"""Tests for the API application factory and the health endpoint."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

import motosphere
from motosphere.api.app import create_app
from motosphere.core.settings import Settings

HEALTH_PATH = "/api/health"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings()))


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get(HEALTH_PATH)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "status": "ok",
        "name": "MotoSphere",
        "version": motosphere.__version__,
    }


def test_health_is_never_cached(client: TestClient) -> None:
    response = client.get(HEALTH_PATH)

    assert response.headers.get("cache-control") == "no-store"


def test_health_rejects_other_methods(client: TestClient) -> None:
    for method in ("POST", "PUT", "DELETE"):
        response = client.request(method, HEALTH_PATH)
        assert response.status_code == 405, method


def test_unknown_path_returns_json_404(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert "detail" in response.json()


def test_openapi_schema_describes_health(client: TestClient) -> None:
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    schema: dict[str, Any] = response.json()
    assert schema["info"]["title"] == "MotoSphere API"
    assert schema["info"]["version"] == motosphere.__version__
    operation = schema["paths"][HEALTH_PATH]["get"]
    ok_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert ok_schema == {"$ref": "#/components/schemas/HealthResponse"}
    health_schema = schema["components"]["schemas"]["HealthResponse"]
    assert set(health_schema["required"]) == {"status", "name", "version"}


def test_docs_are_served_under_api(client: TestClient) -> None:
    response = client.get("/api/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_default_documentation_paths_are_not_served(client: TestClient) -> None:
    for path in ("/docs", "/redoc", "/openapi.json"):
        response = client.get(path)
        assert response.status_code == 404, path


def test_create_app_uses_given_settings() -> None:
    settings = Settings(api_port=9123)

    app = create_app(settings)

    assert app.state.settings is settings


def test_create_app_falls_back_to_get_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOTOSPHERE_API_PORT", "9456")

    app = create_app()

    assert app.state.settings.api_port == 9456


def test_create_app_returns_independent_applications() -> None:
    first = create_app(Settings())
    second = create_app(Settings())

    assert first is not second
    for app in (first, second):
        response = TestClient(app).get(HEALTH_PATH)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
