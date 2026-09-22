from fastapi import status


def test_public_list_combos_empty(client):
    response = client.get("/api/v1/combos")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_admin_create_combo_success(client, admin_token_headers):
    payload = {
        "title": "Combo Jurássico Família",
        "description": "2 Pizzas Grandes + 1 Refri 2L + 1 Borda Recheada",
        "price": "119.90",
        "image_url": "/static/uploads/combo-familia.webp",
        "is_active": True,
        "is_promo_of_day": True,
    }
    res = client.post("/api/v1/combos", json=payload, headers=admin_token_headers)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["title"] == "Combo Jurássico Família"
    assert data["price"] == "119.90"
    assert data["is_promo_of_day"] is True
    assert "id" in data


def test_create_combo_unauthorized(client):
    payload = {
        "title": "Combo Bronto Casal",
        "price": "79.90",
    }
    res = client.post("/api/v1/combos", json=payload)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_promo_combos(client, admin_token_headers):
    # Create non-promo combo
    client.post(
        "/api/v1/combos",
        json={"title": "Combo Individual", "price": "39.90", "is_promo_of_day": False},
        headers=admin_token_headers,
    )
    # Create promo of the day combo
    promo_res = client.post(
        "/api/v1/combos",
        json={"title": "Combo Rex do Dia", "price": "89.90", "is_promo_of_day": True},
        headers=admin_token_headers,
    )
    promo_id = promo_res.json()["id"]

    res = client.get("/api/v1/combos/promos")
    assert res.status_code == status.HTTP_200_OK
    promos = res.json()
    assert len(promos) >= 1
    assert any(c["id"] == promo_id for c in promos)
    assert all(c["is_promo_of_day"] is True for c in promos)


def test_update_combo(client, admin_token_headers):
    create_res = client.post(
        "/api/v1/combos",
        json={"title": "Combo Dino Kids", "price": "45.00"},
        headers=admin_token_headers,
    )
    combo_id = create_res.json()["id"]

    update_payload = {"price": "48.00", "title": "Super Dino Kids"}
    up_res = client.put(f"/api/v1/combos/{combo_id}", json=update_payload, headers=admin_token_headers)
    assert up_res.status_code == status.HTTP_200_OK
    assert up_res.json()["price"] == "48.00"
    assert up_res.json()["title"] == "Super Dino Kids"


def test_toggle_combo_active_and_promo(client, admin_token_headers):
    create_res = client.post(
        "/api/v1/combos",
        json={"title": "Combo Pterodáctilo", "price": "65.00"},
        headers=admin_token_headers,
    )
    combo_id = create_res.json()["id"]

    # Toggle promo
    promo_res = client.patch(f"/api/v1/combos/{combo_id}/toggle-promo", headers=admin_token_headers)
    assert promo_res.status_code == status.HTTP_200_OK
    assert promo_res.json()["is_promo_of_day"] is True

    # Toggle active
    active_res = client.patch(f"/api/v1/combos/{combo_id}/toggle-active", headers=admin_token_headers)
    assert active_res.status_code == status.HTTP_200_OK
    assert active_res.json()["is_active"] is False

    # Inactive should not be in public list
    pub_list = client.get("/api/v1/combos?active_only=true")
    assert not any(c["id"] == combo_id for c in pub_list.json())


def test_delete_combo(client, admin_token_headers):
    create_res = client.post(
        "/api/v1/combos",
        json={"title": "Combo Provisório", "price": "50.00"},
        headers=admin_token_headers,
    )
    combo_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/combos/{combo_id}", headers=admin_token_headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    get_res = client.get(f"/api/v1/combos/{combo_id}")
    assert get_res.status_code == status.HTTP_404_NOT_FOUND
