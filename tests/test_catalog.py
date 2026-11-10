def test_categories_cover_whole_catalog(client):
    categories = client.get("/catalog/categories").json()["items"]
    total = client.get("/catalog/components").json()["total"]

    assert sum(item["count"] for item in categories) == total
    assert {item["category"] for item in categories} == {
        "cpu",
        "motherboard",
        "ram",
        "gpu",
        "psu",
        "case",
        "cooler",
        "storage",
    }


def test_filter_by_category(client):
    response = client.get("/catalog/components", params={"category": "cpu", "limit": 200})

    items = response.json()["items"]
    assert items
    assert {item["category"] for item in items} == {"cpu"}


def test_unknown_category_is_rejected(client):
    assert client.get("/catalog/components", params={"category": "keyboard"}).status_code == 422


def test_search_matches_brand_and_model(client):
    by_model = client.get("/catalog/components", params={"search": "b650"}).json()
    by_brand = client.get("/catalog/components", params={"search": "palit"}).json()

    assert by_model["total"] == 2
    assert by_brand["total"] == 2


def test_pagination_reports_total_and_slice(client):
    page = client.get("/catalog/components", params={"limit": 3, "offset": 2}).json()

    assert page["total"] == page["total"]
    assert len(page["items"]) == 3
    assert page["limit"] == 3
    assert page["offset"] == 2


def test_component_by_id_and_missing(client, catalog):
    component = catalog["Ryzen 5 7600"]

    found = client.get(f"/catalog/components/{component['id']}")
    assert found.status_code == 200
    assert found.json()["socket"] == "AM5"

    assert client.get("/catalog/components/999999").status_code == 404


def test_price_note_is_returned(client):
    page = client.get("/catalog/components").json()
    assert "не live-прайс" in page["price_note"]
