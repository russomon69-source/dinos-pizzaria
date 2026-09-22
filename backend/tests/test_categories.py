from fastapi import status


def test_public_list_categories_empty(client):
    response = client.get("/api/v1/categories")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_admin_create_category_success(client, admin_token_headers):
    payload = {
        "name": "Pizzas Tradicionais",
        "slug": "pizzas-tradicionais",
        "order": 1,
        "is_active": True,
    }
    response = client.post("/api/v1/categories", json=payload, headers=admin_token_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Pizzas Tradicionais"
    assert data["slug"] == "pizzas-tradicionais"
    assert data["order"] == 1
    assert data["is_active"] is True
    assert "id" in data


def test_create_category_unauthorized(client):
    payload = {
        "name": "Pizzas Especiais",
        "slug": "pizzas-especiais",
        "order": 2,
        "is_active": True,
    }
    response = client.post("/api/v1/categories", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_category_duplicate_rejected(client, admin_token_headers):
    payload = {
        "name": "Bebidas",
        "slug": "bebidas",
        "order": 3,
        "is_active": True,
    }
    r1 = client.post("/api/v1/categories", json=payload, headers=admin_token_headers)
    assert r1.status_code == status.HTTP_201_CREATED

    r2 = client.post("/api/v1/categories", json=payload, headers=admin_token_headers)
    assert r2.status_code == status.HTTP_400_BAD_REQUEST


def test_get_category_by_id(client, admin_token_headers):
    payload = {
        "name": "Sobremesas",
        "slug": "sobremesas",
        "order": 4,
        "is_active": True,
    }
    create_res = client.post("/api/v1/categories", json=payload, headers=admin_token_headers)
    cat_id = create_res.json()["id"]

    res = client.get(f"/api/v1/categories/{cat_id}")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["id"] == cat_id
    assert res.json()["name"] == "Sobremesas"


def test_get_category_not_found(client):
    res = client.get("/api/v1/categories/99999")
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_update_category(client, admin_token_headers):
    payload = {
        "name": "Calzones",
        "slug": "calzones",
        "order": 5,
        "is_active": True,
    }
    create_res = client.post("/api/v1/categories", json=payload, headers=admin_token_headers)
    cat_id = create_res.json()["id"]

    update_payload = {"name": "Calzones Especiais", "order": 10}
    up_res = client.put(f"/api/v1/categories/{cat_id}", json=update_payload, headers=admin_token_headers)
    assert up_res.status_code == status.HTTP_200_OK
    data = up_res.json()
    assert data["name"] == "Calzones Especiais"
    assert data["order"] == 10


def test_toggle_category_active(client, admin_token_headers):
    payload = {
        "name": "Bordas Recheadas",
        "slug": "bordas-recheadas",
        "order": 6,
        "is_active": True,
    }
    create_res = client.post("/api/v1/categories", json=payload, headers=admin_token_headers)
    cat_id = create_res.json()["id"]

    toggle_res = client.patch(f"/api/v1/categories/{cat_id}/toggle-active", headers=admin_token_headers)
    assert toggle_res.status_code == status.HTTP_200_OK
    assert toggle_res.json()["is_active"] is False

    # Inactive category should not appear in public active_only list
    pub_res = client.get("/api/v1/categories?active_only=true")
    assert not any(c["id"] == cat_id for c in pub_res.json())

    # But appears when active_only=false
    all_res = client.get("/api/v1/categories?active_only=false")
    assert any(c["id"] == cat_id for c in all_res.json())


def test_delete_category(client, admin_token_headers):
    payload = {
        "name": "Temporários",
        "slug": "temporarios",
        "order": 99,
        "is_active": True,
    }
    create_res = client.post("/api/v1/categories", json=payload, headers=admin_token_headers)
    cat_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/categories/{cat_id}", headers=admin_token_headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    get_res = client.get(f"/api/v1/categories/{cat_id}")
    assert get_res.status_code == status.HTTP_404_NOT_FOUND
