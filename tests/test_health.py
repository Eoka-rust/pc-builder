from app.config import get_settings
from app.seed import COMPONENTS


def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["version"] == get_settings().app_version


def test_version_endpoint_returns_settings_value(client):
    assert client.get("/version").json() == {"version": get_settings().app_version}


def test_openapi_schema_is_built(client):
    schema = client.get("/openapi.json").json()

    assert schema["info"]["version"] == get_settings().app_version
    assert "/builds/check" in schema["paths"]


def test_seed_catalog_is_complete(catalog):
    assert len(catalog) == len(COMPONENTS)
