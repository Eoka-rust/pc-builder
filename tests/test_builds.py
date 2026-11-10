def build_payload(catalog: dict[str, dict], **overrides) -> dict:
    models = {
        "cpu": "Ryzen 5 7600",
        "motherboard": "B650 GAMING PLUS WIFI",
        "ram": "FURY Beast DDR5 16GB 5600",
        "gpu": "GeForce RTX 4060 Dual 8GB",
        "psu": "System Power 10 650W",
        "case": "i3 Neo",
        "cooler": "AK400",
        "storage": "NV2 1TB M.2",
    }
    models.update(overrides)
    items = [{"component_id": catalog[model]["id"], "quantity": 1} for model in models.values()]
    items[2]["quantity"] = 2
    return {"name": "Сборка для теста", "items": items}


def test_check_returns_compatible_report(client, catalog):
    response = client.post("/builds/check", json=build_payload(catalog))

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["errors"] == []
    assert body["estimated_power_w"] == 245
    assert body["recommended_psu_w"] == 350


def test_created_build_returns_items_and_total(client, catalog):
    payload = build_payload(catalog)
    response = client.post("/builds", json=payload)

    assert response.status_code == 201, response.text
    build = response.json()
    assert build["name"] == payload["name"]
    assert len(build["items"]) == 8
    ram = next(item for item in build["items"] if item["component"]["category"] == "ram")
    assert ram["quantity"] == 2
    assert build["total_price_rub"] > 0

    fetched = client.get(f"/builds/{build['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["total_price_rub"] == build["total_price_rub"]


def test_incompatible_build_is_rejected_with_reasons(client, catalog):
    payload = build_payload(
        catalog,
        motherboard="B550M DS3H",
        ram="Viper Steel DDR4 16GB 3200",
    )
    response = client.post("/builds", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "incompatible_build"
    assert "socket_mismatch" in {error["code"] for error in detail["errors"]}
    assert client.get("/builds").json()["total"] == 0


def test_gpu_and_case_mismatch_is_reported(client, catalog):
    payload = build_payload(catalog, gpu="GeForce RTX 4070 Super JetStream 12GB", case="T8")
    response = client.post("/builds/check", json=payload)

    assert response.status_code == 200
    assert "gpu_too_long" in {error["code"] for error in response.json()["errors"]}


def test_unknown_component_returns_404(client, catalog):
    payload = build_payload(catalog)
    payload["items"][0]["component_id"] = 999999

    response = client.post("/builds", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "component_not_found"


def test_empty_build_is_rejected_by_schema(client):
    assert client.post("/builds", json={"name": "x", "items": []}).status_code == 422
    assert (
        client.post("/builds", json={"name": "", "items": [{"component_id": 1}]}).status_code == 422
    )


def test_list_and_delete_build(client, catalog):
    created = client.post("/builds", json=build_payload(catalog)).json()

    listing = client.get("/builds").json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == created["id"]

    assert client.delete(f"/builds/{created['id']}").status_code == 204
    assert client.get(f"/builds/{created['id']}").status_code == 404
