def test_root_serves_configurator(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Конструктор сборки" in response.text


def test_static_assets_are_served(client):
    for path in ("/styles.css", "/app.js"):
        assert client.get(path).status_code == 200


def test_ui_does_not_shadow_api_routes(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/catalog/categories").status_code == 200
    assert client.get("/docs").status_code == 200
